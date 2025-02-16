from datetime import datetime
from typing import Optional

from globals import ID_NAME_SEPERATOR
from .video_models import Downloads

class ForDownload:
    def __init__(self, db):
        self.db = db

    def list_downloads(self) -> list:
        session = self.db.get_session()
        return session.query(Downloads).all()

    def upsert_download(self, video_url: str, download: Downloads) -> Downloads:
        session = self.db.get_session()
        result = session.query(Downloads).filter_by(video_url=video_url).first()
        if result:
            for key, value in vars(download).items():
                if not key.startswith('_'):  # Skip keys starting with an underscore
                    setattr(result, key, value)
        else:
            download.video_url = video_url
            result = session.add(download)
            session.commit()
        return result

    def get_download(self, video_url: str) -> Optional[Downloads]:
        session = self.db.get_session()
        return session.query(Downloads).filter_by(video_url=video_url).first()

    def delete_download(self, video_path) -> None:
        session = self.db.get_session()
        download = session.query(Downloads).filter_by(video_url=video_path).first()
        if download:
            session.delete(download)

    def mark_download_failed(self, original_url) -> None:
        session = self.db.get_session()
        download = session.query(Downloads).filter_by(original_url=original_url).first()
        if download:
            download.failed = 1

    def next_download(self, url: str, title: str) -> tuple[str, Downloads]:
        """
        prepare the next download
        create a new download object if the url is not already in the database
        pre-fill the download object with some initial data

        :param url: the url to download
        :param title: the intermediate title of the video
        :return: the download id and the download object
        """
        session = self.db.get_session()
        download_random_id = datetime.now().strftime('%Y%m%d%H%M%S')
        existing_download = session.query(Downloads).filter_by(original_url=url).first()
        if existing_download:
            download_random_id = existing_download.file_name.split(ID_NAME_SEPERATOR)[0][:14]
            return download_random_id, existing_download
        else:
            name = f"{download_random_id}{ID_NAME_SEPERATOR}downloading"
            download = Downloads(video_url=name, original_url=url, file_name=name, title=title, download_date=int(datetime.now().timestamp()))
            session.add(download)
            session.commit()
            return download_random_id, download
