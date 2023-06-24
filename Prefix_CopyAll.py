import shutil
from pathlib import Path

print("This will not work on subdirectories.")

copy_from = input("Folder to copy: ")
copy_to = input("Folder to copy to: ")
prefix = input("Prefix: ")
in_list = list(Path(copy_from).rglob("*"))
file = 0

for file in in_list:
    
    copyfile = file
    file = file.relative_to(copy_from)
    
    if prefix in str(file):        
        (copy_to / file.parent).mkdir(parents=True, exist_ok=True)
        shutil.copy(copy_from / file, copy_to / file)
