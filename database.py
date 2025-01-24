import sqlite3
import os
from typing import Optional
from globals import get_data_directory

class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        self.connection = None

    def connect(self):
        if self.connection is None:
            self.connection = sqlite3.connect(self.db_path)
        return self.connection

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    def execute_query(self, query, params=None):
        if params is None:
            params = []
        cursor = self.connect().cursor()
        cursor.execute(query, params)
        self.connection.commit()
        return cursor

    def fetch_all(self, query, params=None):
        cursor = self.execute_query(query, params)
        return cursor.fetchall()

    def fetch_one(self, query, params=None):
        cursor = self.execute_query(query, params)
        return cursor.fetchone()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class MigrateDatabase(Database):
    def __init__(self):
        db_path = os.path.join(get_data_directory(), 'migrate.db')
        super().__init__(db_path)

    def upsert_migration(self, migration_name):
        query = '''
        INSERT OR REPLACE INTO migrations (id, migration_name)
        VALUES (
            (SELECT id FROM migrations WHERE migration_name = ?),
            ?
        )
        '''
        params = [migration_name, migration_name]
        self.execute_query(query, params)

    def get_migration(self, migration_name):
        query = '''
            SELECT * FROM migrations
            WHERE migration_name = ?
        '''
        params = [migration_name]
        return self.fetch_one(query, params)

class VideoDatabase(Database):
    def __init__(self):
        db_path = os.path.join(get_data_directory(), 'videos.db')
        super().__init__(db_path)

    def upsert_video(self, video_url, file_name, original_url=None, title=None, favorite=False, failed=False, download_date=None):
        query = '''
        INSERT OR REPLACE INTO videos (id, video_url, file_name, original_url, title, favorite, failed, download_date)
        VALUES (
            (SELECT id FROM videos WHERE video_url = ?),
            ?, ?, ?, ?, ?, ?, ?
        )
        '''
        params = [video_url, video_url, file_name, original_url, title, favorite, failed, download_date]
        self.execute_query(query, params)

    def set_favorite(self, video_path, favorite):
        query = '''
            UPDATE videos
            SET favorite = ?
            WHERE video_url = ?
        '''
        params = [favorite, video_path]
        self.execute_query(query, params)

    def get_video_by_path(self, video_path):
        query = '''
            SELECT * FROM videos
            WHERE video_url = ?
        '''
        params = [video_path]
        return self.fetch_one(query, params)


video_db: Optional[VideoDatabase] = None
def init_video_database():
    global video_db
    video_db = VideoDatabase()
    video_db.execute_query('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY,
            video_url TEXT NOT NULL UNIQUE ON CONFLICT IGNORE,
            file_name TEXT NOT NULL,
            original_url TEXT,
            title TEXT,
            download_date INTEGER,
            favorite BOOLEAN NOT NULL DEFAULT 0,
            failed BOOLEAN NOT NULL DEFAULT 0
        )
    ''')

def get_video_db() -> VideoDatabase:
    if video_db is None:
        init_video_database()
    return video_db

migrate_db: Optional[MigrateDatabase] = None
def init_migration_database():
    global migrate_db
    migrate_db = MigrateDatabase()
    migrate_db.execute_query('''
        CREATE TABLE IF NOT EXISTS migrations (
            id INTEGER PRIMARY KEY,
            migration_name TEXT NOT NULL UNIQUE ON CONFLICT IGNORE
        )
    ''')

def get_migration_db() -> MigrateDatabase:
    if migrate_db is None:
        init_migration_database()
    return MigrateDatabase()
