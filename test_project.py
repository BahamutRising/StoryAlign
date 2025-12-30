from Tiles import Tile, PlotMap, PlotTile, CharacterTile, SettingTile
from Project import Project
from pathlib import Path

# -------------------------------
# Stage 0: Setup
# -------------------------------
project = Project()

# Create some tiles
map1 = PlotMap(name="Epic Adventure")
plot1 = PlotTile(name="First Battle")
plot2 = PlotTile(name="Second Battle")
char1 = CharacterTile(name="Arin")
setting1 = SettingTile(name="Ancient Forest")
setting2 = SettingTile(name="Dragon Castle")

# -------------------------------
# Stage 1: Add tiles to project
# -------------------------------
print("\n--- Stage 1: Adding tiles ---")
project.add_tile(map1)
project.add_tile(plot1)
project.add_tile(plot2)
project.add_tile(char1)
project.add_tile(setting1)
project.add_tile(setting2)

for t in project.tiles.values():
    print(f"{t.tile_type}: {t.name}, ID: {t.id}")

# -------------------------------
# Stage 2: Add links
# -------------------------------
print("\n--- Stage 2: Linking tiles ---")
map1.add_link(plot1.id, project)
map1.add_link(plot2.id, project)
map1.add_link(setting1.id, project)
map1.add_link(setting2.id, project)

char1.add_link(plot1.id, project)  # Character linked to plot
char1.add_link(plot2.id, project)

# Print resolved links
map1.resolved_links = map1.resolve_links(project.tiles)
char1.resolved_links = char1.resolve_links(project.tiles)

print(f"Map '{map1.name}' links:")
for t in map1.resolved_links:
    print(f" - {t.tile_type}: {t.name}")

print(f"Character '{char1.name}' links:")
for t in char1.resolved_links:
    print(f" - {t.tile_type}: {t.name}")

# -------------------------------
# Stage 3: Plot points
# -------------------------------
print("\n--- Stage 3: Assign plot points ---")
map1.plot_points = [plot1.id, plot2.id]
map1.resolved_plot_points = map1.resolve_plot_points(project.tiles)

print(f"Map '{map1.name}' plot points:")
for t in map1.resolved_plot_points:
    print(f" - {t.tile_type}: {t.name}")

# -------------------------------
# Stage 4: Save project
# -------------------------------
print("\n--- Stage 4: Saving project ---")
project_root = Path("TestProject")
project.save(project_root, project_name="Epic Adventure Project")
print(f"Project saved to folder: {project_root.resolve()}")

# # -------------------------------
# # Stage 5: Load project
# # -------------------------------
# print("\n--- Stage 5: Loading project ---")
# loaded_project = Project.load(project_root)
# loaded_map = loaded_project.tiles[map1.id]

# # Check resolved links and plot points after load
# loaded_map.resolved_links = loaded_map.resolve_links(loaded_project.tiles)
# loaded_map.resolved_plot_points = loaded_map.resolve_plot_points(loaded_project.tiles)

# print(f"Loaded map '{loaded_map.name}' links:")
# for t in loaded_map.resolved_links:
#     print(f" - {t.tile_type}: {t.name}")

# print(f"Loaded map '{loaded_map.name}' plot points:")
# for t in loaded_map.resolved_plot_points:
#     print(f" - {t.tile_type}: {t.name}")