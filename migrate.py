import os
import shutil

from globals import get_data_directory, URL_MAP_JSON, get_application_path

def migrate():
    migrate_url_map()


def migrate_url_map():
    data_folder = get_data_directory()
    map_path = os.path.join(data_folder, URL_MAP_JSON)
    if os.path.exists(map_path):
        # already done this migration nothing to do
        return

    # look for file in root folder (where it previously reside)
    root_map_path = os.path.join(get_application_path(), URL_MAP_JSON)
    if not os.path.exists(root_map_path):
        # no file to migrate
        return

    # make sure data folder exists
    os.makedirs(data_folder, exist_ok=True)

    # move file to data folder
    shutil.move(root_map_path, map_path)
    print("Migrated URL map file")


