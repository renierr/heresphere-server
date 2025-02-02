import os
from sqlalchemy import Column, Integer, String, UniqueConstraint
from typing import Optional
from sqlalchemy.orm import declarative_base
from database.database import Database, ReprMixin
from globals import get_data_directory

VideoBase = declarative_base()

# videos table
class Videos(VideoBase, ReprMixin):
    __tablename__ = 'videos'
    id = Column(Integer, primary_key=True, autoincrement=True)
    path = Column(String, nullable=False, unique=True)
    source_url = Column(String)
    video_url = Column(String)
    file_name = Column(String)
    title = Column(String)
    download_id = Column(String)
    video_uid = Column(String)
    download_date = Column(Integer)
    favorite = Column(Integer, nullable=False, default=0)

class Downloads(VideoBase, ReprMixin):
    __tablename__ = 'downloads'
    id = Column(Integer, primary_key=True, autoincrement=True)
    video_url = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    original_url = Column(String)
    title = Column(String)
    download_date = Column(Integer)
    favorite = Column(Integer, nullable=False, default=0)
    failed = Column(Integer, nullable=False, default=0)
    __table_args__ = (
        UniqueConstraint('video_url', sqlite_on_conflict='IGNORE'),
    )

class VideoDatabase(Database):
    """
    Database class for storing video data
    """
    def __init__(self):
        db_path = os.path.join(get_data_directory(), 'videos.db')
        super().__init__(db_path)
        VideoBase.metadata.create_all(self.engine)

    def upsert_video(self, video_data):
        session = self.get_session()
        video = session.query(Videos).filter_by(path=video_data['path']).first()
        if video:
            for key, value in video_data.items():
                setattr(video, key, value)
        else:
            video = Videos(**video_data)
            session.add(video)

    def get_video(self, video_path):
        return self.get_session().query(Videos).filter_by(path=video_path).first()

    def delete_video(self, video_path):
        session = self.get_session()
        video = session.query(Videos).filter_by(path=video_path).first()
        if video:
            session.delete(video)

    def list_videos(self):
        session = self.get_session()
        return session.query(Videos).all()

    def upsert_download(self, data):
        session = self.get_session()
        video = session.query(Downloads).filter_by(video_url=data['video_url']).first()
        if video:
            for key, value in data.items():
                setattr(video, key, value)
        else:
            video = Downloads(**data)
            session.add(video)

video_db: Optional[VideoDatabase] = None
def init_video_database():
    global video_db
    video_db = VideoDatabase()

def get_video_db() -> VideoDatabase:
    if video_db is None:
        init_video_database()
    return video_db

