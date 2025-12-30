from Project import Project
from Tiles import PlotMap, PlotTile, CharacterTile, SettingTile
from pathlib import Path

def print_ok(msg):
    print("✅", msg)

def assert_true(condition, message):
    if not condition:
        raise AssertionError("❌ " + message)

# --- Stage 1: Create Project with tiles ---
project = Project()
map1 = PlotMap("Epic Story")
p1 = PlotTile("Battle One")
p2 = PlotTile("Battle Two")
char = CharacterTile("Arin")
place = SettingTile("Forest")

for t in [map1, p1, p2, char, place]:
    project.add_tile(t)

print_ok("Tiles created")

# --- Stage 2: Apply function to PlotTiles ---
def is_plot_tile(tile):
    return tile.tile_type == "PlotTile"

def add_important_tag(tile):
    tile.add_tag("important")

count = project.apply_to_tiles(is_plot_tile, add_important_tag)
assert_true(count == 2, "Should have applied to 2 PlotTiles")
assert_true("important" in p1.tags and "important" in p2.tags, "Tags not applied correctly")
print_ok("apply_to_tiles applied function to filtered tiles correctly")

# --- Stage 3: Apply function to all tiles ---
def add_test_tag(tile):
    tile.add_tag("test")

count_all = project.apply_to_tiles(lambda t: True, add_test_tag)
assert_true(count_all == 5, "Should have applied to all tiles")
for t in project.tiles.values():
    assert_true("test" in t.tags, f"Tile {t.name} missing 'test' tag")
print_ok("apply_to_tiles applied function to all tiles correctly")

# --- Stage 4: Save and reload project ---
save_path = Path("ApplyTestProject")
project.save(save_path)

loaded = Project.load(save_path)

# Check tags persisted
for tile_id, tile in loaded.tiles.items():
    if tile.tile_type == "PlotTile":
        assert_true("important" in tile.tags, f"{tile.name} missing 'important' tag after reload")
    assert_true("test" in tile.tags, f"{tile.name} missing 'test' tag after reload")

print_ok("apply_to_tiles changes persisted after save/load")

# --- Stage 5: Use apply_to_tiles to remove tags ---
def remove_test_tag(tile):
    tile.tags.discard("test")

count_removed = loaded.apply_to_tiles(lambda t: "test" in t.tags, remove_test_tag)
for tile in loaded.tiles.values():
    assert_true("test" not in tile.tags, f"{tile.name} still has 'test' tag after removal")

print_ok("apply_to_tiles can remove tags correctly")

print("\n🎉 ALL apply_to_tiles tests passed!")