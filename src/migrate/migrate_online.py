import os
import sqlite3

from globals import get_data_directory
from migrate.migrate_utils import already_migrated, track_migration, safe_add_column


def migrate_online_db_duration_description():
    if not already_migrated('online_db_duration_description'):
        track_migration('online_db_duration_description')
        # drop similar table from videos.db - easiest way. will get created again on start of the app, Data is lost but not accessible anyway
        with sqlite3.connect(os.path.join(get_data_directory(), 'videos.db')) as conn:
            cursor = conn.cursor()
            # Add columns for duration and description
            safe_add_column(cursor, "online", "size", "INTEGER")
            safe_add_column(cursor, "online", "duration", "INTEGER")
            safe_add_column(cursor, "online", "description", "TEXT")
            conn.commit()
        print("Migrated online table description and duration columns")
