import os
import sqlite3
from globals import get_data_directory
from migrate.migrate_utils import already_migrated, track_migration

def migrate_drop_video_table():

    if not already_migrated('drop_video_table'):
        track_migration('drop_video_table')

        download_db_file = os.path.join(get_data_directory(), 'videos.db')
        if not os.path.exists(download_db_file):
            return # nothing to migrate

        # Connect to the old SQLite database
        conn = sqlite3.connect(download_db_file)
        cursor = conn.cursor()

        # only drop table if less then 3 entries
        cursor.execute('SELECT count(*) FROM videos')
        count = cursor.fetchone()[0]
        if count < 3:
            cursor.execute('DROP TABLE IF EXISTS videos')
        conn.close()



