import shutil
from pathlib import Path
from datetime import datetime, timedelta
import time
from Project import Project

# # Create a test project (replace with your actual Project constructor)
# project = Project()
# project.project_name = "TestProjectBackend"
# project.last_modified = datetime.now().isoformat()
# project.project_id = "123"

# root_folder = Path("TestProjectBackend")

# # --- Clean up old test folders first ---
# for folder in [root_folder, root_folder.with_name(root_folder.name+".tmp"), root_folder.with_name(root_folder.name+".backup")]:
#     if folder.exists():
#         shutil.rmtree(folder)

# # --- Test normal save ---
# print(project.save(root_folder))  # Should create root_folder

# # --- Simulate crash: create a .tmp folder but don't promote ---
# temp_folder = root_folder.with_name(root_folder.name + ".tmp")
# project._save_to_folder(temp_folder)  # Save temp without promoting
# print("Simulated crash: .tmp folder created")

# # --- Save again, triggers recovery mode ---
# project.last_modified = datetime.now().isoformat()  # Update timestamp
# print(project.save(root_folder))  # Should recover and promote temp safely

# # --- Simulate multiple saves with leftover backup ---
# backup_folder = root_folder.with_name(root_folder.name + ".backup")
# backup_folder.mkdir(exist_ok=True)  # Fake leftover backup
# print(project.save(root_folder))  # Should clean up backup and save normally

# # Check final state
# print("Final folders:", [p.name for p in Path(".").iterdir() if p.is_dir()])





# Helper to create a fake project with given last_modified
def create_fake_project(name, last_modified):
    p = Project()
    p.project_name = name
    p.project_id = name + "_id"
    p.last_modified = last_modified
    return p

root_folder = Path("TestProjectBackend")

# --- Clean up any old test folders ---
for folder in [root_folder, root_folder.with_name(root_folder.name+".tmp"), root_folder.with_name(root_folder.name+".backup")]:
    if folder.exists():
        shutil.rmtree(folder)

# --- Create fake projects ---
now = datetime.now()
root_project = create_fake_project("RootProject", (now - timedelta(seconds=5)).isoformat())
tmp_project  = create_fake_project("TmpProject",  now.isoformat())
backup_project = create_fake_project("BackupProject", (now - timedelta(seconds=10)).isoformat())

# Save them to folders
root_project._save_to_folder(root_folder)
tmp_project._save_to_folder(root_folder.with_name(root_folder.name+".tmp"))
backup_project._save_to_folder(root_folder.with_name(root_folder.name+".backup"))

# --- Now attempt to save a new project that triggers recovery ---
new_project = create_fake_project("NewProject", (now + timedelta(seconds=1)).isoformat())
print("Before save:")
print("Folders:", [p.name for p in Path(".").iterdir() if p.is_dir()])

print(new_project.save(root_folder))  # Should trigger recovery, pick the newest valid project, and save successfully

# --- Check final state ---
print("After save:")
print("Folders:", [p.name for p in Path(".").iterdir() if p.is_dir()])

# Optionally, load the recovered project to verify it's the newest
recovered_project, report = Project.load(root_folder, strict=False)
print("Recovered project name:", recovered_project.project_name)
print("Recovered last_modified:", recovered_project.last_modified)
print("Load report:", report)