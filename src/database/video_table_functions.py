from typing import Optional, List
from .video_models import Videos

class ForVideo:
    def __init__(self, db):
        self.db = db

    def upsert_video(self, video_data: dict) -> None:
        session = self.db.get_session()
        video = session.query(Videos).filter_by(path=video_data['path']).first()
        if video:
            for key, value in video_data.items():
                setattr(video, key, value)
        else:
            video = Videos(**video_data)
            session.add(video)

    def get_video(self, video_path: str) -> Optional[Videos]:
        session = self.db.get_session()
        return session.query(Videos).filter_by(path=video_path).first()

    def delete_video(self, video_path: str) -> None:
        session = self.db.get_session()
        video = session.query(Videos).filter_by(path=video_path).first()
        if video:
            session.delete(video)

    def list_videos(self) -> List[Videos]:
        session = self.db.get_session()
        return session.query(Videos).all()