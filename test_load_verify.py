# stage5_load_verify.py
from Project import Project
from Tiles import PlotMap, CharacterTile, PlotTile, SettingTile

# Load project
project = Project.load("TestProject")
print("--- Stage 5: Load and verify project ---")

for tile in project.tiles.values():
    print(f"{tile.tile_type}: {tile.name}, ID: {tile.id}")
    
    # Resolve links
    resolved_links = tile.resolve_links(project.tiles)
    tile.resolved_links = resolved_links
    if resolved_links:
        print(f"Links for '{tile.name}':")
        for linked_tile in resolved_links:
            print(f" - {linked_tile.tile_type}: {linked_tile.name}")
    else:
        if tile.links:  # Only warn if there were supposed to be links
            for missing_id in tile.links:
                print(f"Warning: Link ID {missing_id} not found for tile '{tile.name}'")

    # Resolve plot points if PlotMap
    if isinstance(tile, PlotMap):
        resolved_plot_points = tile.resolve_plot_points(project.tiles)
        tile.resolved_plot_points = resolved_plot_points
        if resolved_plot_points:
            print(f"Plot points in '{tile.name}':")
            for pp in resolved_plot_points:
                print(f" - {pp.tile_type}: {pp.name}")
        else:
            if tile.plot_points:  # Only warn if there were supposed to be plot points
                for missing_pp in tile.plot_points:
                    print(f"Warning: Plot Point ID {missing_pp} not found for map '{tile.name}'")