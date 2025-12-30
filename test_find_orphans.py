from Project import Project
from Tiles import PlotMap, PlotTile, CharacterTile, SettingTile

def assert_true(condition, message):
    if not condition:
        raise AssertionError("❌ " + message)

def print_ok(msg):
    print("✅", msg)

print("\n--- Stage 1: Build Project ---")
project = Project()

# Create tiles
map1 = PlotMap("Epic Story")
p1 = PlotTile("Battle One")
p2 = PlotTile("Battle Two")
char1 = CharacterTile("Arin")
char2 = CharacterTile("Bryn")
place = SettingTile("Forest")

# Add tiles to project
for t in [map1, p1, p2, char1, char2, place]:
    project.add_tile(t)

print_ok("Tiles created")

print("\n--- Stage 2: Link some tiles ---")
# Link map to plot tiles
map1.add_plot_point(p1, project)  # bidirectional linking
map1.add_plot_point(p2, project) # bidirectional linking

# Add some one-way links
char1.add_link(p1.id, project)

print_ok("Links created")

print("\n--- Stage 3: Test orphans ---")

# 3a: Incoming only
incoming_orphans = project.find_orphans(check_incoming=True, check_outgoing=False)
incoming_names = [t.name for t in incoming_orphans]
assert_true("Bryn" in incoming_names, "Bryn should be incoming orphan")
assert_true("Forest" in incoming_names, "Forest should be incoming orphan")
assert_true("Arin" in incoming_names, "Arin should be incoming orphan")
assert_true("Battle One" not in incoming_names, "Battle One should not be incoming orphan")

print_ok("Incoming orphans correct")

# 3b: Outgoing only
outgoing_orphans = project.find_orphans(check_incoming=False, check_outgoing=True)
outgoing_names = [t.name for t in outgoing_orphans]
assert_true("Bryn" in outgoing_names, "Bryn should be outgoing orphan")
assert_true("Forest" in outgoing_names, "Forest should be outgoing orphan")
assert_true("Battle Two" not in outgoing_names, "Battle Two should not be outgoing orphan")
assert_true("Battle One" not in outgoing_names, "Battle One should not be outgoing orphan")

print_ok("Outgoing orphans correct")

# 3c: Both incoming and outgoing
both_orphans = project.find_orphans(check_incoming=True, check_outgoing=True)
both_names = [t.name for t in both_orphans]
assert_true("Bryn" in both_names, "Bryn should be both orphan")
assert_true("Forest" in both_names, "Forest should be both orphan")
assert_true("Battle One" not in both_names, "Battle One should not be both orphan")
assert_true("Battle Two" not in both_names, "Battle Two should not be both orphan")
assert_true("Arin" not in both_names, "Arin should not be both orphan")

print_ok("Both incoming and outgoing orphans correct")

# 3d: Ignore types
orphans_ignore_chars = project.find_orphans(ignore_types=["CharacterTile"])
orphans_ignore_chars_names = [t.name for t in orphans_ignore_chars]
assert_true("Bryn" not in orphans_ignore_chars_names, "Bryn should be ignored")
assert_true("Forest" in orphans_ignore_chars_names, "Forest should still be orphan")
assert_true("Battle One" not in orphans_ignore_chars_names, "Battle One should not be orphan")

print_ok("Ignore types works")

# 3e: Ignore IDs
ignore_ids_set = [char2.id, place.id]
orphans_ignore_ids = project.find_orphans(ignore_ids=ignore_ids_set)
orphans_ignore_ids_names = [t.name for t in orphans_ignore_ids]
assert_true("Bryn" not in orphans_ignore_ids_names, "Bryn should be ignored by ID")
assert_true("Forest" not in orphans_ignore_ids_names, "Forest should be ignored by ID")
assert_true("Battle One" not in orphans_ignore_ids_names, "Battle One should not be orphan")

print_ok("Ignore IDs works")

print("\n🎉 All orphan detection tests passed!")