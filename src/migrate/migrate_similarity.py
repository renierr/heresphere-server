import os
import sqlite3

from globals import get_data_directory
from migrate.migrate_utils import already_migrated, track_migration


def migrate_similar_table_histogramm_phash():
    if not already_migrated('similar_table_histogram_phash_again'):
        track_migration('similar_table_histogram_phash_again')
        # drop similar table from videos.db - easiest way. will get created again on start of the app, Data is lost but not accessible anyway
        with sqlite3.connect(os.path.join(get_data_directory(), 'videos.db')) as conn:
            cursor = conn.cursor()
            cursor.execute('DROP TABLE IF EXISTS similarity')
            cursor.execute('VACUUM')
        print("Migrated similar table histogram and phash and hog")
