import os
import shutil
import threading

from bus import push_text_to_client
from database import get_migration_db
from globals import get_data_directory, URL_MAP_JSON, get_application_path, VideoFolder


def migrate():
    migrate_tracking()
    migrate_url_map()
    migrate_fill_ai_features()

def already_migrated(migration_name):
    with get_migration_db() as db:
        return bool(db.get_migration(migration_name))

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


def migrate_fill_ai_features_thread():
    from similar import fill_db_with_features
    for state, local_video_path, _ in fill_db_with_features(VideoFolder.library):
        if state == 'start':
            push_text_to_client(f"Processing AI features for {local_video_path}")
        if state == 'exising':
            push_text_to_client(f"AI features already exist for {local_video_path}")
        if state == 'new':
            push_text_to_client(f"Created AI features for {local_video_path}")

def migrate_fill_ai_features():
    if not already_migrated('fill_ai_features'):
        track_migration('fill_ai_features')
        thread = threading.Thread(target=migrate_fill_ai_features_thread)
        thread.start()


