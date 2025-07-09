from database.migrate_database import get_migration_db

def already_migrated(migration_name):
    with get_migration_db() as db:
        return bool(db.get_migration(migration_name))


def track_migration(migration_name):
    with get_migration_db() as db:
        db.upsert_migration(migration_name)


def safe_add_column(cursor, table_name, column_name, column_type):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    if column_name not in columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

