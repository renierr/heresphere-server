from datetime import datetime
from typing import Optional, List

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from .video_models import Videos, Similarity


class ForSimilarity:
    def __init__(self, db):
        self.db = db

    def update_features(self, video: Videos, features: bytes) -> None:
        session: Session = self.db.get_session()

        if not video or not video.video_url:
            return

        if inspect(video).transient:
            video = self.db.for_video_table.get_video(video.video_url)

        similarity = video.similarity
        if similarity:
            similarity.histogramm = features
            similarity.changed = datetime.now()
        else:
            similarity = Similarity(video=video, histogramm=features)
            session.add(similarity)
            video.similarity = similarity

    def get_similarity(self, video_url: str) -> Optional[Similarity]:
        session = self.db.get_session()
        return session.query(Similarity).filter_by(video_url=video_url).first()

    def delete_similarity(self, video_url: str) -> None:
        session = self.db.get_session()
        similarity = session.query(Similarity).filter_by(video_url=video_url).first()
        if similarity:
            session.delete(similarity)

    def list_similarity(self) -> List[Similarity]:
        session = self.db.get_session()
        return session.query(Similarity).all()