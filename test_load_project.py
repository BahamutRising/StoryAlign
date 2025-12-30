# test_load_project_staged.py
from Project import Project
from Tiles import PlotMap, PlotTile, CharacterTile, SettingTile

def main():
    project_folder = "TestProject"
    print("\n--- Stage 5: Loading Project ---")
    project = Project.load(project_folder)
    print(f"Project loaded from folder: {project_folder}")

    # Stage 5-1: Print all tiles
    print("\n--- Stage 5-1: Tiles in project ---")
    for tile_id, tile in project.tiles.items():
        print(f"{tile.tile_type}: {tile.name}, ID: {tile.id}")

    # Stage 5-2: Print links for each tile
    print("\n--- Stage 5-2: Tile links ---")
    for tile_id, tile in project.tiles.items():
        if hasattr(tile, "resolved_links") and tile.resolved_links:
            print(f"{tile.tile_type} '{tile.name}' links:")
            for linked_tile in tile.resolved_links:
                print(f"  - {linked_tile.tile_type}: {linked_tile.name}")

    # Stage 5-3: Print plot points for PlotMap tiles
    print("\n--- Stage 5-3: PlotMap plot points ---")
    for tile in project.tiles.values():
        if isinstance(tile, PlotMap):
            print(f"Map '{tile.name}' plot points:")
            if hasattr(tile, "resolved_plot_points"):
                for plot_tile in tile.resolved_plot_points:
                    print(f"  - {plot_tile.tile_type}: {plot_tile.name}")
            else:
                print("  No plot points resolved.")

if __name__ == "__main__":
    main()