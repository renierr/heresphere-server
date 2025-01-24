import sqlite3
import os
from datetime import datetime
from typing import Optional
from globals import get_data_directory


def result_as_dict(cursor) -> dict:
    row = cursor.fetchone()
    if row is None:
        return {}
    columns = [column[0] for column in cursor.description]
    return dict(zip(columns, row))


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

    def fetch_all(self, query, params=None) -> list:
        if params is None:
            params = []
        cursor = self.execute_query(query, params)
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

    def fetch_one(self, query, params=None) -> dict:
        if params is None:
            params = []
        cursor = self.execute_query(query, params)
        return result_as_dict(cursor)

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

class DownloadsDatabase(Database):
    def __init__(self):
        db_path = os.path.join(get_data_directory(), 'downloads.db')
        super().__init__(db_path)

    def upsert(self, *, video_url, file_name, original_url=None, title=None, favorite=False, failed=False, download_date=None):
        query = '''
        INSERT OR REPLACE INTO downloads (id, video_url, file_name, original_url, title, favorite, failed, download_date)
        VALUES (
            (SELECT id FROM downloads WHERE video_url = ?),
            ?, ?, ?, ?, ?, ?, ?
        )
        '''
        params = [video_url, video_url, file_name, original_url, title, favorite, failed, download_date]
        self.execute_query(query, params)

    def set_favorite(self, video_path, favorite):
        query = '''
            UPDATE downloads
            SET favorite = ?
            WHERE video_url = ?
        '''
        params = [favorite, video_path]
        self.execute_query(query, params)

    def find_by_path(self, video_path) -> dict:
        query = '''
            SELECT * FROM downloads
            WHERE video_url = ?
        '''
        params = [video_path]
        return self.fetch_one(query, params)

    def find_by_original_url(self, original_url) -> dict:
        query = '''
            SELECT * FROM downloads
            WHERE original_url = ?
        '''
        params = [original_url]
        return self.fetch_one(query, params)

    def store_download(self, *, url, video_url, filename, title) -> dict:
        download_date = int(datetime.now().timestamp())
        query = '''
        INSERT OR REPLACE INTO downloads (id, video_url, file_name, original_url, title, download_date)
        VALUES (
            (SELECT id FROM downloads WHERE original_url = ?),
            ?, ?, ?, ?, ?
        )
        '''
        params = [url, video_url, filename, url, title, download_date]

        cursor = self.execute_query(query, params)
        return result_as_dict(cursor)



download_db: Optional[DownloadsDatabase] = None
def init_downloads_database():
    global download_db
    download_db = DownloadsDatabase()
    download_db.execute_query('''
        CREATE TABLE IF NOT EXISTS downloads (
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

def get_downloads_db() -> DownloadsDatabase:
    if download_db is None:
        init_downloads_database()
    return download_db

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
