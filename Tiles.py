import json
from pathlib import Path

# Mapping of Tile types to their respective prefixes for ID generation
prefix_map = {
    "PlotMap": "pm",
    "PlotTile": "pt",
    "CharacterTile": "ch",
    "SettingTile": "st"
}

class Tile:
    default_directories = {
        "PlotMap": "Tiles/PlotMaps",
        "PlotTile": "Tiles/PlotTiles",
        "CharacterTile": "Tiles/CharacterTiles",
        "SettingTile": "Tiles/SettingTiles"
    } # Default directories for saving different Tile types

    def __init__(self, tile_type, name, id=None, links=None, **kwargs):
        self.id = id #Project assigns unique ID later if None
        self.tile_type = tile_type
        self.name = name
        self.links = links if links is not None else [] # Prevent shared mutable default argument. List of linked tile IDs
        self.resolved_links = [] #List of Tile objects whose IDs make up self.links
        self.tags = set()

    def toDict(self):
        #Convert the Tile object to a dictionary for JSON serialization
        return {
            "id": self.id,
            "tile_type": self.tile_type,
            "name": self.name,
            "links": self.links,
            "tags": list(self.tags) #Turns set into list for json serialization
        }
    
    @classmethod
    def fromDict(cls, data: dict): #Class method to create a Tile object from a dictionary
        tile_type = data.get("tile_type")
        tile_type_class = cls.type_map.get(tile_type, cls) #Get the appropriate subclass based on tile_type, default to Tile if not found
        #This is used because you might do Tile.fromDict(data) and want the correct subclass returned

        #Ensure all expected constructor arguments exist
        #Set safe defaults for base Tile attributes
        data.setdefault("id", None) #Project assigns unique ID later if None
        data.setdefault("tile_type", "Unknown")
        data.setdefault("name", "Unnamed Tile")
        data.setdefault("links", [])
        data.setdefault("tags", [])

        #Set safe defaults for Tile subclass-specific attributes. This means older saved files missing new attributes can still be loaded
        if tile_type_class == PlotMap:
            data.setdefault("plot_points", [])
        elif tile_type_class == PlotTile:
            data.setdefault("description", "")
            data.setdefault("date", "")
            data.setdefault("location", "")
            data.setdefault("timeline_index", None)
        elif tile_type_class == CharacterTile:
            data.setdefault("description", "")
            data.setdefault("title", "")
            data.setdefault("backstory", "")
            data.setdefault("traits", [])
            data.setdefault("race", "")
            data.setdefault("age", None)
            data.setdefault("gender", "")
            data.setdefault("occupation", "")
        elif tile_type_class == SettingTile:
            data.setdefault("description", "")
            data.setdefault("history", "")

        tile = tile_type_class(**data) #Call the constructor of the appropriate subclass (**data unpacks the dictionary into keyword arguments)
        tile.tags = set(data["tags"]) #Loads tile with its tags
        return tile

    @classmethod
    def load(cls, filepath): #Class method to load a Tile object from a JSON file
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"{filepath} does not exist")

        with path.open('r', encoding='utf-8') as file: # Open the file for reading with UTF-8 encoding (standard for JSON files)
            data = json.load(file)
        return cls.fromDict(data) #Create and return a Tile object from the loaded data using fromDict method
        #Add check for file validity

    #Instance method to save a Tile object to a JSON file
    def save(self, filename=None, directory=None):
        if filename is None:
            filename = f"{self.id}.json" # Default filename based on Tile ID if none provided
        if directory is None:
            directory = self.default_directories.get(self.tile_type, ".") # Default directory based on Tile type if none provided, default to current directory if type not found
        
        path = Path(directory) / filename # Construct the full file path by combining directory and filename
        path.parent.mkdir(parents=True, exist_ok=True) # Ensure the directory exists. Create it if it doesn't
        
        with path.open('w', encoding='utf-8') as file: # Open the file for writing with UTF-8 encoding (standard for JSON files)
            json.dump(self.toDict(), file, indent=4) # Turn Tile object into dict and write to JSON with indentation for readability

    #Add a link from this Tile to another Tile by ID. If project passed in, updates resolved_links
    def add_link(self, target_id, project, link_type="references"):
        if target_id not in project.tiles: #Checks if target_id is in the project's registry
            raise ValueError(f"Cannot link to {target_id}: Tile not in project")
        
        #Prevent duplicate links of same type
        for link in self.links:
            if link["target"] == target_id and link.get("type", "references") == link_type:
                raise ValueError(f"Link already exists: {link_type} to {project.tiles[target_id].name}")
            
        target_tile = project.tiles[target_id]
            
        if link_type in {"requires", "causes", "enables", "blocks"}:
            if not isinstance(self, PlotTile) or not isinstance(target_tile, PlotTile):
                raise ValueError("Story logic links (requires, causes, enables, blocks) must be between two PlotTiles because they represent story-event ordering.")
            
        self.links.append({"target": target_id, "type": link_type})
        
        #Updated resolved links
        if target_tile not in self.resolved_links:
            self.resolved_links.append(target_tile)

        # if target_id not in self.links:
        #     self.links.append(target_id)
        #     target_tile = project.tiles[target_id]
        #     if target_tile not in self.resolved_links:
        #         self.resolved_links.append(target_tile) #Adds the new Tile object to resolved_links

        #self.resolve_links(project.tiles)

    #Remove a link from this Tile (not bidirectional). Updates resolved_links. If link_type not provided, removes all link instances
    def remove_link(self, target_id, link_type=None):
        self.links = [
            link for link in self.links
            if not (link["target"] == target_id and (link_type is None or link.get("type") == link_type))
        ]

        #Only remove resolved tile if no remaining links point to it
        still_linked = any(link["target"] == target_id for link in self.links)
        if not still_linked:
            self.resolved_links = [
                tile for tile in self.resolved_links
                if tile.id != target_id
            ]

        # if target_id in self.links:
        #     self.links.remove(target_id)
        #     self.resolved_links = [tile for tile in self.resolved_links if tile.id != target_id] #Filters resolved_links to remove Tile with target_id

    #Method to resolve all links to Tile objects
    def resolve_links(self, registry):
        resolved = []
        seen_ids = set()

        for link in self.links:
            tile_id = link["target"]
            if tile_id in registry and tile_id not in seen_ids:
                resolved.append(registry[tile_id])
                seen_ids.add(tile_id)
            elif tile_id not in registry:
                print(f"Warning: link target {tile_id} not found")

        # for link_id in self.links:
        #     if link_id in registry: #Registry maps IDs to Tile objects
        #         tile = registry[link_id] #Get the Tile object from the registry
        #         resolved.append(tile)
        #     else:
        #         print(f"Warning: link ID {link_id} not found in registry")

        self.resolved_links = resolved #Stores resolved linked Tile objects
        return resolved
    
    #Return all link dicts from Tile (self) to target_id
    def get_links_to(self, target_id):
        return [link for link in self.links if link.get("target") == target_id]
    
    #Return unique target IDs of this Tile's links
    def get_link_targets(self):
        id_set = {link.get("target") for link in self.links}
        return list(id_set)
    
    #Return all link types this Tile has to target
    def get_link_types(self, target_id):
        return [link.get("type") for link in self.links if link.get("target") == target_id]
    
    def add_tag(self, tag):
        new_tag = tag.strip().lower() #Remove whitespace and make case insensitive
        if not new_tag:
            raise ValueError("Tag cannot be empty")
        self.tags.add(new_tag)

    def remove_tag(self, tag):
        self.tags.discard(tag.strip().lower())

    def has_tag(self, tag):
        return tag.strip().lower() in self.tags

