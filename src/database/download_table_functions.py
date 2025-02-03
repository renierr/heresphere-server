from datetime import datetime
from typing import Optional, List

from globals import ID_NAME_SEPERATOR
from .video_models import Downloads

class ForDownload:
    def __init__(self, db):
        self.db = db

    def list_downloads(self) -> list:
        session = self.db.get_session()
        return session.query(Downloads).all()

    def upsert_download(self, data) -> None:
        session = self.db.get_session()
        video = session.query(Downloads).filter_by(video_url=data['video_url']).first()
        if video:
            for key, value in data.items():
                setattr(video, key, value)
        else:
            video = Downloads(**data)
            session.add(video)

    def delete_download(self, video_path) -> None:
        session = self.db.get_session()
        download = session.query(Downloads).filter_by(video_path=video_path).first()
        if download:
            session.delete(download)

    def mark_download_failed(self, video_url) -> None:
        session = self.db.get_session()
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
        session = self.db.get_session()
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
