import sys
from PySide6.QtWidgets import (
QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QWidget, QHBoxLayout, QLabel, QDialog, QComboBox, QSpinBox,
QVBoxLayout, QFileDialog, QMessageBox, QLineEdit, QFormLayout, QTextEdit, QPushButton, QListWidget, QListWidgetItem, QMenu
)
from PySide6.QtCore import Qt
from Project import Project
from Tiles import Tile, PlotMap, PlotTile, CharacterTile, SettingTile

class StoryTree(QTreeWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

    def dropEvent(self, event):
        event.setDropAction(Qt.IgnoreAction) #Stops Qt from moving items - handle it manually
        mw = self.main_window

        #Item being dragged
        dragged = self.currentItem()
        if not dragged:
            event.ignore()
            return
        
        dragged_id = dragged.data(0, Qt.UserRole)
        if not dragged_id:
            event.ignore()
            return
        
        dragged_tile = mw.project.tiles.get(dragged_id)
        if not isinstance(dragged_tile, PlotTile): #If not dragging a PlotTile, do nothing
            event.ignore()
            return
        
        #Find target item
        target = self.itemAt(event.position().toPoint())
        if not target:
            event.ignore()
            return
        
        target_id = target.data(0, Qt.UserRole)
        target_tile = mw.project.tiles.get(target_id)

        #Case 1 - drop on PlotMap header (add a new PlotTile as plot point or move existing plot point to end)
        if isinstance(target_tile, PlotMap):
            target_plotmap = target_tile

            if dragged_tile.id not in target_plotmap.plot_points: #Adding a PlotTile as a new plot point at end
                target_plotmap.add_plot_point(dragged_tile, mw.project)
            else: #Moving a current plot point to end
                old_index = target_plotmap.plot_points.index(dragged_tile.id)
                end_index = len(target_plotmap.plot_points) - 1

                if old_index == end_index: #If the current index is the end, do nothing
                    event.ignore()
                    return
                
                target_plotmap.move_plot_point(old_index, end_index)
            
            #Rebuild tree and keep selection
            mw.refresh_tree_preserve_view(selected_id=dragged_tile.id)
            mw.mark_dirty()
            event.accept()
            return
        
        #Cases 2+3 - drop on a plot point
        #Case 2 - reorder plot points - move plot point
        #Case 3 - insert a new plot point - add plot point
        if not isinstance(target_tile, PlotTile):
            event.ignore()
            return
        
        #Target's PlotMap
        target_plotmap = None
        
        if target.parent():
            target_plotmap_item = target.parent()
            target_plotmap_id = target_plotmap_item.data(0, Qt.UserRole)
            if not target_plotmap_id:
                event.ignore()
                return
            
            target_plotmap = mw.project.tiles.get(target_plotmap_id) #Get plot point's PlotMap

        if not isinstance(target_plotmap, PlotMap): #Dragging onto a PlotTile that is not part of a PlotMap is ignored
            event.ignore()
            return
        
        #We now know we dropped a PlotTile (plot point or not currently) on a PlotTile plot point within a PlotMap

        #Case 2:
        if dragged_tile.id in target_plotmap.plot_points: #If reordering plot points within same PlotMap
            #Find indices
            old_index = target_plotmap.plot_points.index(dragged_tile.id)
            new_index = target_plotmap.plot_points.index(target_tile.id)

            if old_index == new_index: #If moving to the current index, do nothing
                event.ignore()
                return
        
            #Move in the PlotMap
            target_plotmap.move_plot_point(old_index, new_index)

            #Rebuild tree and keep selection
            mw.refresh_tree_preserve_view(selected_id=dragged_tile.id)
            mw.mark_dirty()
            event.accept()
            return
        
        #Case 3:
        target_index = target_plotmap.plot_points.index(target_tile.id)

        rect = self.visualItemRect(target) #Rectangle of target
        drop_y = event.position().toPoint().y() #Where in the rectangle it was dropped

        #Determine to place before target plot point (yes if below center of rectangle)
        before = drop_y < rect.center().y()             
        insert_index = target_index if before else target_index + 1

        target_plotmap.add_plot_point(dragged_tile, mw.project, insert_index)

        #Rebuild tree and keep selection
        mw.refresh_tree_preserve_view(selected_id=dragged_tile.id)
        mw.mark_dirty()
        event.accept()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("StoryAlign")

        self.project = None
        self.project_folder = None
        self.dirty = False #Dirty tracking for changes
        self.update_window_title()

        #---Menubar---
        
        menubar = self.menuBar()

        #File menu
        file_menu = menubar.addMenu("File")

        new_project_action = file_menu.addAction("New Project")
        new_project_action.triggered.connect(self.new_project)

        open_project_action = file_menu.addAction("Open Project")
        open_project_action.triggered.connect(self.load_project)

        file_menu.addSeparator()

        self.save_action = file_menu.addAction("Save")
        self.save_action.triggered.connect(self.save_project)
        self.save_action.setEnabled(False)

        self.save_as_action = file_menu.addAction("Save As")
        self.save_as_action.triggered.connect(self.save_project_as)
        self.save_as_action.setEnabled(False)
        
        #---Layout---

        #Main layout: horizontal split
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)

        #Left: Tile tree and features
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)

        #Search + filter bar
        self.tree_search = QLineEdit()
        self.tree_search.setPlaceholderText("Search tiles...")
        self.tree_search.textChanged.connect(self.apply_tree_filter)

        self.tree_filter = QComboBox()
        self.tree_filter.addItem("All")
        self.tree_filter.addItems(["PlotMap", "PlotTile", "CharacterTile", "SettingTile"])
        self.tree_filter.currentTextChanged.connect(self.apply_tree_filter)

        left_layout.addWidget(self.tree_search)
        left_layout.addWidget(self.tree_filter)   

        #Buttons layout
        buttons_layout = QHBoxLayout()
        self.add_tile_btn = QPushButton("+ Add Tile")
        self.delete_tile_btn = QPushButton("- Delete Tile")
        self.add_tile_btn.setEnabled(False)
        self.delete_tile_btn.setEnabled(False)

        self.add_tile_btn.clicked.connect(self.open_add_tile_dialog)
        self.delete_tile_btn.clicked.connect(self.delete_selected_tile)

        buttons_layout.addWidget(self.add_tile_btn)
        buttons_layout.addWidget(self.delete_tile_btn)

        left_layout.addLayout(buttons_layout)

        #Tile Tree
        self.tile_tree = StoryTree(self)
        self.tile_tree.setHeaderLabels(["Tiles"])
        #Connect selection - open tile in insepector/detail panel
        self.tile_tree.itemSelectionChanged.connect(self.on_tile_selected)
        
        #Context menu actions
        self.tile_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tile_tree.customContextMenuRequested.connect(self.on_tree_context_menu)
        self.tile_tree.itemDoubleClicked.connect(self.on_tree_item_double_clicked) #Double-clicking tile opens inline edit
        self.tile_tree.itemChanged.connect(self.on_tree_item_renamed) #When the item name change finishes...

        #Dragging options
        self.tile_tree.setDragEnabled(True)
        self.tile_tree.setAcceptDrops(True)
        self.tile_tree.setDropIndicatorShown(True)
        self.tile_tree.setDragDropMode(QTreeWidget.InternalMove)

        left_layout.addWidget(self.tile_tree)

        #Add left panel to main_layout
        main_layout.addWidget(left_panel, 1)  #1 = stretch factor

        #Right: Detail panel - tile inspector and editor
        self.detail_panel = QWidget()
        self.detail_layout = QVBoxLayout() #layout of detail panel
        self.detail_panel.setLayout(self.detail_layout) #set layout of detail panel

        label = QLabel("Select a tile to see details")
        self.detail_layout.addWidget(label)

        #Add right panel to main_layout
        main_layout.addWidget(self.detail_panel, 2)  #2 = stretch factor. Add detail panel to overall layout

    #Update window title based on name and dirty status
    def update_window_title(self):
        name = self.project.project_name if self.project else "StoryAlign"
        star = "*" if self.dirty else ""
        self.setWindowTitle(f"{name}{star} - StoryAlign")

    #Mark project as dirty - unsaved changes
    def mark_dirty(self):
        if not self.dirty:
            self.dirty = True
            self.update_window_title()

    def refresh_tree_preserve_view(self, selected_id=None, initial=False):
        def get_expanded_keys():
            expanded = set()

            def walk(item):
                key = item.data(0, Qt.UserRole) or item.data(0, Qt.UserRole + 1)
                if key and item.isExpanded():
                    expanded.add(key)
                
                for i in range(item.childCount()):
                    walk(item.child(i))

            for i in range(self.tile_tree.topLevelItemCount()):
                walk(self.tile_tree.topLevelItem(i))

            return expanded

        scroll = self.tile_tree.verticalScrollBar().value()
        expanded = get_expanded_keys()
        
        self.populate_tree(initial)

        def restore_expanded(expanded_ids):
            def walk(item):
                key = item.data(0, Qt.UserRole) or item.data(0, Qt.UserRole + 1)
                if key in expanded_ids:
                    item.setExpanded(True)
                    
                for i in range(item.childCount()):
                    walk(item.child(i))

            for i in range(self.tile_tree.topLevelItemCount()):
                walk(self.tile_tree.topLevelItem(i))

        restore_expanded(expanded)
        if selected_id:
            self.open_tile_by_id(selected_id)
        self.tile_tree.verticalScrollBar().setValue(scroll)

    def populate_tree(self, initial=False):
        self.tile_tree.clear() #Clear tree before repopulating

        self.tile_tree.setHeaderLabels([f"Tiles - {self.project.project_name}"])
        
        #Group tiles by type
        type_map = {}
        for tile in self.project.tiles.values():
            type_map.setdefault(tile.tile_type + "s", []).append(tile) #type_map becomes {"PlotMaps": [list of PlotMaps], "PlotTile": [list of PlotTiles], etc}

        for tile_type, tiles in type_map.items():
            type_item = QTreeWidgetItem([tile_type])
            type_item.setData(0, Qt.UserRole + 1, f"type:{tile_type}") #Type header tree identity (not ID)
            self.tile_tree.addTopLevelItem(type_item)

            for tile in tiles:
                tile_item = QTreeWidgetItem([tile.name])
                tile_item.setData(0, Qt.UserRole, tile.id) #Store tile ID in UserRole
                tile_item.setFlags(tile_item.flags() | Qt.ItemIsEditable)
                type_item.addChild(tile_item)

                #Show plot points for PlotMaps, not links
                if isinstance(tile, PlotMap):
                    for i, plot_tile in enumerate(tile.resolved_plot_points):
                        child = QTreeWidgetItem([f"{i+1}. {plot_tile.name}"])
                        child.setData(0, Qt.UserRole, plot_tile.id)
                        child.setFlags(child.flags() & ~Qt.ItemIsEditable) #Doesn't let you edit the name of a plot point (passed to PlotTile)
                        tile_item.addChild(child)
                    if initial:
                        tile_item.setExpanded(True) #Initial population expands PlotMaps

                # for linked_tile in tile.resolved_links:
                #     linked_item = QTreeWidgetItem([linked_tile.name])
                #     linked_item.setData(0, Qt.UserRole, linked_tile.id)
                #     linked_item.setFlags(linked_item.flags() | Qt.ItemIsEditable)
                #     tile_item.addChild(linked_item)
                # tile_item.setExpanded(False)
            if initial:
                type_item.setExpanded(True) #Initial population expands tile type tree nodes

    #Context menu for tree
    def on_tree_context_menu(self, pos):
        #selected = self.tile_tree.selectedItems() #Figures out what was clicked
        item = self.tile_tree.itemAt(pos)
        clicked_type = None #Used to determine default type for Add Tile

        menu = QMenu(self)
        add_tile_action = menu.addAction("Add Tile")

        if item is None: #Right clicked empty space - show Add Tile only with no default
            add_tile_action.triggered.connect(self.open_add_tile_dialog)
            menu.exec(self.tile_tree.viewport().mapToGlobal(pos))
            return
        
        tile_id = item.data(0, Qt.UserRole)
        
        if tile_id is None: #Type header actions
            #Get type header text to use as default for add tile option ("PlotMaps" -> "PlotMap")
            clicked_type = item.text(0)
            if clicked_type.endswith("s"):
                clicked_type = clicked_type[:-1]
        else: #Tile actions
            tile = self.project.tiles.get(tile_id)
            if tile:
                clicked_type = tile.tile_type
            
            rename_action = menu.addAction("Rename")
            add_link_action = menu.addAction("Add Link")
            menu.addSeparator()

            if item.parent():
                parent_id = item.parent().data(0, Qt.UserRole)
                if parent_id:
                    plotmap = self.project.tiles.get(parent_id)
                    if isinstance(plotmap, PlotMap) and isinstance(tile, PlotTile):
                        remove_action = menu.addAction("Remove from PlotMap")

                        def remove_from_plotmap():
                            plotmap.remove_plot_point(tile)
                            self.refresh_tree_preserve_view(selected_id=plotmap.id)
                            self.mark_dirty()
                        remove_action.triggered.connect(remove_from_plotmap)

            delete_action = menu.addAction("Delete")

            def show_add_link_dialog():
                selected = self.tile_tree.selectedItems()
                if not selected:
                    return
                
                tile_id = selected[0].data(0, Qt.UserRole)
                if not tile_id:
                    return
                
                tile = self.project.tiles.get(tile_id)
                if not tile:
                    return
                
                self.open_add_link_dialog(tile)
            
            rename_action.triggered.connect(lambda: self.start_inline_rename(item))
            add_link_action.triggered.connect(show_add_link_dialog)
            delete_action.triggered.connect(self.delete_selected_tile)

        add_tile_action.triggered.connect(lambda: self.open_add_tile_dialog(default_type=clicked_type))
        
        menu.exec(self.tile_tree.viewport().mapToGlobal(pos)) #Show the context menu at right-click locations

    def on_tree_item_double_clicked(self, item):
        item_id = item.data(0, Qt.UserRole)
        if not item_id:
            return
        tile = self.project.tiles.get(item_id)
        if not tile:
            return
        if isinstance(tile, PlotTile):
            self.start_inline_rename(item) #Ensures editing a plot point name edits the PlotTile name

    def start_inline_rename(self, item):
        item_id = item.data(0, Qt.UserRole)
        item = self.search_tree(item_id) #Ensures editing a plot point name edits the PlotTile name
        if item:
            self.tile_tree.editItem(item, 0) #Starts the name edit

    def on_tree_item_renamed(self, item):
        tile_id = item.data(0, Qt.UserRole)
        if not tile_id:
            return
        
        tile = self.project.tiles.get(tile_id)
        if not tile:
            return
        
        new_name = item.text(0).strip()

        if not new_name:
            #Revert if blank
            item.setText(0, tile.name)
            return

        if tile.name != new_name:
            tile.name = new_name
            self.mark_dirty()
            self.refresh_tree_preserve_view(selected_id=tile_id)

    def open_add_link_dialog(self, tile):
        dialog = QDialog(self) #Opens a dialog window
        dialog.setWindowTitle("Add Link")

        layout = QVBoxLayout(dialog) #Set dialog window layout

        search_box = QLineEdit()
        search_box.setPlaceholderText("Search tiles...")

        type_filter = QComboBox()
        type_filter.addItem("All")
        type_filter.addItems(["PlotMap", "PlotTile", "CharacterTile", "SettingTile"])

        layout.addWidget(search_box)
        layout.addWidget(type_filter)

        list_widget = QListWidget()
        layout.addWidget(list_widget)

        #Only unlinked tiles that aren't the selected tile can be linked
        all_candidates = [
            other_tile
            for other_tile in self.project.tiles.values()
            if other_tile.id != tile.id
            ]

        # all_candidates = [
        #     other_tile
        #     for other_tile in self.project.tiles.values()
        #     if other_tile.id != tile.id and not any(link["target"] == other_tile.id for link in tile.links)
        #     ]
        
        #Refreshes and updates link options QList list_widget based on type filter and search
        def refresh_list():
            list_widget.clear()

            query = search_box.text().lower()
            selected_type = type_filter.currentText()

            for other_tile in all_candidates:
                #Type filter
                if selected_type != "All" and other_tile.tile_type != selected_type:
                    continue #Only include selected-type tiles

                #Search filter
                if query and query not in other_tile.name.lower():
                    continue #Only include tiles with the search query (if any) within their name

                item = QListWidgetItem(f"{other_tile.name} ({other_tile.tile_type})")
                item.setData(Qt.UserRole, other_tile.id)
                list_widget.addItem(item)

        search_box.textChanged.connect(refresh_list)
        type_filter.currentTextChanged.connect(refresh_list)

        refresh_list() #Run when dialog box opens

        #The various link types (excluding plot point)
        LINK_TYPES = ["references", "requires", "causes", "enables", "blocks", "foreshadows", "happens in", "involves"]
        #2-5 are logical. 1 is basic. 6-8 are for info.
        #References = general reference to something else. Requires = B requires A to happen (logic). Causes = A causes B to happen.

        # link_type_combo = QComboBox()
        # link_type_combo.addItems(LINK_TYPES)
        # layout.addWidget(QLabel("Link Type:"))
        # layout.addWidget(link_type_combo)

        row = QHBoxLayout()
        left = QLabel(tile.name)
        row.addWidget(left)

        link_type_combo = QComboBox()
        link_type_combo.addItems(LINK_TYPES)
        row.addWidget(link_type_combo)

        middle = QLabel("______")
        row.addWidget(middle)

        def selection_change():
            confirm.setEnabled(bool(list_widget.selectedItems()))
            selected = list_widget.selectedItems()
            item = selected[0]
            middle.setText(item.text())
        list_widget.itemSelectionChanged.connect(selection_change)

        layout.addLayout(row)

        confirm = QPushButton("Link Selected Tile")
        layout.addWidget(confirm)

        #Add link, refresh tree, and keep the current tile open (by reopening it)
        def confirm_link():
            selected = list_widget.selectedItems()
            if not selected:
                QMessageBox.warning(dialog, "No Selection", "Please select a tile to link")
                return
            item = selected[0]
            target_id = item.data(Qt.UserRole)
            link_type = link_type_combo.currentText()

            try:
                tile.add_link(target_id, self.project, link_type)
            except ValueError as error:
                QMessageBox.warning(self, "Cannot Link Tiles", str(error))
                return

            dialog.accept()
            self.mark_dirty()

            #Refresh links section
            self.refresh_tree_preserve_view(selected_id=tile.id)

        confirm.clicked.connect(confirm_link)
        confirm.setEnabled(False)

        # #Gray out Link Selected Tile button until selection
        # list_widget.itemSelectionChanged.connect(lambda: confirm.setEnabled(bool(list_widget.selectedItems())))
        
        dialog.exec() #Actually run the dialog window

    #When someone selects an item in the tree
    def on_tile_selected(self):
        self.clear_detail_panel()
        
        selected_items = self.tile_tree.selectedItems()
        if not selected_items: #If no tile is selected
            self.delete_tile_btn.setEnabled(False)
            return
        
        item = selected_items[0]
        tile_id = item.data(0, Qt.UserRole)
        
        if not tile_id:
            #This is a type header, not a tile (you click the top nodes like PlotMap)
            self.delete_tile_btn.setEnabled(False)
            label = QLabel(f"Type: {item.text(0)}")
            self.detail_layout.addWidget(label)
            return
        
        tile = self.project.tiles.get(tile_id)
        if not tile:
            label = QLabel("Tile not found")
            self.detail_layout.addWidget(label)
            return
        
        self.delete_tile_btn.setEnabled(True)

        if isinstance(tile, PlotMap):
            self.build_plotmap_view(tile)
        else:
            self.build_basic_editor(tile, item) #Tile editor function

    def open_tile_by_id(self, tile_id):
        item = self.search_tree(tile_id)
        if item:
            self.tile_tree.setCurrentItem(item)

    #Searches the tile tree for the tile with the matching id. Returns True if found; False if not (Searches canonical tiles, not linked tiles)
    def search_tree(self, tile_id):
        root = self.tile_tree.invisibleRootItem()

        for i in range(root.childCount()): #Tile types
            type_item = root.child(i)

            for j in range(type_item.childCount()): #Actual tiles
                tile_item = type_item.child(j)

                if tile_item.data(0, Qt.UserRole) == tile_id:
                    return tile_item
                        
        return None #If not found, return None
    
    #Dialog window to create a tile
    def open_add_tile_dialog(self, default_type=None):
        if not self.project:
            QMessageBox.warning(self, "No Project Open", "Open a project or create a new project before adding a tile.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Create Tile")

        layout = QVBoxLayout(dialog)

        type_box = QComboBox()
        type_box.addItems(["PlotMap", "PlotTile", "CharacterTile", "SettingTile"])

        if default_type:
            index = type_box.findText(default_type)
            if index >= 0: #If found
                type_box.setCurrentIndex(index)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Tile name")

        create_btn = QPushButton("Create")
        cancel_btn = QPushButton("Cancel")

        layout.addWidget(QLabel("Tile Type"))
        layout.addWidget(type_box)
        layout.addWidget(QLabel("Name"))
        layout.addWidget(name_edit)
        layout.addWidget(create_btn)
        layout.addWidget(cancel_btn)

        cancel_btn.clicked.connect(dialog.reject)

        create_btn.setEnabled(False)

        #Enables "Create" button if name field isn't blank
        def update_create_button():
            create_btn.setEnabled(bool(name_edit.text().strip())) 
        name_edit.textChanged.connect(update_create_button)

        def do_create():
            name = name_edit.text().strip()
            tile_type = type_box.currentText()

            if not name:
                QMessageBox.warning(dialog, "Missing Name", "Tile must have a name.")
                return
            
            if tile_type == "PlotMap":
                tile = PlotMap(name)
            elif tile_type == "PlotTile":
                tile = PlotTile(name)
            elif tile_type == "CharacterTile":
                tile = CharacterTile(name)
            elif tile_type == "SettingTile":
                tile = SettingTile(name)

            self.project.add_tile(tile)
            self.mark_dirty()
            self.refresh_tree_preserve_view(selected_id=tile.id)
            dialog.accept()

        create_btn.clicked.connect(do_create)
        dialog.exec()

    def delete_selected_tile(self):
        selected = self.tile_tree.selectedItems()
        if not selected:
            return
        
        if not self.project:
            return
        
        item = selected[0]
        tile_id = item.data(0, Qt.UserRole)

        if not tile_id:
            return
        
        tile = self.project.tiles[tile_id]

        confirm = QMessageBox.question(self, "Delete Tile", f"Delete '{tile.name}'?\nThis will remove all links to it.", QMessageBox.Yes | QMessageBox.No)

        if confirm != QMessageBox.Yes:
            return

        self.project.remove_tile(tile_id)
        self.mark_dirty()
        self.refresh_tree_preserve_view()
        self.clear_detail_panel() #Since the deleted tile was selected, clear the panel

    #Filter tile tree based on search and type filter input
    def apply_tree_filter(self):
        query = self.tree_search.text().lower()
        selected_type = self.tree_filter.currentText()

        root = self.tile_tree.invisibleRootItem()

        for i in range(root.childCount()):
            type_item = root.child(i)
            self.filter_type_node(type_item, query, selected_type)

    #Filter each tile type group
    def filter_type_node(self, type_item, query, selected_type):
        type_name = type_item.text(0) #Get type header name

        #If filtering by type, hide entire group if it doesn't match
        if selected_type != "All" and type_name != selected_type + "s":
            type_item.setHidden(True)
            return
        else:
            type_item.setHidden(False)

        any_visible = False

        for i in range(type_item.childCount()):
            tile_item = type_item.child(i)
            visible = self.filter_tile_node(tile_item, query)
            any_visible = any_visible or visible #True if any tiles are visible for this tile type

        #Hide empty tile type groups
        type_item.setHidden(not any_visible)

    #Filter tiles (and their linked children)
    def filter_tile_node(self, item, query):
        tile_id = item.data(0, Qt.UserRole)
        tile = self.project.tiles.get(tile_id)

        if not tile:
            return False
        
        query = query.lower() if query else ""

        #If this tile node matches the search (if any) or one of its links matches
        self_matches = not query or query in tile.name.lower() #No query = match. Query and query in name = match
        any_link_matches = any(query in linked.name.lower() for linked in tile.resolved_links)

        if isinstance(tile, PlotMap):
            any_plot_point_visible = False

            for i in range(item.childCount()):
                child_item = item.child(i)
                child_tile_id = child_item.data(0, Qt.UserRole)
                child_tile = self.project.tiles.get(child_tile_id)

                if not child_tile:
                    continue

                child_matches = not query or query in child_tile.name.lower()

                #Also check links of child plot point
                if not child_matches:
                    for linked in child_tile.resolved_links:
                        if query and query in linked.name.lower():
                            child_matches = True
                            break

                child_item.setHidden(not child_matches)
                if child_matches:
                    any_plot_point_visible = True
            #PlotMap is visible if itself matches the query, any links match, or any plot points are visible
            visible = self_matches or any_link_matches or any_plot_point_visible
            item.setHidden(not visible)
            #Expand PlotMap if query exists and either a plot point matches or itself matches (if itself matches, plot point visible since PlotMap in plot point's links)
            item.setExpanded(bool(query and (any_plot_point_visible or self_matches)))
            return visible
        else:
            visible = self_matches or any_link_matches
            item.setHidden(not visible)
            return visible

    def build_basic_editor(self, tile, tree_item):
        #Title and subtitle
        title = QLabel(f"{tile.name}")
        subtitle = QLabel(f"{tile.tile_type}")
        title.setStyleSheet("font-weight: bold; font-size: 16px;")
        subtitle.setStyleSheet("font-weight: bold; font-size: 12px;")
        self.detail_layout.addWidget(title)
        self.detail_layout.addWidget(subtitle)

        #Form layout
        form = QFormLayout()
        self.detail_layout.addLayout(form)     

        #Name field
        name_edit = QLineEdit(tile.name)

        def on_name_changed():
            new_name = name_edit.text().strip()
            
            if not new_name:
                #Revert to previous
                name_edit.setText(tile.name)
                QMessageBox.warning(self, "Invalid Name", "Tile name cannot be empty")
                return
            
            if tile.name != new_name:
                tile.name = new_name
                self.mark_dirty()

                self.refresh_tree_preserve_view(selected_id=tile.id)

        name_edit.editingFinished.connect(on_name_changed)
        form.addRow("Name:", name_edit)

        #Tags field
        tags_edit = QLineEdit(", ".join(sorted(tile.tags)))

        def on_tags_changed():
            new_tags = {t.strip().lower() for t in tags_edit.text().split(",") if t.strip()} #Adds stripped tags if a tag has non-whitespace content
            if tile.tags != new_tags:
                tile.tags = new_tags
                self.mark_dirty()

        tags_edit.editingFinished.connect(on_tags_changed)
        form.addRow("Tags:", tags_edit)

        #Description field
        if hasattr(tile, "description"): #PlotTiles, CharacterTiles, SettingTiles
            desc_edit = QTextEdit()
            desc_edit.setPlainText(tile.description)
            desc_edit.setMinimumHeight(120)

            def on_description_changed():
                if tile.description != desc_edit.toPlainText():
                    tile.description = desc_edit.toPlainText()
                    self.mark_dirty()

            desc_edit.textChanged.connect(on_description_changed)
            form.addRow("Description:", desc_edit)

        #Tile-specific info
        if isinstance(tile, PlotTile):
            #Date field
            date_edit = QLineEdit(tile.date)
            def on_date_changed():
                if tile.date != date_edit.text():
                    tile.date = date_edit.text()
                    self.mark_dirty()
            date_edit.editingFinished.connect(on_date_changed)
            form.addRow("Date:", date_edit)

            #Location field
            location_edit = QLineEdit(tile.location)
            def on_location_changed():
                if tile.location != location_edit.text():
                    tile.location = location_edit.text()
                    self.mark_dirty()
            location_edit.editingFinished.connect(on_location_changed)
            form.addRow("Location:", location_edit)

            #Timeline index field
            timeline_index_edit = QSpinBox()
            timeline_index_edit.setMinimum(-1)
            timeline_index_edit.setMaximum(100000)
            if tile.timeline_index is None:
                timeline_index_edit.setValue(-1)
            else:
                timeline_index_edit.setValue(tile.timeline_index)

            def on_timeline_index_changed(value):
                if value == -1:
                    new_val = None
                else:
                    new_val = value

                if tile.timeline_index != new_val:
                    tile.timeline_index = new_val
                    self.mark_dirty()
            timeline_index_edit.valueChanged.connect(on_timeline_index_changed)
            form.addRow("Timeline Index:", timeline_index_edit)
        elif isinstance(tile, CharacterTile):
            #Title field
            title_edit = QLineEdit(tile.title)
            def on_title_changed():
                if tile.title != title_edit.text():
                    tile.title = title_edit.text()
                    self.mark_dirty()
            title_edit.editingFinished.connect(on_title_changed)
            form.addRow("Title:", title_edit)

            #Backstory field
            backstory_edit = QTextEdit()
            backstory_edit.setPlainText(tile.backstory)
            backstory_edit.setMinimumHeight(120)

            def on_backstory_changed():
                if tile.backstory != backstory_edit.toPlainText():
                    tile.backstory = backstory_edit.toPlainText()
                    self.mark_dirty()

            backstory_edit.textChanged.connect(on_backstory_changed)
            form.addRow("Backstory:", backstory_edit)

            #Traits field - list of character traits
            form.addRow(QLabel("Traits:"))

            traits_layout = QVBoxLayout()
            form.addRow(traits_layout)

            #Populate traits field section
            def rebuild_traits():
                #Clear old traits widgets
                self.clear_layout(traits_layout)

                #Rebuild from tile.traits
                for i, trait in enumerate(tile.traits):
                    row = QHBoxLayout()
                    edit = QLineEdit(trait) #Each trait gets its own line edit

                    def trait_updater(index, field):
                        def update():
                            new_value = field.text()
                            if tile.traits[index] != new_value:
                                tile.traits[index] = new_value
                                self.mark_dirty()
                        return update
                    edit.editingFinished.connect(trait_updater(i, edit))

                    #Each trait gets a delete button
                    delete_btn = QPushButton("✕")
                    delete_btn.setFixedWidth(25)

                    def trait_deleter(index):
                        def delete():
                            tile.traits.pop(index)
                            self.mark_dirty()
                            rebuild_traits() #Refresh traits after deleting one (calls itself to repopulate traits section)
                        return delete
                    delete_btn.clicked.connect(trait_deleter(i))

                    row.addWidget(edit)
                    row.addWidget(delete_btn)

                    traits_layout.addLayout(row)
                
                #Add trait button
                add_trait_btn = QPushButton("+ Add Trait")

                def add_trait():
                    tile.traits.append("New trait") #Adds a placeholder trait to be edited after trait refresh
                    self.mark_dirty()
                    rebuild_traits()
                add_trait_btn.clicked.connect(add_trait)

                traits_layout.addWidget(add_trait_btn)

            rebuild_traits()

            #Extra chracter info - only display if it has it initially (non-empty)? Add dropdown to select what to display
            # (for ease and adding attributes that are currerntly empty)

            #Race field
            race_edit = QLineEdit(tile.race)
            def on_race_changed():
                if tile.race != race_edit.text():
                    tile.race = race_edit.text()
                    self.mark_dirty()
            race_edit.editingFinished.connect(on_race_changed)
            form.addRow("Race:", race_edit)

            #Age field
            age_edit = QLineEdit(tile.age)
            def on_age_changed():
                if tile.age != age_edit.text():
                    tile.age = age_edit.text()
                    self.mark_dirty()
            age_edit.editingFinished.connect(on_age_changed)
            form.addRow("Age:", age_edit)

            #Gender field
            gender_edit = QLineEdit(tile.gender)
            def on_gender_changed():
                if tile.gender != gender_edit.text():
                    tile.gender = gender_edit.text()
                    self.mark_dirty()
            gender_edit.editingFinished.connect(on_gender_changed)
            form.addRow("Gender:", gender_edit)

            #Occupation field
            occupation_edit = QLineEdit(tile.occupation)
            def on_occupation_changed():
                if tile.occupation != occupation_edit.text():
                    tile.occupation = occupation_edit.text()
                    self.mark_dirty()
            occupation_edit.editingFinished.connect(on_occupation_changed)
            form.addRow("Occupation:", occupation_edit)
        elif isinstance(tile, SettingTile):
            #History field
            history_edit = QTextEdit()
            history_edit.setPlainText(tile.history)
            history_edit.setMinimumHeight(120)

            def on_history_changed():
                if tile.history != history_edit.toPlainText():
                    tile.history = history_edit.toPlainText()
                    self.mark_dirty()

            history_edit.textChanged.connect(on_history_changed)
            form.addRow("History:", history_edit)
        
        #Linked tiles section - clickable list that opens that tile
        links_label = QLabel("Linked Tiles:")
        links_label.setStyleSheet("font-weight: bold;")
        self.detail_layout.addWidget(links_label)

        links_list = QListWidget()
        self.detail_layout.addWidget(links_list)

        #Display links in a list
        for link in tile.links:
            target = self.project.tiles[link["target"]]
            label = f'{link["type"]} → {target.name}'

            item = QListWidgetItem(label)
            #item.setData(Qt.UserRole, link["target"])
            item.setData(Qt.UserRole, link)
            links_list.addItem(item)

        # for target_id in tile.get_link_targets():
        #     target = self.project.tiles[target_id]
        #     types = ", ".join(sorted(tile.get_link_types(target_id)))
        #     item = QListWidgetItem(f"{target.name} - {types}")
        #     item.setData(Qt.UserRole, target.id)
        #     links_list.addItem(item)

        #Double-clicking a link opens the linked tile in the inspector/detail panel
        def open_linked_tile(item):
            target_id = item.data(Qt.UserRole)
            self.open_tile_by_id(target_id)
        
        links_list.doubleClicked.connect(open_linked_tile)

        #Button to open a dialog window to add a link
        add_link_btn = QPushButton("Add Link")
        self.detail_layout.addWidget(add_link_btn)

        add_link_btn.clicked.connect(lambda: self.open_add_link_dialog(tile))

        #Button to remove the selected link
        remove_layout = QHBoxLayout()

        # type_combo = QComboBox()
        # type_combo.setEnabled(False)

        remove_link_btn = QPushButton("Remove Link")
        remove_link_btn.setEnabled(False)

        # remove_layout.addWidget(type_combo)
        remove_layout.addWidget(remove_link_btn)

        self.detail_layout.addLayout(remove_layout)

        # def update_link_type_combo():
        #     selected = links_list.currentItem()
        #     if not selected:
        #         type_combo.setEnabled(False)
        #         remove_link_btn.setEnabled(False)
        #         return
            
        #     target_id = selected.data(Qt.UserRole)
        #     type_combo.clear()
        #     types = [type for type in tile.get_link_types(target_id) if type != "plot point"] #Don't allow plot point links to be changed

        #     if not types:
        #         type_combo.setEnabled(False)
        #         remove_link_btn.setEnabled(False)
        #         return
            
        #     type_combo.setEnabled(True)
        #     remove_link_btn.setEnabled(True)

        #     #Add found type options
        #     for type in sorted(types):
        #         type_combo.addItem(type)

        #     #All types option
        #     if len(types) > 1:
        #         type_combo.addItem("All")

        # #Gray out Remove Selected Link button until selection
        # links_list.itemSelectionChanged.connect(update_link_type_combo)

        def remove_selected_link():
            selected = links_list.currentItem()
            if not selected:
                return
            
            link = selected.data(Qt.UserRole)
            target_id = link["target"]
            link_type = link["type"]

            #Don't allow removing plot point links in inspector
            if link_type == "plot point":
                plotmap = self.project.tiles.get(target_id)
                if isinstance(plotmap, PlotMap) and isinstance(tile, PlotTile):
                    plotmap.remove_plot_point(tile)
                    self.mark_dirty()
                    self.refresh_tree_preserve_view(selected_id=tile.id)
            
            # target_id = selected.data(Qt.UserRole)
            # link_type = type_combo.currentText()

            tile.remove_link(target_id, link_type)
            
            self.mark_dirty()

            #Refresh links section
            self.refresh_tree_preserve_view(selected_id=tile.id)

        remove_link_btn.clicked.connect(remove_selected_link)

        #Gray out Remove Selected Link button until selection of link that isn't plot point
        def selection_change():
            selected = links_list.selectedItems()[0]
            link = selected.data(Qt.UserRole)

            if link and link["type"] != "plot point":
                remove_link_btn.setText("Remove Link")
                remove_link_btn.setEnabled(True)
            elif link and link["type"] == "plot point":
                remove_link_btn.setText("Remove from PlotMap")
                remove_link_btn.setEnabled(True)
            else:
                remove_link_btn.setEnabled(False)
        #links_list.itemSelectionChanged.connect(lambda: remove_link_btn.setEnabled(bool(links_list.selectedItems())))
        links_list.itemSelectionChanged.connect(selection_change)

    def build_plotmap_view(self, plotmap):
    #Add button to view PlotMap later
        title = QLabel(f"PlotMap: {plotmap.name}")
        title.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.detail_layout.addWidget(title)

        self.detail_layout.addWidget(QLabel("Plot Points:"))

        for tile in plotmap.resolved_plot_points:
            label = QLabel(f"- {tile.name}")
            self.detail_layout.addWidget(label)

    #Removes all widgets and layouts from detail panel
    def clear_detail_panel(self):
        while self.detail_layout.count():
            item = self.detail_layout.takeAt(0) #gets first widget
            
            widget = item.widget()
            layout = item.layout()

            if widget:
                widget.deleteLater()
            elif layout:
                self.clear_layout(layout)
        
    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)

            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self.clear_layout(child.layout()) #Recursively clears any layouts within a layout

    def new_project(self):
        self.project = Project()
        self.project_folder = None

        self.save_action.setEnabled(True)
        self.save_as_action.setEnabled(True)
        self.add_tile_btn.setEnabled(True)
        self.delete_tile_btn.setEnabled(False)

        self.mark_dirty()
        self.refresh_tree_preserve_view(initial=True)

    def load_project(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Project Folder") #Folder selection
        if not folder:
            return

        loaded_project, load_report, load_check_report = Project.load(folder) #Load the project from the folder

        if loaded_project is None:
            QMessageBox.critical(self, "Load failed", "Project could not be loaded.")
            return

        #Add load checking later. Display errors and warnings with options to proceed or not.

        self.project = loaded_project
        self.project_folder = folder
        self.dirty = False
        self.update_window_title()

        self.save_action.setEnabled(True)
        self.save_as_action.setEnabled(True)
        self.add_tile_btn.setEnabled(True)
        self.delete_tile_btn.setEnabled(False)
        self.refresh_tree_preserve_view(initial=True)

    def save_project(self):
        if not self.project:
            return
        
        if not self.project_folder:
            self.save_project_as()
            return
        
        ok = self.project.save(self.project_folder)

        if ok:
            self.dirty = False
            self.update_window_title()
            QMessageBox.information(self, "Saved", "Project saved successfully!")
        else:
            QMessageBox.critical(self, "Save Failed", "The project could not be saved.")

    def save_project_as(self):
        if not self.project:
            return
        
        folder = QFileDialog.getExistingDirectory(self, "Select Project Folder to Save to") #Folder selection
        if not folder:
            return

        self.project_folder = folder
        ok = self.project.save(folder)

        if ok:
            self.dirty = False
            self.update_window_title()
            QMessageBox.information(self, "Saved", "Project saved successfully!")
        else:
            QMessageBox.critical(self, "Save Failed", "The project could not be saved.")

    #Before closing, asks if you want to save changes (if you've made any)
    def closeEvent(self, event):
        if not self.dirty:
            event.accept()
            return
        
        reply = QMessageBox.question(self, "Unsaved Changes", "You have unsaved changes. Do you want to save before closing?", QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)

        if reply == QMessageBox.Yes:
            self.save_project()
        elif reply == QMessageBox.No:
            event.accept()
        else:
            event.ignore()



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(800, 600)
    window.show()

    # folder = "TestProjectBackend"
    # loaded_tup = Project.load(folder)
    # window.project = loaded_tup[0]
    # window.populate_tree()

    sys.exit(app.exec())