class PlotMap(Tile):
    def __init__(self, name, id=None, links=None, plot_points=None, **kwargs):
        super().__init__("PlotMap", name, id, links)
        self.plot_points = plot_points if plot_points is not None else [] # List of plot points specific to PlotMap. Order = story order (not timeline)
        self.resolved_plot_points = [] #Cached resolved PlotTile objects

    def toDict(self):
        data = super().toDict()
        data.update({
            "plot_points": self.plot_points
        })
        return data

    #Method to resolve all the PlotMap's plot_points IDs to Tile objects
    def resolve_plot_points(self, registry):
        resolved = []

        for plot_id in self.plot_points:
            if plot_id in registry: #Registry maps IDs to Tile objects
                tile = registry[plot_id] #Get the PlotTile object from the registry
                resolved.append(tile)
            else:
                print(f"Warning: Plot Point ID {plot_id} not found in registry")

        self.resolved_plot_points = resolved #Stores resolved plot points PlotTiles
        return resolved #Stores resolved plot points PlotTiles.
    
    #Add a PlotTile to plot_points. Also bidirectionally links the PlotMap and PlotTile.
    def add_plot_point(self, plot_tile, project, index=None):
        if not isinstance(plot_tile, PlotTile):
            raise TypeError("plot_tile must be a PlotTile instance")
        if plot_tile.id in self.plot_points:
            raise ValueError(f"PlotTile {plot_tile.id} is already a plot point in this PlotMap")

        #Bidirectional linking
        self.add_link(plot_tile.id, project, "plot point") #Links plot_tile to the PlotMap. Also will check if plot_tile exists in project
        plot_tile.add_link(self.id, project, "plot point") #Links the PlotMap to plot_tile
        #^Resolved_links for both updated in add_link()

        if index is None:
            index = len(self.plot_points)
        if index < 0 or index > len(self.plot_points):
            raise IndexError(f"Index {index} out of range")
        
        #Update both plot_points and resolved_plot_points
        self.plot_points.insert(index, plot_tile.id)
        self.resolved_plot_points.insert(index, plot_tile)
        
    #Remove a PlotTile from plot_points. Also bidirectionally unlinks the PlotMap and PlotTile.
    def remove_plot_point(self, plot_tile):
        if not isinstance(plot_tile, PlotTile):
            raise TypeError("plot_tile must be a PlotTile instance")
        if plot_tile.id not in self.plot_points:
            raise ValueError(f"PlotTile {plot_tile.id} is not a plot point in this PlotMap")

        #Bidirectional unlinking
        self.remove_link(plot_tile.id, "plot point") #Unlinks plot_tile from the PlotMap
        plot_tile.remove_link(self.id, "plot point") #Unlinks the PlotMap from plot_tile

        index = self.plot_points.index(plot_tile.id)

        self.plot_points.pop(index) #Removes PlotTile ID from plot_points list
        self.resolved_plot_points.pop(index) #Removes PlotTile object from the resolved_plot_points

    #Move a plot_point by changing the plot_point at the old_index to the new_index
    def move_plot_point(self, old_index, new_index):
        max_index = len(self.plot_points)

        if not (0 <= old_index < max_index):
            raise IndexError("old_index out of range")
        if not (0 <= new_index < max_index):
            raise IndexError("new_index out of range")
        
        #Move PlotTile ID
        plot_tile_id = self.plot_points.pop(old_index)
        self.plot_points.insert(new_index, plot_tile_id)

        #Move resolved PlotTile object
        plot_tile = self.resolved_plot_points.pop(old_index)
        self.resolved_plot_points.insert(new_index, plot_tile)

