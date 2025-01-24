import os
import shutil

from database import get_downloads_db, get_migration_db
from globals import get_data_directory, URL_MAP_JSON, get_application_path, get_url_map, load_url_map


def migrate():
    migrate_tracking()
    migrate_url_map()
    from_url_map_to_database()
    rename_db_from_videos_to_download()

def already_migrated(migration_name):
    with get_migration_db() as db:
        return db.get_migration(migration_name) is not None

def track_migration(migration_name):
    with get_migration_db() as db:
        db.upsert_migration(migration_name)

def migrate_tracking():
    # make sure data fodler exists
    os.makedirs(get_data_directory(), exist_ok=True)
    if not already_migrated('tracking'):
        track_migration('tracking')
        print("Migrated tracking")

def migrate_url_map():
    if not already_migrated('url_map'):
        track_migration('url_map')
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

def from_url_map_to_database():
    if not already_migrated('url_map_to_db'):
        track_migration('url_map_to_db')
        load_url_map()
        url_map = get_url_map()
        with get_downloads_db() as db:
            for value in url_map.values():
                original_url = value.get('url')
                video_url = value.get('video_url')
                file_name = value.get('filename')
                title = value.get('title')
                favorite = value.get('favorite', False)
                failed = value.get('failed', False)
                download_date = value.get('downloaded_date', None)

                if not original_url or not video_url or not file_name:
                    continue
                db.upsert_video(original_url, video_url, file_name, title, favorite, failed, download_date)
        print("Migrated URL map to DB")


def rename_db_from_videos_to_download():
    if not already_migrated('rename_db_from_videos_to_downloads'):
        track_migration('rename_db_from_videos_to_downloads')
        db_path = os.path.join(get_data_directory(), 'videos.db')
        new_db_path = os.path.join(get_data_directory(), 'downloads.db')
        if os.path.exists(db_path):
            os.rename(db_path, new_db_path)
            print("Renamed videos.db to download.db")
