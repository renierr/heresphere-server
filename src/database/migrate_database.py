import os
from sqlalchemy import Column, Integer, String, DateTime, func
from typing import Optional
from sqlalchemy.orm import declarative_base
from database.database import Database, ReprMixin
from globals import get_data_directory

MigrationBase = declarative_base()

# migrations table
class Migrations(MigrationBase, ReprMixin):
    __tablename__ = 'migrations'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    date = Column(DateTime, nullable=False, default=func.now())

class MigrationDatabase(Database):
    """
    Database class for storing migration data
    """
    def __init__(self):
        db_path = os.path.join(get_data_directory(), 'migrate.db')
        super().__init__(db_path)
        MigrationBase.metadata.create_all(self.engine)

    def upsert_migration(self, migration_name):
        session = self.get_session()
        migration = session.query(Migrations).filter_by(name=migration_name).first()
        if migration:
            setattr(migration, 'date', func.now())
        else:
            migration = Migrations(name=migration_name)
            session.add(migration)

    def get_migration(self, migration_name):
        return self.get_session().query(Migrations).filter_by(name=migration_name).first()


migration_db: Optional[MigrationDatabase] = None
def init_migration_database():
    global migration_db
    migration_db = MigrationDatabase()

def get_migration_db() -> MigrationDatabase:
    if migration_db is None:
        init_migration_database()
    return migration_db

