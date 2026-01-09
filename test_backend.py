from Project import Project
from Tiles import PlotMap, PlotTile, CharacterTile, SettingTile
from pathlib import Path
from datetime import datetime, timezone
import shutil
import time
import json

def assert_true(condition, message):
    if not condition:
        raise AssertionError("❌ " + message)

def print_ok(msg):
    print("✅", msg)


print("\n--- Stage 1: Build Project ---")
project = Project()
project.project_name = "Epic Adventure"
project.add_tag("epic")
project.add_tag("test_project")
project.author = "Gabriel"

map1 = PlotMap("Epic Story")
p1 = PlotTile("Battle One")
p2 = PlotTile("Battle Two")
char = CharacterTile("Arin")
place = SettingTile("Forest")
castle = SettingTile("Castle")

# Add tags to tiles
p1.add_tag("battle")
p1.add_tag("important")
p2.add_tag(" battle ")
char.add_tag("character")
place.add_tag(" setting")
castle.add_tag("setting ")

for t in [map1, p1, p2, char, place, castle]:
    project.add_tile(t)

print_ok("Tiles created and tags assigned")

print("\n--- Stage 2: Add Plot Points and Links ---")
map1.add_plot_point(p1, project)
map1.add_plot_point(p2, project)
char.add_link(p1.id, project)
place.add_link(p2.id, project)
castle.add_link(p2.id, project)

# Invariants
assert_true(p1.id in map1.plot_points, "p1 not in plot_points")
assert_true(any(link["target"] == map1.id for link in p1.links), "Map not linked from PlotTile")
assert_true(any(link["target"] == p1.id for link in map1.links), "PlotTile not linked from PlotMap")
assert_true(not any(link["target"] == char.id for link in p1.links), "CharacterTile link should not be bidirectional")
assert_true(p1 in char.resolved_links, "Resolved links should include p1 for char")

print_ok("Plot points and links set correctly")

print("\n--- Stage 3: Orphan Detection ---")

# ----- Baseline -----
#incoming = project.find_orphans(check_incoming=True, check_outgoing=False)
incoming = project.find_orphans(check_outgoing=False)
#outgoing = project.find_orphans(check_incoming=False, check_outgoing=True)
outgoing = project.find_orphans(check_incoming=False)
full = project.find_orphans(require_both=True)

incoming_names = {t.name for t in incoming}
outgoing_names = {t.name for t in outgoing}
full_names = {t.name for t in full}

# From graph analysis
assert_true(incoming_names == {"Arin", "Forest", "Castle"}, "Baseline incoming orphans wrong")
assert_true(len(outgoing_names) == 0, "Baseline outgoing orphans should be empty")
assert_true(len(full_names) == 0, "Baseline full orphans should be empty")

print_ok("Baseline orphan detection correct")


# ----- Break one important link: map1 → p2 -----
map1.remove_plot_point(p2)

# Recompute
incoming = project.find_orphans(check_incoming=True, check_outgoing=False)
outgoing = project.find_orphans(check_incoming=False, check_outgoing=True)
full = project.find_orphans(require_both=True)

incoming_names = {t.name for t in incoming}
outgoing_names = {t.name for t in outgoing}
full_names = {t.name for t in full}

# p2 still has incoming (place, castle) so not incoming orphan
# BUT p2 now has no outgoing → outgoing orphan
assert_true("Battle Two" in outgoing_names, "Battle Two should be outgoing orphan")

# p2 should NOT be incoming orphan yet
assert_true("Battle Two" not in incoming_names, "Battle Two should not be incoming orphan yet")

# Still no full orphans
assert_true(len(full_names) == 0, "Should be no full orphans yet")


# ----- Now break remaining incoming links to p2 -----
place.remove_link(p2.id)
castle.remove_link(p2.id)

incoming = project.find_orphans(check_incoming=True, check_outgoing=False)
outgoing = project.find_orphans(check_incoming=False, check_outgoing=True)
full = project.find_orphans(require_both=True)

incoming_names = {t.name for t in incoming}
outgoing_names = {t.name for t in outgoing}
full_names = {t.name for t in full}

# Now p2 has no incoming AND no outgoing
assert_true("Battle Two" in incoming_names, "Battle Two should now be incoming orphan")
assert_true("Battle Two" in outgoing_names, "Battle Two should still be outgoing orphan")
assert_true("Battle Two" in full_names, "Battle Two should be full orphan")

print_ok("Broken graph orphan detection correct")


# ----- Restore everything -----
map1.add_plot_point(p2, project)
place.add_link(p2.id, project)
castle.add_link(p2.id, project)

final_orphans = project.find_orphans(require_both=True)
assert_true(len(final_orphans) == 0, "No full orphans should remain after restoring")

print_ok("Stage 3 orphan detection passed")


print("\n--- Stage 4: Tag Selection and Bulk Operation ---")
battle_tiles = project.select_tiles(lambda t: "battle" in t.tags)
assert_true(set(t.id for t in battle_tiles) == set([p1.id, p2.id]), "Tag selection failed")

