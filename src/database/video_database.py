import os
from datetime import datetime
from typing import Optional
from database.database import Database, ReprMixin
from globals import get_data_directory, ID_NAME_SEPERATOR
from .video_table_functions import ForVideo
from .video_models import Videos, Downloads, VideoBase

class VideoDatabase(Database):
    """
    Database class for storing video data
    """
    def __init__(self):
        db_path = os.path.join(get_data_directory(), 'videos.db')
        super().__init__(db_path)
        VideoBase.metadata.create_all(self.engine)
        self.for_video_table = ForVideo(self)

    def list_downloads(self) -> list:
        session = self.get_session()
        return session.query(Downloads).all()

    def upsert_download(self, data) -> None:
        session = self.get_session()
        video = session.query(Downloads).filter_by(video_url=data['video_url']).first()
        if video:
            for key, value in data.items():
                setattr(video, key, value)
        else:
            video = Downloads(**data)
            session.add(video)

    def delete_download(self, video_path) -> None:
        session = self.get_session()
        download = session.query(Downloads).filter_by(video_path=video_path).first()
        if download:
            session.delete(download)

    def set_favorite(self, video_url, favorite) -> None:
        session = self.get_session()
        video = session.query(Downloads).filter_by(video_url=video_url).first()
        if video:
            video.favorite = favorite
        download = session.query(Downloads).filter_by(video_url=video_url).first()
        if download:
            download.favorite = favorite

    def change_title(self, video_url, title) -> None:
        session = self.get_session()
        video = session.query(Downloads).filter_by(video_url=video_url).first()
        if video:
            video.title = title
        download = session.query(Downloads).filter_by(video_url=video_url).first()
        if download:
            download.title = title

    def mark_download_failed(self, video_url) -> None:
        session = self.get_session()
        download = session.query(Downloads).filter_by(video_url=video_url).first()
        if download:
            download.failed = 1

    def next_download(self, url) -> tuple[str,Downloads]:
        """
        prepare the next download
        create a new download object if the url is not already in the database
        pre-fill the download object with some initial data

        :param url: the url to download
        :return: the download id and the download object
        """
        session = self.get_session()
        download_random_id = datetime.now().strftime('%Y%m%d%H%M%S')
        existing_download = session.query(Downloads).filter_by(original_url=url).first()
        if existing_download:
            download_random_id = existing_download.file_name.split(ID_NAME_SEPERATOR)[0]
            return download_random_id, existing_download
        else:
            name = f"{download_random_id}{ID_NAME_SEPERATOR}downloading"
            download = Downloads(video_url=name, original_url=url, file_name=name, download_date=int(datetime.now().timestamp()))
            session.add(download)
            session.commit()
            return download_random_id, download


video_db: Optional[VideoDatabase] = None
def init_video_database():
    global video_db
    video_db = VideoDatabase()

def get_video_db() -> VideoDatabase:
    if video_db is None:
        init_video_database()
    return video_db

