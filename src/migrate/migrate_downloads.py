import os
import sqlite3

from database.video_database import get_video_db
from globals import get_data_directory
from migrate.migrate_utils import already_migrated, track_migration


def migrate_download_db_to_videos():

    if not already_migrated('downloads_db_to_videos'):
        track_migration('downloads_db_to_videos')

        download_db_file = os.path.join(get_data_directory(), 'downloads.db')
        if not os.path.exists(download_db_file):
            return # nothing to migrate

        # Connect to the old SQLite database
        conn = sqlite3.connect(download_db_file)
        cursor = conn.cursor()

        # Fetch all data from the downloads table
        cursor.execute('SELECT * FROM downloads')
        all_download_data = cursor.fetchall()
        column_names = [description[0] for description in cursor.description]
        downloads = [dict(zip(column_names, row)) for row in all_download_data]
        conn.close()
        print(downloads)

        with get_video_db() as video_db:
            for download in downloads:
                video_data = {
                    'original_url': download.get('original_url'),
                    'video_url': download.get('video_url'),
                    'file_name': download.get('file_name'),
                    'title': download.get('title'),
                    'download_date': download.get('download_date'),
                    'favorite': download.get('favorite'),
                    'failed': download.get('failed')
                }
                video_db.upsert_download(video_data)
        #os.remove(os.path.join(get_data_directory(), 'downloads.db'))
