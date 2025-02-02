import sqlite3
import os
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from globals import get_data_directory, ID_NAME_SEPERATOR


# Define a mixin class that provides a __repr__ method and a to_dict method
class ReprMixin:
    """
    Mixin class that provides a __repr__ method and a to_dict method

    The to_dict method returns a dictionary representation of the object
    The __repr__ method returns a string representation of the object
    """
    def to_dict(self):
        return {col.name: getattr(self, col.name) for col in self.__table__.columns}

    def __repr__(self):
        attrs = ', '.join(f"{key}={value!r}" for key, value in self.to_dict().items())
        return f"<{self.__class__.__name__}({attrs})>"

# Base class for databases with common methods
class Database:
    """
    Base class for databases with common methods

    The __enter__ and __exit__ methods allow the database to be used as a context manager
    The new_session method creates a new session
    The get_session method returns the current session or creates a new one if needed
    """
    def __init__(self, db_path):
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}')
        self.Session = sessionmaker(bind=self.engine)
        self.session = None

    def __enter__(self):
        self.session = self.Session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.session.commit()
        else:
            self.session.rollback()
        self.session.close()
        self.session = None

    def new_session(self):
        return self.Session()

    def get_session(self):
        if self.session:
            return self.session
        return self.Session()


def result_as_dict(cursor) -> dict:
    row = cursor.fetchone()
    if row is None:
        return {}
    columns = [column[0] for column in cursor.description]
    return dict(zip(columns, row))

# deprecated class changed to Database
class DatabaseOld:
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


class DownloadsDatabase(DatabaseOld):
    def __init__(self):
        db_path = os.path.join(get_data_directory(), 'downloads.db')
        super().__init__(db_path)


class SimilarityDatabase(DatabaseOld):
    def __init__(self):
        db_path = os.path.join(get_data_directory(), 'similarity.db')
        super().__init__(db_path)

    def upsert_similarity(self, *, video_path, image_path, features):
        query = '''
        INSERT OR IGNORE INTO features (video_path, image_path, features) VALUES (?, ?, ?)
        '''
        params = [video_path, image_path, features.tobytes()]
        self.execute_query(query, params)

    def get_features(self, video_path) -> dict:
        query = '''
            SELECT features FROM features WHERE video_path = ?
        '''
        params = [video_path]
        return self.fetch_one(query, params)

similarity_db: Optional[SimilarityDatabase] = None
def init_similarity_database():
    global similarity_db
    similarity_db = SimilarityDatabase()
    similarity_db.execute_query('''
        CREATE TABLE IF NOT EXISTS features (
            id INTEGER PRIMARY KEY,
            video_path TEXT NOT NULL UNIQUE ON CONFLICT IGNORE,
            image_path TEXT NOT NULL UNIQUE ON CONFLICT IGNORE,
            features BLOB NOT NULL
        )
    ''')

def get_similarity_db() -> SimilarityDatabase:
    if similarity_db is None:
        init_similarity_database()
    return similarity_db



