from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


# Define a mixin class that provides a __repr__ method and a to_dict method
class ReprMixin:
    """
    Mixin class that provides a __repr__ method and a to_dict method

    The to_dict method returns a dictionary representation of the object
    The __repr__ method returns a string representation of the object
    """
    def to_dict(self):
        return {col.name: getattr(self, col.name) for col in self.__table__.columns}

    def __repr__(self):
        attrs = ', '.join(f"{key}={value!r}" for key, value in self.to_dict().items())
        return f"<{self.__class__.__name__}({attrs})>"

# Base class for databases with common methods
class Database:
    """
    Base class for databases with common methods

    The __enter__ and __exit__ methods allow the database to be used as a context manager
    The new_session method creates a new session
    The get_session method returns the current session or creates a new one if needed
    """
    def __init__(self, db_path):
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}')
        self.SessionMaker = sessionmaker(bind=self.engine)
        self.session: Session | None = None

    def __enter__(self):
        self.session = self.SessionMaker() if self.session is None else self.session
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is None:  # No exception in the 'with' block
                try:
                    self.session.commit()
                except Exception as commit_exc:  # Catch exceptions during commit
                    self.session.rollback()  # Still try to rollback
                    raise commit_exc # re-raise the exception
            else:  # Exception occurred in the 'with' block
                try:
                    self.session.rollback()
                except Exception:  # Catch exceptions during rollback
                    pass # do not raise this exception, as the original one is more important
        finally:  # Ensure session is ALWAYS closed
            try:
                self.session.close()
                self.session = None
            except Exception:  # Catch exceptions during close
                self.session = None # set to None even if close fails to avoid future problems

    def new_session(self) -> Session:
        return self.SessionMaker()

    def get_session(self) -> Session:
        if self.session:
            return self.session
        return self.SessionMaker()

