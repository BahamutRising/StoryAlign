# from Project import Project
# from Tiles import PlotMap, PlotTile, CharacterTile, SettingTile
# from pathlib import Path
# # import shutil

# def assert_true(condition, message):
#     if not condition:
#         raise AssertionError("❌ " + message)

# def print_ok(msg):
#     print("✅", msg)

# # # Clean up previous test folder if it exists
# test_folder = Path("MetaTestProject")
# # if test_folder.exists():
# #     shutil.rmtree(test_folder)

# print("\n--- Stage 1: Build Project with Metadata ---")
# project = Project()
# project.project_name = "My Adventure"
# project.description = "This is a test project for metadata."
# map1 = PlotMap("Epic Story")
# tile1 = PlotTile("Battle One")
# tile2 = PlotTile("Battle Two")
# char = CharacterTile("Arin")
# place = SettingTile("Forest")

# for t in [map1, tile1, tile2, char, place]:
#     project.add_tile(t)

# print_ok("Project and tiles created with metadata")

# print("\n--- Stage 2: Save Project ---")
# project.save(test_folder)
# manifest_path = test_folder / "manifest.json"
# assert_true(manifest_path.exists(), "Manifest file not created")

# print_ok("Project saved and manifest exists")

# print("\n--- Stage 3: Verify Manifest Metadata ---")
# import json
# with manifest_path.open("r", encoding="utf-8") as f:
#     manifest = json.load(f)

# assert_true(manifest["project_name"] == project.project_name, "Project name mismatch")
# assert_true(manifest["description"] == project.description, "Description mismatch")
# assert_true(manifest["tile_count"] == project.tile_count, "Tile count mismatch")
# assert_true("project_id" in manifest, "project_id missing")
# assert_true("created_at" in manifest, "created_at missing")
# assert_true("last_modified" in manifest, "last_modified missing")
# assert_true("version" in manifest, "version missing")
# assert_true("schema_version" in manifest, "schema_version missing")
# assert_true(len(manifest["tiles"]) == project.tile_count, "Tile entries missing in manifest")

# print_ok("Manifest metadata verified")

# print("\n--- Stage 4: Load Project and Verify ---")
# loaded = Project.load(test_folder)
# assert_true(loaded.project_name == project.project_name, "Loaded project name mismatch")
# assert_true(loaded.description == project.description, "Loaded description mismatch")
# assert_true(loaded.tile_count == len(project.tiles) == project.tile_count, "Loaded tile count mismatch")
# assert_true(loaded.project_id == project.project_id, "Loaded project_id mismatch")

# print_ok("Loaded project metadata verified")

# print("\n🎉 ALL METADATA TESTS PASSED")



from Project import Project
from Tiles import PlotMap, PlotTile
from pathlib import Path
#import shutil
import time

def assert_true(condition, message):
    if not condition:
        raise AssertionError("❌ " + message)

def print_ok(msg):
    print("✅", msg)

# Clean up previous test folder if it exists
test_folder = Path("MetaTestVersion")
# if test_folder.exists():
#     shutil.rmtree(test_folder)

print("\n--- Stage 1: Create Project ---")
project = Project()
project.project_name = "Version Test Project"
map1 = PlotMap("Epic Map")
tile1 = PlotTile("Battle One")

project.add_tile(map1)
project.add_tile(tile1)

print_ok("Project created with tiles")

print("\n--- Stage 2: First Save ---")
project.save(test_folder)
first_version = project.version
first_last_modified = project.last_modified

assert_true(first_version == 2, f"Version should be 2 after first save, got {first_version}")
assert_true(first_last_modified is not None, "last_modified should be set")

print_ok(f"First save complete: version={first_version}, last_modified={first_last_modified}")

# Wait a second to make a noticeable difference in last_modified
time.sleep(1)

print("\n--- Stage 3: Second Save ---")
project.save(test_folder)
second_version = project.version
second_last_modified = project.last_modified

assert_true(second_version == first_version + 1, f"Version should increment by 1. Expected {first_version + 1}, got {second_version}")
assert_true(second_last_modified > first_last_modified, "last_modified should be updated to a later timestamp")

print_ok(f"Second save complete: version={second_version}, last_modified={second_last_modified}")

print("\n--- Stage 4: Load Project and Verify ---")
loaded = Project.load(test_folder)
assert_true(loaded.version == second_version, "Loaded project version mismatch")
assert_true(loaded.last_modified == second_last_modified, "Loaded project last_modified mismatch")

print_ok("Loaded project version and last_modified verified")

print("\n🎉 ALL VERSION AND TIMESTAMP TESTS PASSED")
