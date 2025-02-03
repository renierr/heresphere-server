from typing import Optional, List
from .video_models import Videos

class ForVideo:
    def __init__(self, db):
        self.db = db

    def upsert_video(self, video_url: str, video: Videos) -> Videos:
        session = self.db.get_session()
        result = session.query(Videos).filter_by(video_url=video_url).first()
        if result:
            for key, value in vars(video).items():
                if not key.startswith('_'):  # Skip keys starting with an underscore
                    setattr(result, key, value)
        else:
            result = session.add(video)
            session.commit()
        return result

    def get_video(self, video_url: str) -> Optional[Videos]:
        session = self.db.get_session()
        return session.query(Videos).filter_by(video_url=video_url).first()

    def delete_video(self, video_url: str) -> None:
        session = self.db.get_session()
        video = session.query(Videos).filter_by(video_url=video_url).first()
        if video:
            session.delete(video)

    def list_videos(self) -> List[Videos]:
        session = self.db.get_session()
        return session.query(Videos).all()