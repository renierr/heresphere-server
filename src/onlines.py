from cache import cache
from database.video_database import get_video_db
from database.video_models import Videos


@cache(maxsize=128, ttl=3600)
def list_onlines():
    onlines = []

    with (get_video_db() as db):
        existing_dict = dict(db.session.query(Videos.source_url, Videos.download_date
                                    ).filter(Videos.source_url != '').all())
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
                    'download_date': existing_dict.get(online.original_url),
                    'size': online.size,
                    'duration': online.duration,
                    'description': online.description,
                })
    return sorted(onlines, key=lambda x: x['date'] or '', reverse=True)

def delete_online(url: str):
    list_onlines.cache__clear()
    with get_video_db() as db:
        db.for_online_table.delete_online(url)
    return {'success': True, 'message': 'Online entry deleted successfully.'}
