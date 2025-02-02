import os
from sqlalchemy import create_engine, Column, Integer, String

from typing import Optional
from database import Database
from globals import get_data_directory
from database import TableBase

# videos table
class Videos(TableBase):
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

class VideoDatabase(Database):
    """
    Database class for storing video data
    """
    def __init__(self):
        db_path = os.path.join(get_data_directory(), 'videos.db')
        super().__init__(db_path)

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

video_db: Optional[VideoDatabase] = None
def init_video_database():
    global video_db
    video_db = VideoDatabase()

def get_video_db() -> VideoDatabase:
    if video_db is None:
        init_video_database()
    return video_db

