from __future__ import annotations

import datetime

from sqlalchemy import String, Integer, UniqueConstraint, LargeBinary, ForeignKey, func, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from .database import ReprMixin

class VideoBase(DeclarativeBase):
    pass

# videos table
class Videos(VideoBase, ReprMixin):
    __tablename__ = 'videos'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_url: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str] = mapped_column(String)
    file_name: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    download_id: Mapped[str] = mapped_column(String)
    video_uid: Mapped[str] = mapped_column(String)
    download_date: Mapped[int] = mapped_column(Integer)
    favorite: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    similarity: Mapped[Similarity] = relationship(back_populates='video')
    __table_args__ = (
        UniqueConstraint('video_url', sqlite_on_conflict='IGNORE'),
    )

class Downloads(VideoBase, ReprMixin):
    __tablename__ = 'downloads'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_url: Mapped[str] = mapped_column(String, nullable=False)
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    original_url: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    download_date: Mapped[int] = mapped_column(Integer)
    favorite: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    __table_args__ = (
        UniqueConstraint('video_url', sqlite_on_conflict='IGNORE'),
    )

class Similarity(VideoBase, ReprMixin):
    __tablename__ = 'similarity'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"))
    video: Mapped[Videos] = relationship(back_populates="similarity")
    features: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    changed: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())