class PlotTile(Tile):
    def __init__(self, name, id=None, links=None, description="", date="", location="", timeline_index=None, **kwargs):
        super().__init__("PlotTile", name, id, links)
        self.description = description
        self.date = date
        self.location = location
        self.timeline_index = timeline_index #Chronological order of this event in the Project world (not same as plot order). None = unplaced on timeline

    def toDict(self):
        data = super().toDict()
        data.update({
            "description": self.description,
            "date": self.date,
            "location": self.location,
            "timeline_index": self.timeline_index
        })
        return data

class CharacterTile(Tile):
    def __init__(self, name, id=None, links=None, description="", title="", backstory="", traits=None, race="", age=None, gender="", occupation="", **kwargs):
        super().__init__("CharacterTile", name, id, links)
        self.description = description
        self.title = title
        self.backstory = backstory
        self.traits = traits if traits is not None else [] # List of traits specific to CharacterTile
        self.race = race
        self.age = age
        self.gender = gender
        self.occupation = occupation

    def toDict(self):
        data = super().toDict()
        data.update({
            "description": self.description,
            "title": self.title,
            "backstory": self.backstory,
            "traits": self.traits,
            "race": self.race,
            "age": self.age,
            "gender": self.gender,
            "occupation": self.occupation
        })
        return data

class SettingTile(Tile):
    def __init__(self, name, id=None, links=None, description="", history="", **kwargs):
        super().__init__("SettingTile", name, id, links)
        self.description = description
        self.history = history

    def toDict(self):
        data = super().toDict()
        data.update({
            "description": self.description,
            "history": self.history
        })
        return data
    
#Define the type_map after all Tile subclasses have been defined to avoid NameError
Tile.type_map = {
        "PlotMap": PlotMap,
        "PlotTile": PlotTile,
        "CharacterTile": CharacterTile,
        "SettingTile": SettingTile
    } #Mapping of Tile types to their respective classes. Inherited by all Tile subclasses. Used in fromDict method
