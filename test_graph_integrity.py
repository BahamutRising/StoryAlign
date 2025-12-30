from Project import Project
from Tiles import PlotMap, PlotTile, CharacterTile, SettingTile

def assert_true(condition, message):
    if not condition:
        raise AssertionError("❌ " + message)

def print_ok(msg):
    print("✅", msg)


print("\n--- Stage 1: Build Project ---")
project = Project()

map1 = PlotMap("Epic Story")
p1 = PlotTile("Battle One")
p2 = PlotTile("Battle Two")
char = CharacterTile("Arin")
place = SettingTile("Forest")

for t in [map1, p1, p2, char, place]:
    project.add_tile(t)

print_ok("Tiles created")


print("\n--- Stage 2: Add Plot Points ---")
map1.add_plot_point(p1, project)
map1.add_plot_point(p2, project)

# Invariants
assert_true(p1.id in map1.plot_points, "p1 not in plot_points")
assert_true(map1.id in p1.links, "Map not linked from PlotTile")
assert_true(p1.id in map1.links, "PlotTile not linked from PlotMap")

print_ok("Plot point bidirectional links")


print("\n--- Stage 3: Add Character Link ---")
char.add_link(p1.id, project)

assert_true(p1.id in char.links, "Char not linked to PlotTile")
assert_true(char not in p1.resolved_links, "Should not be bidirectional")
assert_true(char.id not in p1.links, "Should not be bidirectional")

print_ok("One-way links behave correctly")


print("\n--- Stage 4: Resolved Objects Check ---")
assert_true(p1 in map1.resolved_plot_points, "p1 not in resolved_plot_points")
assert_true(map1 in p1.resolved_links, "map not in p1.resolved_links")
assert_true(p1 in map1.resolved_links, "p1 not in map1.resolved_links")

print_ok("Resolved caches are in sync")


print("\n--- Stage 5: Remove Plot Point ---")
map1.remove_plot_point(p1)

assert_true(p1.id not in map1.plot_points, "plot_points not updated")
assert_true(p1.id not in map1.links, "map still links to p1")
assert_true(p1 not in map1.resolved_plot_points, "resolved_plot_points stale")
assert_true(p1 not in map1.resolved_links, "resolved_links stale")
assert_true(map1.id not in p1.links, "p1 still links to map")
assert_true(map1 not in p1.resolved_links, "resolved_links stale")

print_ok("Removal kept graph consistent")


print("\n--- Stage 6: Save + Reload ---")
project.save("GraphTest", "Test Project")

# loaded = Project.load("GraphTest")

# m = next(t for t in loaded.tiles.values() if isinstance(t, PlotMap)) #Gets the first and (should be) only PlotMap, map1
# p = next(t for t in loaded.tiles.values() if isinstance(t, PlotTile)) #Gets the first PlotTile (should be p2)
# #^This is just finding one PlotMap and one PlotTile from the loaded project.
# assert_true(p not in m.resolved_plot_points, "Reloaded plot_points wrong")
# assert_true(p not in m.resolved_links, "Reloaded links wrong")
# assert_true(m not in p.resolved_links, "Reloaded links wrong")

# print_ok("Reloaded project rebuilt graph correctly")


# print("\n🎉 ALL GRAPH INVARIANTS PASSED")