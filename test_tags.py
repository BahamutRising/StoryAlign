from Project import Project
from Tiles import PlotTile, CharacterTile, SettingTile

def assert_true(condition, msg):
    if not condition:
        raise AssertionError("❌ " + msg)

def print_ok(msg):
    print("✅", msg)


print("\n--- Stage 1: Create project + tiles ---")
project = Project()
#project_tags?
project.project_name = "Tag Test Project"
project.tags = {"fantasy", "epic"}

p1 = PlotTile("Battle One")
p2 = PlotTile("Battle Two")
c1 = CharacterTile("Arin")
s1 = SettingTile("Forest")

for t in [p1, p2, c1, s1]:
    project.add_tile(t)

print_ok("Tiles created")


print("\n--- Stage 2: Add tags ---")
p1.add_tag("Battle")
p1.add_tag("Epic")
p2.add_tag("battle")
c1.add_tag("Hero ")
s1.add_tag(" Location")

assert_true("battle" in p1.tags, "battle tag missing")
assert_true("epic" in p1.tags, "epic tag missing")
assert_true("hero" in c1.tags, "hero tag missing")
assert_true("location" in s1.tags, "location tag missing")

print_ok("Tags normalized correctly")


print("\n--- Stage 3: find_tiles_by_tag ---")
battle_tiles = project.find_tiles_by_tag("battle")
hero_tiles = project.find_tiles_by_tag("hero")

battle_names = [t.name for t in battle_tiles]
hero_names = [t.name for t in hero_tiles]

assert_true("Battle One" in battle_names, "Battle One missing")
assert_true("Battle Two" in battle_names, "Battle Two missing")
assert_true("Arin" in hero_names, "Arin missing")

print_ok("find_tiles_by_tag works")


print("\n--- Stage 4: Save project ---")
project.save("TagTestProject")
print_ok("Project saved")


print("\n--- Stage 5: Load project ---")
loaded = Project.load("TagTestProject")

loaded_battles = loaded.find_tiles_by_tag("battle")
loaded_heroes = loaded.find_tiles_by_tag("hero")

loaded_battle_names = [t.name for t in loaded_battles]
loaded_hero_names = [t.name for t in loaded_heroes]

assert_true("Battle One" in loaded_battle_names, "Battle One lost after reload")
assert_true("Battle Two" in loaded_battle_names, "Battle Two lost after reload")
assert_true("Arin" in loaded_hero_names, "Hero tag lost after reload")

assert_true("fantasy" in loaded.tags, "Project tag fantasy lost")
assert_true("epic" in loaded.tags, "Project tag epic lost")

print_ok("Tags survived save/load")


print("\n🎉 TAG SYSTEM FULLY VERIFIED")