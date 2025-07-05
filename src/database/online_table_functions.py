from datetime import datetime
from typing import Optional

from globals import ID_NAME_SEPERATOR
from .video_models import Online

class ForOnline:
    def __init__(self, db):
        self.db = db

    def list_online(self) -> list:
        session = self.db.get_session()
        return session.query(Online).all()

    def upsert_online(self, video_url: str, online: Online) -> Online:
        session = self.db.get_session()
        result = session.query(Online).filter_by(original_url=video_url).first()
        if result:
            for key, value in vars(online).items():
                if not key.startswith('_'):  # Skip keys starting with an underscore
                    setattr(result, key, value)
            # increase the stream count
            result.stream_count += 1
        else:
            online.original_url = video_url
            result = session.add(online)
            session.commit()
        return result

    def get_online(self, video_url: str) -> Optional[Online]:
        session = self.db.get_session()
        return session.query(Online).filter_by(video_url=video_url).first()

    def delete_online(self, video_path) -> None:
        session = self.db.get_session()
        download = session.query(Online).filter_by(video_url=video_path).first()
        if download:
            session.delete(download)

    def next_online(self, url: str, title: str) -> tuple[str, Online]:
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
        existing_download = session.query(Online).filter_by(original_url=url).first()
        if existing_download:
            existing_download.failed = 0
            download_random_id = existing_download.file_name.split(ID_NAME_SEPERATOR)[0][:14]
            return download_random_id, existing_download
        else:
            name = f"{download_random_id}{ID_NAME_SEPERATOR}online"
            download = Online(video_url=name, original_url=url, title=title, date=int(datetime.now().timestamp()))
            session.add(download)
            session.commit()
            return download_random_id, download
