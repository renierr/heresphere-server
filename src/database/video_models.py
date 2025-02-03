from sqlalchemy import Column, Integer, String, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from .database import ReprMixin

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
