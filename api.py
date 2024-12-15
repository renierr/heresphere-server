import os
import time
import platform
from os.path import devnull

from loguru import logger

from bus import push_text_to_client
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


import subprocess

def generate_thumbnail(video_path, thumbnail_path):
    try:
        # Use ffmpeg to generate a thumbnail
        with open(os.devnull, 'w') as devnull:
            subprocess.run([
                'ffmpeg', '-i', video_path, '-vf', 'thumbnail', '-ss', '00:00:10.000', '-frames:v', '1', thumbnail_path
            ], check=True, stdout=devnull, stderr=devnull)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to generate thumbnail for {video_path}: {e}")
        return False

def generate_thumbnails():
    static_dir = get_static_directory()
    video_dir = os.path.join(static_dir, 'videos')
    generated_thumbnails = []
    logger.debug(f"Generating thumbnails for videos in {video_dir}")
    push_text_to_client(f"Generating thumbnails for videos")

    for root, dirs, files in os.walk(video_dir):
        for filename in files:
            if filename.endswith(('.mp4', '.mkv', '.avi', '.webm')):
                video_path = os.path.join(root, filename)
                thumbnail_dir = os.path.join(root, '.thumb')
                os.makedirs(thumbnail_dir, exist_ok=True)
                thumbnail_path = os.path.join(thumbnail_dir, f"{filename}.thumb.jpg")

                if not os.path.exists(thumbnail_path):
                    success = generate_thumbnail(video_path, thumbnail_path)
                    if success:
                        generated_thumbnails.append(thumbnail_path)
    push_text_to_client(f"Generated thumbnails finished with {len(generated_thumbnails)} thumbnails")
    return {"success": True, "generated_thumbnails": generated_thumbnails}

def generate_thumbnail_for_path(video_path):
    push_text_to_client(f"Generating thumbnail for {video_path}")
    static_dir = get_static_directory()
    relative_path = video_path.replace('/static/videos/', '')
    real_path = os.path.join(static_dir, 'videos', relative_path)

    base_name = os.path.basename(real_path)
    thumbnail_dir = os.path.join(os.path.dirname(real_path), '.thumb')
    os.makedirs(thumbnail_dir, exist_ok=True)
    thumbnail_path = os.path.join(thumbnail_dir, f"{base_name}.thumb.jpg")

    if not os.path.exists(real_path):
        return {"success": False, "error": "Video file does not exist"}

    if os.path.exists(thumbnail_path):
        os.remove(thumbnail_path)
    success = generate_thumbnail(real_path, thumbnail_path)
    if success:
        return {"success": True, "thumbnail_path": thumbnail_path}
    else:
        return {"success": False, "error": "Failed to generate thumbnail"}
