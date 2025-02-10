from .migrate_similarity import migrate_similar_table_histogramm_phash
from .migrate_utils import already_migrated, track_migration


def migrate():
    migrate_tracking()
    migrate_similar_table_histogramm_phash()


def migrate_tracking():
    if not already_migrated('tracking'):
        track_migration('tracking')
        print("Migrated tracking")


