from Tiles import Tile, PlotMap, PlotTile, CharacterTile, SettingTile, prefix_map
from pathlib import Path
import uuid
import json
from datetime import datetime, timezone
import shutil
import time
import traceback

class Project:
    def __init__(self):
        self.tiles = {} #This is the registry for the project with pairs of "ID": Tile object
        #Metadata:
        self.project_name = "Untitled Project"
        self.project_id = "proj_" + uuid.uuid4().hex[:8] #Creates an ID of proj_<8-digit hex code>
        self.description = ""
        self.author = ""
        self.last_editor = ""
        self.created_at = datetime.now(timezone.utc).isoformat() #Sets created_at to current time. This implementation is consistent across timezones
        self.last_modified = self.created_at
        self.version = 0 #Counts number of saves. Starts as version 0 until saving (becomes version 1)
        self.schema_version = 1 #Tracks the file saving and loading method used (allows backwards compatibility in future)
        self.tags = set()

    @property #Calling projectInstance.tile_count runs this
    def tile_count(self):
        return len(self.tiles)
    
    #Adds a Tile to the project, generating a unique ID if needed
    def add_tile(self, tile: Tile):
        #Assign unique ID if needed
        if tile.id is None:
            tile.id = self._generate_unique_id(tile.tile_type) #Generates unique ID if needed
        #Checks if the Tile's ID is already in registry. Keeps links intact
        elif tile.id in self.tiles:
            raise ValueError(f"Tile ID {tile.id} already exists in this project")
        
        self.tiles[tile.id] = tile #Adds the Tile to the registry

    #Removes a Tile from the project and all links to the Tile in the project
    def remove_tile(self, tile_id):
        if tile_id not in self.tiles:
            raise ValueError(f"Tile {tile_id} not found in project")
        
        #Remove all links to this Tile from all other Tiles in project
        for tile in self.tiles.values():
            if tile_id in tile.links:
                tile.remove_link(tile_id)
                print(f"Warning: Removed broken link from Tile {tile.id} to deleted Tile {tile_id}")

        #Remove the Tile from the registry
        del self.tiles[tile_id]

    #Returns a list of Tiles matching filter_function(tile) == True. Perfect for lambda
    def select_tiles(self, filter_function):
        return [tile for tile in self.tiles.values() if filter_function(tile)]
    
    #Applies an action function to all Tiles in the project that satisfy the filter function. Returns count of Tiles affected
    def apply_to_tiles(self, filter_function, action_function):
        tiles = self.tiles.values()
        count = 0
        for tile in tiles:
            if filter_function(tile): #Filters tiles
                action_function(tile) #Runs the action function on all filtered Tiles
                count += 1
        return count #Returns number of Tiles affected
    
    #Returns a list of Tile objects that are orphans
    def find_orphans(self, check_incoming=True, check_outgoing=True, require_both=False, ignore_types=None, ignore_ids=None):
        # find_orphans() - returns all orphans (incoming or outgoing (or both))
        # find_orphans(check_outgoing=False) - returns all incoming orphans
        # find_orphans(check_incoming=False) - returns all outgoing orphans
        # find_orphans(require_both=True) - returns all full orphans (both incoming and outgoing)
        ignore_types_set = set(ignore_types or []) #Returns set of ignore_types or an empty set 
        ignore_ids_set = set(ignore_ids or []) #Returns set of ignore_ids or an empty set
        orphans = []

        for tile in self.tiles.values():
            if tile.tile_type in ignore_types_set:
                continue #Filter out ignored types
            if tile.id in ignore_ids_set:
                continue #Filter out ignored IDs

            is_incoming_orphan = check_incoming and not any(tile.id in t.links for t in self.tiles.values()) #is an incoming orphan if the Tile is not linked BY anything
            is_outgoing_orphan = check_outgoing and not tile.links #is an outgoing orphan if the Tile links TO nothing

            conditions = []
            if check_incoming:
                conditions.append(is_incoming_orphan)
            if check_outgoing:
                conditions.append(is_outgoing_orphan)
            if not conditions: #If no conditions given, raise an error
                raise ValueError("Must check at least incoming or outgoing")
            
            if require_both:
                if all(conditions): #if all given conditions (incoming and outgoing) are True, add the tile (full orphan)
                    orphans.append(tile)
            else:
                if any(conditions):#if not requiring both, add any tile that meets one of the given conditions
                    orphans.append(tile)

        return orphans
    
    def set_author(self, name):
        if self.author:
            raise ValueError("Author already set")
        self.author = name

    def set_last_editor(self, name):
        self.last_editor = name

    def add_tag(self, tag):
        new_tag = tag.strip().lower()
        if not new_tag:
            raise ValueError("Tag cannot be empty")
        self.tags.add(new_tag)

    def remove_tag(self, tag):
        self.tags.discard(tag.strip().lower())

    def has_tag(self, tag):
        return tag.strip().lower() in self.tags

    #Saves a project to a folder by saving all Tiles in their respective folders within the project folder. Saves a manifest.json file as well
    def _save_to_folder(self, root_folder):
        root = Path(root_folder)
        root.mkdir(parents=True, exist_ok=True) #Ensures root folder exists. Creates it if not
        self.last_modified = datetime.now(timezone.utc).isoformat() #Updates to save time. This implementation is consistent across timezones
        self.version += 1 #Every save does version+=1

        #Manifest with useful metadata and for faster loading
        manifest = {
            "project_name": self.project_name,
            "project_id": self.project_id,
            "description": self.description,
            "author": self.author,
            "last_editor": self.last_editor,
            "created_at": self.created_at,
            "last_modified": self.last_modified,
            "version": self.version,
            "schema_version": self.schema_version,
            "tile_count": self.tile_count,
            "tiles": [],
            "project_tags": list(self.tags)
        }

        #Save each Tile
        for tile in self.tiles.values():
            tile_folder = root / tile.default_directories.get(tile.tile_type, ".") #ex: ProjectFolder/Tiles/PlotTiles. Defaults to project folder if type not found
            tile_folder.mkdir(parents=True, exist_ok=True) #Ensures subfolder exists. Creates it if not
            
            tile.save(directory=tile_folder) #Passes in proper directory to save the Tile. This saves it as <id>.json

            #Add tile entries to manifest
            relative_path = (tile_folder / f"{tile.id}.json").relative_to(root) #Ex: gets C:\...ProjectFolder\Tiles\PlotTiles\pt_000000.json relative to the ProjectFolder

            manifest["tiles"].append({
                "id": tile.id,
                "tile_type": tile.tile_type,
                "filepath": str(relative_path) #Ex: "filepath": Tiles\PlotTiles\pt_000000.json
            })

        #Save manifest file in root folder as manifest.json
        manifest_path = root / "manifest.json" #manifest_path is a Path object
        with manifest_path.open("w", encoding="utf-8") as file:
            json.dump(manifest, file, indent=4)

    #Safe save that makes a temp folder, saves all files, makes original folder a backup, replaces old project folder, and only then removes backup
    #Returns True if saved successfully. Returns False if failed.
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
            print(f"WARNING: Project has {len(load_check_report['errors'])} errors and may be corrupted. Save aborted: {load_check_report['errors']}")
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

    #Finds the most recent valid project file of all potential save files and promotes it to the project folder
    def _recovery_mode(self, root: Path, temp: Path, backup: Path):
        candidates = []

        #Attempt to load all possible project copies
        for path in [root, temp, backup]:
            if path.exists():
                try:
                    project, load_report, load_check_report = Project.load(path, strict=False)
                    #If a loaded project file has no errors (and its tile count matches the expected, unless using a blank project), it is a recovery candidate
                    if not load_report["errors"] and not load_check_report["errors"]:
                        if self.tile_count > 0:
                            if project.tile_count == self.tile_count:
                                candidates.append((project, path))
                            else:
                                print(f"Rejected {path}: tile count mismatch (expected {self.tile_count}, got {project.tile_count})")
                    else:
                        print(f"Skipped {path}: load_report={load_report}, load_check_report={load_check_report}")
                except Exception as error:
                    print(f"Failed to load {path}: {error}")

        if not candidates:
            print("ALL PROJECT COPIES ARE CORRUPTED - Proceeding with in-memory project")
            return None

        #Filter only candidates with valid last_modified
        valid_candidates = []
        for project, path in candidates:
            try:
                modified_time = datetime.fromisoformat(project.last_modified)
                valid_candidates.append((project, path, modified_time))
            except Exception:
                print(f"Invalid last_modified in {path}, skipping as candidate")
            
        if not valid_candidates:
            print("NO RECOVEREABLE PROJECT WITH VALID last_modified FOUND - Proceeding with in-memory project")
            return None
        
        #Sort by last_modified
        valid_candidates.sort(key=lambda tup: tup[2], reverse=True) #Newest first
        best_project, best_path, best_time = valid_candidates[0]
                    
        #Promote best project as root (unless root is the best path)
        final_root = root
        if best_path != root:
            print(f"Promoting {best_path} to root")
            if root.exists():
                try:
                    shutil.rmtree(root)
                except Exception as error:
                    print(f"Warning: Failed to remove old root {root}: {error}")
            try:
                time.sleep(0.1)
                best_path.rename(root)
                final_root = root
                print(f"Recovered project from: {best_path}")
            except PermissionError:
                shutil.move(str(best_path), str(root)) #Windows-friendly promoting method via copying
                final_root = root
                print(f"Recovered project from: {best_path}")
            except FileExistsError: #Runs this if the root wasn't removed
                final_root = best_path
                print(f"CRITICAL: Root could not be replaced. Keeping Recovered copy {best_path}")

        #Delete all other copies than best path
        for project, path in candidates:
            if path.exists() and path != final_root:
                try:
                    shutil.rmtree(path)
                except Exception as error:
                    print(f"Warning: Failed to remove old copy {path}: {error}")

        return best_project

    #Creates a Project object loaded with all the Tiles within its folder and resolves all Tile links and plot points.
    #Uses manifest.json to load, otherwise manually gathers files
    @staticmethod
    def _load_from_disk(root_folder):
        load_report = {
            "manifest_used": False,
            "fallback_used": False,

            "tiles_loaded_from_manifest": [],
            "tiles_missing_from_manifest": [],
            "tiles_recovered": [],
            "tiles_loaded_from_fallback": [],

            "warnings": [],
            "errors": [],
        }

        project = Project() #Creates an empty Project object
        root = Path(root_folder) #Root folder becomes safe Path object

        manifest_path = root / "manifest.json"
        loaded_tiles = []
        missing_tiles = []
        manifest_tile_count = None
        
        if manifest_path.exists(): #If manifest.json file exists, attempt manifest load if it has tiles
            load_report["manifest_used"] = True
            with manifest_path.open("r", encoding="utf-8") as file:
                manifest = json.load(file)
            
            #Load project metadata first (even if manifest is missing files). If not found, set to default metadata of a new project
            project.project_name = manifest.get("project_name", project.project_name)
            if manifest.get("project_name") is None:
                load_report["warnings"].append("Manifest missing project's 'project_name' attribute")
            project.project_id = manifest.get("project_id", project.project_id)
            if manifest.get("project_id") is None:
                load_report["warnings"].append("Manifest missing project's 'project_id' attribute")
            project.description = manifest.get("description", project.description)
            if manifest.get("description") is None:
                load_report["warnings"].append("Manifest missing project's 'description' attribute")
            project.author = manifest.get("author", project.author)
            if manifest.get("author") is None:
                load_report["warnings"].append("Manifest missing project's 'author' attribute")
            project.last_editor = manifest.get("last_editor", project.last_editor)
            if manifest.get("last_editor") is None:
                load_report["warnings"].append("Manifest missing project's 'last_editor' attribute")
            project.created_at = manifest.get("created_at", project.created_at)
            if manifest.get("created_at") is None:
                load_report["warnings"].append("Manifest missing project's 'created_at' attribute")
            project.last_modified = manifest.get("last_modified", project.last_modified)
            if manifest.get("last_modified") is None:
                load_report["warnings"].append("Manifest missing project's 'last_modified' attribute")
            project.version = manifest.get("version", project.version)
            if manifest.get("version") is None:
                load_report["warnings"].append("Manifest missing project's 'version' attribute")
            project.schema_version = manifest.get("schema_version", project.schema_version)
            if manifest.get("schema_version") is None:
                load_report["warnings"].append("Manifest missing project's 'schema_version' attribute")
            project.tags = set(manifest.get("project_tags", []))
            if manifest.get("project_tags") is None:
                load_report["warnings"].append("Manifest missing project's 'project_tags' attribute")

            manifest_tile_count = manifest.get("tile_count", None)
            if manifest_tile_count is None: #If the manifest does not have a tile count
                load_report["warnings"].append("Manifest missing project's 'tile_count' attribute")

            if "tiles" in manifest:
                for tile_dict in manifest.get("tiles"):
                    filepath = tile_dict.get("filepath") #Ex: Tiles/PlotTiles/pt_000000.json
                    if not filepath:
                        missing_tiles.append(tile_dict.get("id", "unknown"))
                        load_report["tiles_missing_from_manifest"].append(tile_dict.get("id", "unknown")) #Any tiles missing a filepath in the manifest are recorded
                        continue
                    
                    tile_path = root / filepath #Combines root folder and its filepath relative to root folder for complete path
                    try:
                        tile = Tile.load(tile_path)
                        loaded_tiles.append(tile)
                        load_report["tiles_loaded_from_manifest"].append(tile.id) #Any loaded tiles from manifest are recorded
                    except Exception as error:
                        missing_tiles.append(tile_dict.get("id", "unknown"))
                        load_report["tiles_missing_from_manifest"].append(tile_dict.get("id", "unknown")) #Any tiles that fail to load during manifest load are recorded
                        load_report["warnings"].append(f"{tile_path}: {error}\n{traceback.format_exc()}") #Warning shows exact line where error occurred
            else:
                #Fallback if manifest exists but is missing tiles list: manual file finding and loading
                load_report["fallback_used"] = True
                for json_file in root.rglob("*.json"): #Iterates over a list of all json files in the project root folder
                    try:
                        tile = Tile.load(json_file) #Loads a Tile object from json_file
                        project.add_tile(tile) #Adds loaded Tile object to created project's registry. Assigns ID if missing
                        load_report["tiles_loaded_from_fallback"].append(tile.id)
                    except Exception as error:
                        load_report["errors"].append(f"{json_file}: {error}\n{traceback.format_exc()}") #Error shows exact line where error occurred
                        continue
        else:
            #Fallback if manifest.json doesn't exist: manual file finding and loading
            load_report["fallback_used"] = True
            for json_file in root.rglob("*.json"): #Iterates over a list of all json files in the project root folder
                try:
                    tile = Tile.load(json_file) #Loads a Tile object from json_file
                    project.add_tile(tile) #Adds loaded Tile object to created project's registry. Assigns ID if missing
                    load_report["tiles_loaded_from_fallback"].append(tile.id)
                except Exception as error:
                    load_report["errors"].append(f"{json_file}: {error}\n{traceback.format_exc()}") #Error shows exact line where error occurred
                    continue

        if missing_tiles: #If the manifest existed but resulted in any missing tiles (unsucessful manifest)...
            missing_ratio = len(missing_tiles) / (len(missing_tiles) + len(loaded_tiles))
            if missing_ratio <= 0.30:
                #Recovers missing files via fallback scan if manifest load resulted in <=30% missing files
                
                #Adds successfully loaded tiles to project
                for tile in loaded_tiles:
                    project.add_tile(tile)

                #Loads all tiles with fallback scan
                load_report["fallback_used"] = True

                found_tiles = {}
                for json_file in root.rglob("*.json"):
                    try:
                        tile = Tile.load(json_file)

                        if tile.id in found_tiles:
                            load_report["warnings"].append(f"Duplicate tile ID {tile.id} found at {json_file}. Using last loaded version.")
                        
                        found_tiles[tile.id] = tile #Adds "id": Tile object pairs to found_tiles
                        load_report["tiles_loaded_from_fallback"].append(tile.id)
                    except Exception as error:
                        load_report["errors"].append(f"{json_file}: {error}\n{traceback.format_exc()}") #Error shows exact line where error occurred
                        continue
                
                #Add all recovered tiles (missing manifest load tiles found by fallback scan) to project
                recovered = []
                for tile_dict in manifest.get("tiles", []):
                    tile_id = tile_dict.get("id", "unknown")
                    if tile_id not in project.tiles and tile_id in found_tiles:
                        tile = found_tiles[tile_id]
                        project.add_tile(tile)
                        recovered.append(tile)
                        load_report["tiles_recovered"].append(tile.id)

                #Adds all files not found from manifest load that were found from fallback load to project
                for tile_id, tile in found_tiles.items():
                    if tile_id not in project.tiles:
                        project.add_tile(tile)
            else:
                #Does fallback scan if manifest load resulted in >30% missing files
                load_report["fallback_used"] = True
                for json_file in root.rglob("*.json"):
                    try:
                        tile = Tile.load(json_file)
                        project.add_tile(tile)
                        load_report["tiles_loaded_from_fallback"].append(tile.id)
                    except Exception as error:
                        load_report["errors"].append(f"{json_file}: {error}\n{traceback.format_exc()}") #Error shows exact line where error occurred
                        continue
        elif loaded_tiles: #If manifest existed and had no missing tiles, add loaded tiles to project (successul manifest load)
            for tile in loaded_tiles:
                project.add_tile(tile)

        if manifest_tile_count is not None: #If manifest existed and had a tile count
            if manifest_tile_count != project.tile_count:
                load_report["errors"].append(f"Manifest expected {manifest_tile_count} tiles but loaded {project.tile_count}")

        #Resolve all links for Tiles
        for tile in project.tiles.values(): #Grabs the Tile objects in registry
            tile.resolve_links(project.tiles) #Passes in project registry to resolve_links(), which also updates the tile's resolved_links

            #Resolve all plot points for PlotMap Tiles
            if isinstance(tile, PlotMap):
                tile.resolve_plot_points(project.tiles) #Updates resolved_plot_points attribute with resolved PlotTiles

        return project, load_report #returns loaded Project instance
    
    #UI-friendly load that also runs a load check
    @staticmethod
    def load(root_folder, strict=True):
        project, load_report = Project._load_from_disk(root_folder) #project is the loaded Project object from save folder

        if strict and load_report.get("errors"):
            raise AssertionError(load_report)
        
        load_check_report = project.load_check(raise_on_error=False)

        if strict:
            errors = load_check_report.get("errors")
            if errors:
                raise AssertionError("Project failed integrity check:\n" + "\n".join(errors))
        
        return project, load_report, load_check_report #returns a tuple of (loaded project object, load report dict of file loading issues, load check report dict of loaded project object errors and warnings)

    #Checks the internal consistency of the loaded project. If raise_on_error=False, errors are returned as a list of strs (if none, returns [])
    def load_check(self, raise_on_error=True):
        errors = []
        warnings = []

        project_name = "MISSING NAME"
        project_id = "MISSING ID"
        if hasattr(self, "project_name"):
            project_name = self.project_name
        if hasattr(self, "project_id"):
            project_id = self.project_id

        #Metadata checking        
        if not hasattr(self, "project_name"):
            errors.append(f"WARNING: Project ({project_id}) missing 'project_name' attribute")
        if not hasattr(self, "project_id"):
            errors.append(f"WARNING: Project {project_name} missing 'project_id' attribute")
        if not hasattr(self, "description"):
            warnings.append(f"Project {project_name} ({project_id}) missing 'description' attribute")
        if not hasattr(self, "author"):
            warnings.append(f"Project {project_name} ({project_id}) missing 'author' attribute")
        if not hasattr(self, "last_editor"):
            warnings.append(f"Project {project_name} ({project_id}) missing 'last_editor' attribute")

        has_created_at = True
        has_last_modified = True
        if not hasattr(self, "created_at"):
            warnings.append(f"Project {project_name} ({project_id}) missing 'created_at' attribute")
            has_created_at = False
        if not hasattr(self, "last_modified"):
            warnings.append(f"Project {project_name} ({project_id}) missing 'last_modified' attribute")
            has_last_modified = False

        if has_created_at and has_last_modified:
            try:
                created_date = datetime.fromisoformat(self.created_at)
                modified_date = datetime.fromisoformat(self.last_modified)
                if created_date > modified_date:
                    errors.append(f"Project {project_name} ({project_id}) created_at is after last_modified")
            except Exception as error:
                errors.append(f"Project {project_name} ({project_id}) has invalid datetime format in metadata: {error}")

        if not hasattr(self, "version"):
            warnings.append(f"Project {project_name} ({project_id}) missing 'version' attribute")
        else:
            if type(self.version) == int:
                if self.version < 0:
                    errors.append(f"Project {project_name} ({project_id}) version is negative: {self.version}")
            else:
                errors.append(f"Project {project_name} ({project_id}) version is not an int: {self.version}")
        if not hasattr(self, "schema_version"):
            errors.append(f"Project {project_name} ({project_id}) missing 'schema_version' attribute") #Error because important for loading
        else:
            if type(self.schema_version) == int:
                if self.schema_version < 0:
                    errors.append(f"Project {project_name} ({project_id}) schema version is negative: {self.schema_version}")
            else:
                errors.append(f"Project {project_name} ({project_id}) schema version is not an int: {self.schema_version}")

        #Tags checking
        if not hasattr(self, "tags"):
            warnings.append(f"Project {project_name} ({project_id}) missing 'tags' attribute")
        else:
            if not all(isinstance(tag, str) for tag in self.tags):
                errors.append(f"Project {project_name} ({project_id}) tags contain non-string values")

        #Tile registry consistency
        if not hasattr(self, "tiles"):
            errors.append(f"WARNING: PROJECT {project_name} ({project_id}) MISSING 'tiles' ATTRIBUTE!")
        else:
            for tile_id_key, tile in self.tiles.items():
                tile_name = "MISSING NAME"
                tile_id = "MISSING ID"
                if hasattr(tile, "name"):
                    tile_name = tile.name
                if hasattr(tile, "id"):
                    tile_id = tile.id
                if not hasattr(tile, "id"):
                    errors.append(f"WARNING: Tile {tile_name} ({tile_id}) missing 'id' attribute")
                if not hasattr(tile, "tile_type"):
                    errors.append(f"WARNING: Tile {tile_name} ({tile_id}) missing 'tile_type' attribute")
                if not hasattr(tile, "name"):
                    errors.append(f"WARNING: Tile {tile_name} ({tile_id}) missing 'name' attribute")

                if tile_id != "MISSING ID":
                    if tile.id != tile_id_key:
                        errors.append(f"Tile ID mismatch: {tile_name} tile.id={tile_id}, key={tile_id_key}")
                else:
                    errors.append(f"Tile ID mismatch: {tile_name} tile.id={tile_id}, key={tile_id_key}")

                if not hasattr(tile, "links"):
                    errors.append(f"WARNING: Tile {tile_name} ({tile_id}) missing 'links' attribute")
                if not hasattr(tile, "resolved_links"):
                    errors.append(f"WARNING: Tile {tile_name} ({tile_id}) missing 'resolved_links' attribute")
                if not hasattr(tile, "tags"):
                    warnings.append(f"Tile {tile_name} ({tile_id}) missing 'tags' attribute")

                #Links and resolved_links consistency
                if hasattr(tile, "links"):
                    for link_id in tile.links:
                        if link_id not in self.tiles:
                            errors.append(f"Tile {tile_name} ({tile_id}) links to nonexistent tile {link_id}")

                if hasattr(tile, "resolved_links"):
                    for resolved in tile.resolved_links:
                        resolved_name = "MISSING NAME"
                        if hasattr(resolved, "name"):
                            resolved_name = resolved.name
                        if hasattr(resolved, "id"):
                            if resolved.id not in self.tiles:
                                errors.append(f"Tile {tile_name} ({tile_id}) has resolved link to nonexistent tile {resolved_name} ({resolved.id})")

                #Check that all links IDs are in resolved_links IDs
                if hasattr(tile, "links") and hasattr(tile, "resolved_links"):
                    resolved_ids = set()
                    for resolved in tile.resolved_links:
                        if hasattr(resolved, "id"):
                            resolved_ids.add(resolved.id)

                    for link_id in tile.links:
                        if link_id not in resolved_ids:
                            errors.append(f"Tile {tile_name} ({tile_id}) has unresolved link {link_id}")

                #Check that all resolved_links IDs are in links IDs
                if hasattr(tile, "links") and hasattr(tile, "resolved_links"):
                    plot_id_set = set(tile.links)

                    for resolved in tile.resolved_links:
                        resolved_name = "MISSING NAME"
                        if hasattr(resolved, "name"):
                            resolved_name = resolved.name
                        if hasattr(resolved, "id"):
                            if resolved.id not in plot_id_set:
                                errors.append(f"Tile {tile_name} ({tile_id}) has extra resolved link {resolved_name} ({resolved.id}) not in links")

                #---TILE SPECIFIC CHECKING---

                #PlotMap checking
                if isinstance(tile, PlotMap):
                    if not hasattr(tile, "plot_points"):
                        errors.append(f"PlotMap {tile_name} ({tile_id}) missing 'plot_points' attribute")
                    else:
                        for plot_tile_id in tile.plot_points:
                            if plot_tile_id not in self.tiles:
                                errors.append(f"PlotMap {tile_name} ({tile_id}) has unknown plot point {plot_tile_id}")
                            else:
                                plot_tile = self.tiles[plot_tile_id]
                                plot_tile_name = "MISSING NAME"
                                if hasattr(plot_tile, "name"):
                                    plot_tile_name = plot_tile.name
                                #Check bidirectional link
                                if hasattr(plot_tile, "links"):
                                    if tile.id not in plot_tile.links:
                                        errors.append(f"PlotTile {plot_tile_name} ({plot_tile.id}) not linked back to PlotMap {tile_name} ({tile_id})")
                    #Check resolved plot points
                    if not hasattr(tile, "resolved_plot_points"):
                        errors.append(f"PlotMap {tile_name} ({tile_id}) missing 'resolved_plot_points' attribute")
                    else:
                        for resolved in tile.resolved_plot_points:
                            resolved_name = "MISSING NAME"
                            if hasattr(resolved, "name"):
                                resolved_name = resolved.name
                            if hasattr(resolved, "id"):
                                if resolved.id not in self.tiles:
                                    errors.append(f"PlotMap {tile_name} ({tile_id}) has resolved plot point to unknown tile {resolved_name} ({resolved.id})")

                    #Check that all plot point IDs are in resolved_plot_points IDs
                    if hasattr(tile, "plot_points") and hasattr(tile, "resolved_plot_points"):
                        resolved_ids = set()
                        for resolved in tile.resolved_plot_points:
                            if hasattr(resolved, "id"):
                                resolved_ids.add(resolved.id)

                        for plot_id in tile.plot_points:
                            if plot_id not in resolved_ids:
                                errors.append(f"PlotMap {tile_name} ({tile_id}) has unresolved plot point {plot_id}")

                    #Check that all resolved_plot_points IDs are in plot_points IDs
                    if hasattr(tile, "plot_points") and hasattr(tile, "resolved_plot_points"):
                        plot_id_set = set(tile.plot_points)

                        for resolved in tile.resolved_plot_points:
                            resolved_name = "MISSING NAME"
                            if hasattr(resolved, "name"):
                                resolved_name = resolved.name
                            if hasattr(resolved, "id"):
                                if resolved.id not in plot_id_set:
                                    errors.append(f"PlotMap {tile_name} ({tile_id}) has extra resolved plot point {resolved_name} ({resolved.id}) not in plot_points")

                #PlotTile checking
                if isinstance(tile, PlotTile):
                    #timeline_index checking
                    if not hasattr(tile, "timeline_index"):
                        errors.append(f"PlotTile {tile_name} ({tile_id}) missing 'timeline_index' attribute")
                    else:
                        if tile.timeline_index is not None:
                            if not isinstance(tile.timeline_index, int):
                                errors.append(f"PlotTile {tile_name} ({tile_id}) timeline_index is not an int")
                            elif tile.timeline_index < 0:
                                errors.append(f"PlotTile {tile_name} ({tile_id}) timeline_index is negative")
                    #Extra data checking    
                    if not hasattr(tile, "description"):
                        warnings.append(f"PlotTile {tile_name} ({tile_id}) missing 'description' attribute")
                    if not hasattr(tile, "date"):
                        warnings.append(f"PlotTile {tile_name} ({tile_id}) missing 'date' attribute")
                    if not hasattr(tile, "location"):
                        warnings.append(f"PlotTile {tile_name} ({tile_id}) missing 'location' attribute")

                #CharacterTile checking
                if isinstance(tile, CharacterTile):
                    if not hasattr(tile, "description"):
                        warnings.append(f"CharacterTile {tile_name} ({tile_id}) missing 'description' attribute")
                    if not hasattr(tile, "title"):
                        warnings.append(f"CharacterTile {tile_name} ({tile_id}) missing 'title' attribute")
                    if not hasattr(tile, "backstory"):
                        warnings.append(f"CharacterTile {tile_name} ({tile_id}) missing 'backstory' attribute")
                    if not hasattr(tile, "traits"):
                        warnings.append(f"CharacterTile {tile_name} ({tile_id}) missing 'traits' attribute")
                    if not hasattr(tile, "race"):
                        warnings.append(f"CharacterTile {tile_name} ({tile_id}) missing 'race' attribute")
                    if not hasattr(tile, "age"):
                        warnings.append(f"CharacterTile {tile_name} ({tile_id}) missing 'age' attribute")
                    if not hasattr(tile, "gender"):
                        warnings.append(f"CharacterTile {tile_name} ({tile_id}) missing 'gender' attribute")
                    if not hasattr(tile, "occupation"):
                        warnings.append(f"CharacterTile {tile_name} ({tile_id}) missing 'occupation' attribute")

                #SettingTile checking
                if isinstance(tile, SettingTile):
                    if not hasattr(tile, "description"):
                        warnings.append(f"SettingTile {tile_name} ({tile_id}) missing 'description' attribute")
                    if not hasattr(tile, "history"):
                        warnings.append(f"SettingTile {tile_name} ({tile_id}) missing 'history' attribute")

                #---TILE SPECIFIC CHECKING DONE---

        #Timeline conflict detection
        timeline_index_map = {} #Will be populated with "timeline_index #": list of PlotTiles with this timeline_index. Ex: {1: [pt_000000, pt000001], 2: [pt_000002]}
        for tile in self.tiles.values():
            if isinstance(tile, PlotTile) and tile.timeline_index is not None:
                timeline_index_map.setdefault(tile.timeline_index, []) #Creates a "timeline_index #": [] pair for each timeline_index
                timeline_index_map[tile.timeline_index].append(tile) #Adds every PlotTile with that timeline_index to the list for that timeline_index key

        for index, tiles in timeline_index_map.items():
            if len(tiles) > 1:
                plot_tile_ids = [plot_tile.id for plot_tile in tiles]
                warnings.append(f"Timeline Conflict: timeline_index {index} is used by PlotTiles {plot_tile_ids}")

        if errors and raise_on_error:
            raise AssertionError("Load check failed:\n" + "\n".join(errors))
        return {"errors": errors, "warnings": warnings} #Report any errors or warnings
    
    #Prints or exports the project graph. Simple text-based graph visualization. If export, keys are tile IDs, values are info dicts
    def visualize_graph(self, export=False):
        graph = {}
        for tile in self.tiles.values():
            tile_data = {
                "name": tile.name,
                "tile_type": tile.tile_type,
                "links": tile.links.copy(),
                "tags": list(tile.tags)
            }
            if isinstance(tile, PlotMap):
                tile_data["plot_points"] = tile.plot_points.copy()
            
            graph[tile.id] = tile_data

        if export:
            return graph #Serialized graph data dict exported

        #Return textual representation
        graph_str = "Project Graph:"
        for tile_id, info in graph.items():
            graph_str += f"\n- {info['name']} ({info['tile_type']}, id={tile_id})"
            if info["links"]:
                graph_str += f"\n  Links to: {', '.join(info['links'])}"
            if "plot_points" in info:
                graph_str += f"\n  Plot points: {', '.join(info['plot_points'])}"
            if info["tags"]:
                graph_str += f"\n  Tags: {', '.join(info['tags'])}"
        graph_str += f"\nTotal tiles: {len(graph)}"

        return graph_str
    
    #Private method to create unique ID for a Tile
    def _generate_unique_id(self, tile_type):
        prefix = prefix_map.get(tile_type, "unknown") # Selects prefix based on Tile type, default to "unknown" if type not found
        while True:
            new_id = f"{prefix}_{uuid.uuid4().hex[:6]}" #Generates an ID with the selected prefix and a random 6-character hex string
            if new_id not in self.tiles: #Checks if ID already exists in project registry. If so, generates new ID
                return new_id

    #Optional helper: links two Tiles bidirectionally
    def link_bidirectional(self, tile1, tile2):
        tile1.add_link(tile2.id, self)
        tile2.add_link(tile1.id, self)

    #Optional helper: unlinks two Tiles bidirectionally
    def unlink_bidirectional(self, tile1, tile2):
        tile1.remove_link(tile2.id)
        tile2.remove_link(tile1.id)