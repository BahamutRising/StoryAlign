import shutil, time, json
from pathlib import Path
from datetime import datetime, timezone

# --- Mock classes --- #
class Tile:
    def __init__(self, tile_id):
        self.id = tile_id
    def save(self, directory):
        path = directory / f"{self.id}.json"
        directory.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump({"id": self.id}, f)
    @staticmethod
    def load(path):
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return Tile(data["id"])

class Project:
    def __init__(self):
        self.project_name = "TestProject"
        self.last_modified = datetime.now(timezone.utc).isoformat()
        self.tiles = {f"tile_{i}": Tile(f"tile_{i}") for i in range(2)}
    @property
    def tile_count(self):
        return len(self.tiles)
    def _save_to_folder(self, root_folder):
        root = Path(root_folder)
        root.mkdir(parents=True, exist_ok=True)
        for tile in self.tiles.values():
            tile.save(root)
    def load_check(self, raise_on_error=False):
        return {"errors": [], "warnings": []}
    
    # --- Recovery Mode (simplified) --- #
    def _recovery_mode(self, root, temp, backup):
        candidates = []
        for path in [root, temp, backup]:
            if path.exists():
                try:
                    project = Project()
                    project.last_modified = datetime.now(timezone.utc).isoformat()
                    project.tiles = {f"tile_{i}": Tile(f"tile_{i}") for i in range(2)}
                    candidates.append((project, path))
                except:
                    continue
        if not candidates:
            return None
        # Pick newest based on last_modified
        candidates.sort(key=lambda tup: tup[0].last_modified, reverse=True)
        return candidates[0][0]

    # --- Save with recovery --- #
    def save(self, root_folder):
        root = Path(root_folder)
        temp = root.with_name(root.name + ".tmp") #Temporary save path as ProjectFolder.tmp
        backup = root.with_name(root.name + ".backup") #Backup path as ProjectFolder.backup

        if temp.exists() or backup.exists():
            print("Warning: Found leftover .tmp or .backup folder. Entering recovery mode")
            recovered_project = self._recovery_mode(root, temp, backup) #Recovery check. Returns most recent valid project if available. Returns None if none
            #If the current project is older than recovered, update self
            try:
                if recovered_project and datetime.fromisoformat(recovered_project.last_modified) > datetime.fromisoformat(self.last_modified):
                    print("Recovered a newer project. Updating current project to recovered state")
                    self.__dict__.update(recovered_project.__dict__) #Updates project instance with recovered data
            except Exception:
                pass #If last_modified is invalid or nothing was recovered, proceed with current in memory project

        #Run load_check to check project integrity
        load_check_report = self.load_check(raise_on_error=False)
        if load_check_report["errors"]:
            print(f"WARNING: Project has {len(load_check_report['errors'])} errors and may be corrupted. Save aborted")
            return False
        
        #Save to temp folder
        try:
            self._save_to_folder(temp)
        except Exception as error:
            print(f"CRITICAL: Error saving to temp folder: {error}")
            return False

        #Backup current project if it exists
        if root.exists():
            if backup.exists():
                try:
                    shutil.rmtree(backup) #Remove old backup
                except Exception as error:
                    print(f"Warning: Failed to remove old backup {backup}: {error}")
            try:
                time.sleep(0.1)
                root.rename(backup) #Rename current project folder to to backup
            except PermissionError:
                try:
                    shutil.move(str(root), str(backup))
                except (PermissionError, FileExistsError) as error:
                    print(f"Warning: Could not move root folder to backup: {error}")
            except FileExistsError:
                print(f"Warning: Backup {backup} already exists. Skipping backup rename") #Recovery mode might have failed to remove it
        
        #Promote temp to root project folder
        try:
            time.sleep(0.1)
            temp.rename(root)
        except PermissionError:
            try:
                shutil.move(str(temp), str(root))
            except (PermissionError, FileExistsError) as error:
                print(f"CRITICAL: Could not move temp folder to root: {error}")
                return False
        except FileExistsError as error:
            print(f"CRITICAL: Could not promote temp folder to root: {error}")
            return False

        #Cleanup leftover folders
        for folder in [temp, backup]:
            if folder.exists():
                try:
                    shutil.rmtree(folder)
                except Exception as error:
                    print(f"Warning: Could not remove leftover folder {folder}: {error}")

        return True

# --- Simulation Test --- #
def simulate_recovery():
    test_root = Path.cwd() / "project_sim_test"
    if test_root.exists():
        shutil.rmtree(test_root)
    test_root.mkdir()

    project = Project()

    print("\n--- First save ---")
    print(project.save(test_root))

    print("\n--- Modify project (simulate newer tile) ---")
    project.tiles["tile_2"] = Tile("tile_2")
    project.last_modified = datetime.now(timezone.utc).isoformat()

    print("\n--- Second save (creates temp, backup) ---")
    print(project.save(test_root))

    # Simulate crash: leave temp folder behind
    temp = test_root.with_name(test_root.name + ".tmp")
    if not temp.exists():
        shutil.copytree(test_root, temp)

    print("\n--- Simulate save with leftover temp (triggers recovery) ---")
    new_project = Project()
    new_project.tiles["tile_3"] = Tile("tile_3")
    new_project.last_modified = datetime.now(timezone.utc).isoformat()
    print(new_project.save(test_root))

    # Show final folder structure
    print("\n--- Final folder structure ---")
    for folder in test_root.parent.iterdir():
        if folder.is_dir():
            print(f"{folder.name}: {[f.name for f in folder.iterdir()]}")

simulate_recovery()