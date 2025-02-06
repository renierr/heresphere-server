from typing import Optional, List
from .video_models import Videos, Similarity


class ForSimilarity:
    def __init__(self, db):
        self.db = db

    def upsert_similarity(self, video_url: str, similarity: Similarity) -> Similarity:
        session = self.db.get_session()
        result = session.query(Similarity).filter_by(video_url=video_url).first()
        if result:
            for key, value in vars(similarity).items():
                if not key.startswith('_'):  # Skip keys starting with an underscore
                    setattr(result, key, value)
        else:
            similarity.video_url = video_url
            result = session.add(similarity)
            session.commit()
        return result

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