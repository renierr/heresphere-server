import os
import time
import platform
from loguru import logger
from videos import get_static_directory
from globals import url_map, url_counter, find_url_info


def get_thumbnail(filename):
    base_name = os.path.basename(filename)
    thumbfile = os.path.join(os.path.dirname(filename), '.thumb', f"{base_name}.thumb.jpg")
    if not os.path.exists(thumbfile):
        return None
    relative_thumbfile = os.path.relpath(thumbfile, start=os.path.join(os.path.dirname(filename), '..')).replace('\\', '/')
    return f"/static/videos/{relative_thumbfile}"

def get_file_size_formatted(filename):
    size_bytes = os.path.getsize(filename)

    size_mb = size_bytes / (1024 * 1024)

    if size_mb < 1024:
        return f"{size_mb:.2f} MB"
    else:
        size_gb = size_mb / 1024
        return f"{size_gb:.2f} GB"

def format_duration(duration):
    hours = int(duration // 3600)
    minutes = int((duration % 3600) // 60)
    seconds = int(duration % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def get_creation_date(filename):
    if platform.system() == 'Windows':
        creation_time = os.path.getctime(filename)
    else:
        creation_time = os.path.getmtime(filename)

    readable_time = time.ctime(creation_time)
    return creation_time

def parse_youtube_filename(filename):
    parts = filename.split('___')
    logger.debug(parts)

    id_part = parts[0]
    title_part = parts[1]

    return id_part, title_part

def list_files():
    extracted_details = []

    for root, dirs, files in os.walk(os.path.join(get_static_directory(), 'videos')):
        # Exclude directories that start with a dot
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for filename in files:
            realfile = os.path.join(root, filename)
            partial = filename.endswith('.part')
            thumbnail = get_thumbnail(realfile) if not partial else None
            url_id, url_info = find_url_info(filename)

            if filename.count('___') == 1:
                id, title = parse_youtube_filename(filename)
                extracted_details.append({
                    'yt_id': id,
                    'title': title,
                    'thumbnail': thumbnail,
                    'filename': f"/static/videos/youtube/{filename}",
                    'created': get_creation_date(realfile),
                    'filesize': get_file_size_formatted(realfile),
                    'partial': partial,
                    'url_id': url_id,
                    'orig_link': url_info['url'] if url_info and 'url' in url_info else None,
                    'video_url': url_info['video_url'] if url_info and 'video_url' in url_info else None,
                    'downloaded_date': url_info['downloaded_date'] if url_info and 'downloaded_date' in url_info else None
                })
            else:
                extracted_details.append({
                    'yt_id': None,
                    'title': os.path.splitext(filename)[0],
                    'thumbnail': thumbnail,
                    'filename': f"/static/videos/direct/{filename}",
                    'created': get_creation_date(os.path.join(root, filename)),
                    'filesize': get_file_size_formatted(os.path.join(root, filename)),
                    'partial': partial,
                    'url_id': url_id,
                    'orig_link': url_info['url'] if url_info and 'url' in url_info else None,
                    'video_url': url_info['video_url'] if url_info and 'video_url' in url_info else None,
                    'downloaded_date': url_info['downloaded_date'] if url_info and 'downloaded_date' in url_info else None
                })

    return extracted_details