import os
import shutil
import subprocess

def collect_dist_files():
    datas = []
    static_dir = 'static'
    exclude_dirs = ['videos', 'library']

    for root, dirs, files in os.walk(static_dir):
        for dir_name in exclude_dirs:
            if dir_name in dirs:
                dirs.remove(dir_name)
        for file in files:
            file_path = os.path.join(root, file)
            datas.append(file_path)
    print(datas)
    return datas

def copy_with_structure(source_files, dist_folder):
    for file in source_files:
        dest_path = os.path.join(dist_folder, file)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.copy(file, dest_path)
        print(f"Copied {file} to {dest_path}")

# Run PyInstaller
subprocess.run(['pyinstaller', 'main.spec'])

# Define source and destination paths
source_files = collect_dist_files()
dist_folder = 'dist'

# Copy files to the dist folder while maintaining directory structure
copy_with_structure(source_files, dist_folder)

print("Build completed and files copied to dist folder.")