# Bulk operation example: add 'epic_battle' tag to all battle tiles
def add_epic_tag(tile):
    tile.tags.add("epic_battle")

count = project.apply_to_tiles(lambda t: "battle" in t.tags, add_epic_tag)
assert_true(count == 2, "apply_to_tiles count incorrect")
for t in battle_tiles:
    assert_true("epic_battle" in t.tags, "Bulk action did not apply tag")

print_ok("Tag selection and bulk operation work")


print("\n--- Stage 5: Graph Export ---")

graph_text = project.visualize_graph(export=False)
print(graph_text)
graph = project.visualize_graph(export=True)

# 1. Basic structure
assert_true(isinstance(graph, dict), "Exported graph should be a dict")
assert_true(len(graph) == project.tile_count, "Graph tile count mismatch")

# 2. Check every tile exists in graph
for tile in project.tiles.values():
    assert_true(tile.id in graph, f"{tile.name} missing from exported graph")

# 3. Check fields for each tile
for tile_id, data in graph.items():
    tile = project.tiles[tile_id]

    # Required keys
    assert_true("name" in data, "Missing name in graph entry")
    assert_true("tile_type" in data, "Missing tile_type in graph entry")
    assert_true("links" in data, "Missing links in graph entry")
    assert_true("tags" in data, "Missing tags in graph entry")

    # Correct values
    assert_true(data["name"] == tile.name, f"Name mismatch for {tile.name}")
    assert_true(data["tile_type"] == tile.tile_type, f"Type mismatch for {tile.name}")
    assert_true(set([link["target"] for link in data["links"]]) == set([link["target"] for link in tile.links]), f"Links mismatch for {tile.name}")
    assert_true(set(data["tags"]) == set(tile.tags), f"Tags mismatch for {tile.name}")

    # PlotMap-specific
    if isinstance(tile, PlotMap):
        assert_true("plot_points" in data, f"PlotMap {tile.name} missing plot_points")
        assert_true(set(data["plot_points"]) == set(tile.plot_points), f"Plot points mismatch for {tile.name}")
    else:
        assert_true("plot_points" not in data, f"Non-PlotMap {tile.name} should not have plot_points")

# 4. Spot-check important story structure
map_entry = graph[map1.id]
assert_true(set(map_entry["plot_points"]) == {p1.id, p2.id}, "Map plot points incorrect")

p1_entry = graph[p1.id]
assert_true(any(link["target"] == map1.id for link in p1_entry["links"]), "p1 should link back to map")

p2_entry = graph[p2.id]
assert_true(any(link["target"] == map1.id for link in p2_entry["links"]), "p2 should link back to map")

print_ok("Graph export matches project state")


print("\n--- Stage 6: Save ---")

# root folder for the project
root_folder = "TestProjectBackend"

# Cleanup any leftover folders
for folder in [root_folder, root_folder + ".tmp", root_folder + ".backup"]:
    path = Path(folder)
    if path.exists():
        shutil.rmtree(path)

# Initial save
print(project.save(root_folder))

# Simulate rapid consecutive saves with “crashes”
for i in range(5):
    # Update last_modified
    project.last_modified = datetime.now(timezone.utc).isoformat()

    # Simulate a crash by saving to .tmp but not promoting it
    temp = Path(root_folder + ".tmp")
    project._save_to_folder(temp)
    print(f"Simulated crash: .tmp folder created at {temp}")

    # Save normally (recovery mode should handle leftover .tmp)
    try:
        msg = "Success!" if project.save(root_folder) else "FAILURE"
        print(f"Save {i+1}: {msg}")
    except Exception as e:
        print(f"Save {i+1} failed: {e}")

    # Small delay to avoid Windows file locking issues
    time.sleep(0.2)

# Verify final folder state
final_folders = [f.name for f in Path(".").iterdir() if f.is_dir()]
print("Final folders after stress test:", final_folders)

test_folder = Path("TestProjectBackend")

# Cleanup from previous runs
for folder in [test_folder, test_folder.with_name(test_folder.name + ".tmp"),
                test_folder.with_name(test_folder.name + ".backup")]:
    if folder.exists():
        shutil.rmtree(folder)

# Create initial project
print("=== Initial save ===")
print("Did project save successfully:", project.save(test_folder))

# Simulate crash by creating a .tmp folder manually
tmp_folder = test_folder.with_name(test_folder.name + ".tmp")
if not tmp_folder.exists():
    project._save_to_folder(tmp_folder)
print(f"Simulated crash: .tmp folder created at {tmp_folder}")

# Save again to trigger recovery from leftover .tmp
print("=== Save after simulated crash ===")
print("Did project save successfully:", project.save(test_folder))

# Simulate leftover .backup from previous crash
backup_folder = test_folder.with_name(test_folder.name + ".backup")
if not backup_folder.exists():
    test_folder.rename(backup_folder)

# Create new project version
project.save(test_folder)  # normal save

