from database.migrate_database import get_migration_db

def already_migrated(migration_name):
    with get_migration_db() as db:
        return bool(db.get_migration(migration_name))


def track_migration(migration_name):
    with get_migration_db() as db:
        db.upsert_migration(migration_name)
