from .migrate_utils import already_migrated, track_migration


def migrate():
    migrate_tracking()


def migrate_tracking():
    if not already_migrated('tracking'):
        track_migration('tracking')
        print("Migrated tracking")