# Corrupt last_modified in backup to simulate invalid timestamp
meta_file = backup_folder / "manifest.json"
if meta_file.exists():
    with open(meta_file, "r") as f:
        data = json.load(f)
    data["last_modified"] = "INVALID_TIMESTAMP"
    with open(meta_file, "w") as f:
        json.dump(data, f, indent=4)

# Save again to test recovery chooses newest valid project
print("=== Save with corrupted backup ===")
print("Did project save successfully:", project.save(test_folder))

# Final check: only the project folder should exist, tmp and backup removed
final_folders = [f.name for f in test_folder.parent.iterdir() if f.is_dir()]
print("Final folders after stress test:", final_folders)


print("\n--- Stage 7: Load ---")
# Load the project to check integrity
loaded, load_report, load_check_report = Project.load(test_folder, strict=False)
print("Recovered project name:", getattr(loaded, "project_name", "MISSING"))
print("Recovered last_modified:", getattr(loaded, "last_modified", "MISSING"))
print("Load check report:", load_check_report)

assert_true(len(load_check_report["errors"])==0, "Project failed integrity check:\n" + "\n".join(load_check_report["errors"]))
assert_true(len(load_check_report["warnings"])==0, "Project integrity check produced warnings:\n" + "\n".join(load_check_report["warnings"]))
print(loaded.author)

# Metadata check
assert_true(loaded.project_name == "Epic Adventure", "Project name mismatch")
assert_true(loaded.author == "Gabriel", "Author mismatch")
assert_true("epic" in loaded.tags, "Project tag missing")
assert_true("test_project" in loaded.tags, "Project tag missing")
assert_true(loaded.tile_count == len(project.tiles) == project.tile_count, "Tile count mismatch after load")

# Tile links and plot points
map_loaded = next(t for t in loaded.tiles.values() if isinstance(t, PlotMap))
p1_loaded = next(t for t in loaded.tiles.values() if isinstance(t, PlotTile) and t.name == "Battle One")
p2_loaded = next(t for t in loaded.tiles.values() if isinstance(t, PlotTile) and t.name == "Battle Two")
char_loaded = next(t for t in loaded.tiles.values() if isinstance(t, CharacterTile))

assert_true(p1_loaded.id in map_loaded.plot_points, "Plot point p1 missing after load")
assert_true(any(link["target"] == map_loaded.id for link in p1_loaded.links), "PlotMap link missing in PlotTile after load")
assert_true(char_loaded.id in loaded.tiles.keys(), "CharacterTile loaded")

# Tags persisted
assert_true("battle" in p1_loaded.tags, "Tile tag missing after load")
assert_true("epic_battle" in p2_loaded.tags, "Tile bulk tag missing after load")

print_ok("Save/load with metadata and tags works")


print("\n--- Stage 8: Orphans after Load ---")
# ----- Baseline -----
orphans_loaded = loaded.find_orphans()
assert_true(len(orphans_loaded) > 0, "Orphan detection failed after load")

incoming_loaded = loaded.find_orphans(check_outgoing=False)
outgoing_loaded = loaded.find_orphans(check_incoming=False)
full_loaded = loaded.find_orphans(require_both=True)

incoming_names_loaded = {t.name for t in incoming_loaded}
outgoing_names_loaded = {t.name for t in outgoing_loaded}
full_names_loaded = {t.name for t in full_loaded}

# From graph analysis
assert_true(incoming_names_loaded == {"Arin", "Forest", "Castle"}, "Baseline incoming orphans wrong")
assert_true(len(outgoing_names_loaded) == 0, "Baseline outgoing orphans should be empty")
assert_true(len(full_names_loaded) == 0, "Baseline full orphans should be empty")

print_ok("Baseline orphan detection correct")

print_ok("Orphan detection works after load")

print("\n=== Timeline Conflict Test ===")
TEST_ROOT = Path("TestProjectBackendTimeline")

# Clean slate
if TEST_ROOT.exists():
    shutil.rmtree(TEST_ROOT)

project = Project()
project.project_name = "TimelineTest"

# Create PlotTiles
t1 = PlotTile("Opening")
t2 = PlotTile("Inciting Incident")
t3 = PlotTile("Parallel Scene")

# Assign timeline indexes (force a conflict)
t1.timeline_index = 1
t2.timeline_index = 2
t3.timeline_index = 2   # <-- conflict on purpose

# Add to project
project.add_tile(t1)
project.add_tile(t2)
project.add_tile(t3)

# Create a PlotMap and add tiles
plot = PlotMap("Main Plot")
project.add_tile(plot)

plot.add_plot_point(t1, project)
plot.add_plot_point(t2, project)
plot.add_plot_point(t3, project)

# Save
print(project.save(TEST_ROOT))

# Reload project from disk
reloaded, load_report, load_check_report = Project.load(TEST_ROOT)

print("\nLoad check report:")
print(load_check_report)

# Validate expectations
if not load_check_report["warnings"]:
    print("❌ FAILED: No timeline conflict warning detected")
else:
    print("✅ Timeline warnings detected:")
    for w in load_check_report["warnings"]:
        print("  ", w)

print("\n🎉 ALL BACKEND TESTS PASSED")
