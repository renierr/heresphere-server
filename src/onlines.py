from cache import cache
from database.video_database import get_video_db

#@cache(maxsize=128, ttl=3600)
def list_onlines():
    onlines = []

    with get_video_db() as db:
        on_list = db.for_online_table.list_online()
        for online in on_list:
            if online.video_url:
                onlines.append({
                    'url': online.video_url,
                    'original_url': online.original_url,
                    'title': online.title,
                    'thumbnail': online.thumbnail_url,
                    'date': online.date,
                    'resolution': online.resolution,
                    'stream_count': online.stream_count,
                })
    return sorted(onlines, key=lambda x: x['date'] or '', reverse=True)
