import os
from typing import Optional
from database.database import Database, ReprMixin
from globals import get_data_directory, ID_NAME_SEPERATOR
from .download_table_functions import ForDownload
from .similarity_table_functions import ForSimilarity
from .video_table_functions import ForVideo
from .video_models import Downloads, VideoBase, Videos


class VideoDatabase(Database):
    """
    Database class for storing video data
    """
    def __init__(self):
        db_path = os.path.join(get_data_directory(), 'videos.db')
        super().__init__(db_path)
        VideoBase.metadata.create_all(self.engine)
        self.for_video_table = ForVideo(self)
        self.for_download_table = ForDownload(self)
        self.for_similarity_table = ForSimilarity(self)

    def set_favorite(self, video_url, favorite) -> None:
        video = self.for_video_table.get_video(video_url)
        if video:
            video.favorite = favorite
        download = self.for_download_table.get_download(video_url)
        if download:
            download.favorite = favorite

    def change_title(self, video_url, title) -> None:
        video = self.for_video_table.get_video(video_url)
        if video:
            video.title = title
        download = self.for_download_table.get_download(video_url)
        if download:
            download.title = title

    def move_video(self, video_url: str, new_url: str) -> None:
        video = self.for_video_table.get_video(video_url)
        if video:
            video.video_url = new_url
        download = self.for_download_table.get_download(video_url)
        if download:
            download.video_url = new_url


video_db: Optional[VideoDatabase] = None
def init_video_database():
    global video_db
    video_db = VideoDatabase()

def get_video_db() -> VideoDatabase:
    if video_db is None:
        init_video_database()
    return video_db

