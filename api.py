import math
import os
import shutil

from flask import Blueprint, jsonify, request
from bus import push_text_to_client
from thumbnail import get_thumbnail, ThumbnailFormat
from globals import find_url_info, get_static_directory
from videos import get_basic_save_video_info

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/list')
def get_files():
    try:
        return jsonify(list_files())
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/api/library/list')
def get_library_files():
    try:
        return jsonify(list_files('library'))
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/api/move_to_library', methods=['POST'])
def mtl():
    data = request.get_json()
    video_path = data.get("video_path")

    if not video_path:
        return jsonify({"success": False, "error": "No video path provided"}), 400

    try:
        result = move_to_library(video_path)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def format_byte_size(size_bytes):
    """
    Format a byte size into a human-readable string.

    :param size_bytes: size in bytes
    :return: formatted size string
    """
    if size_bytes == 0:
        return "0B"

    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

def format_duration(duration):
    """
    Format a duration in seconds to HH:MM:SS

    :param duration: duration in seconds
    :return: formatted duration string
    """
    hours = int(duration // 3600)
    minutes = int((duration % 3600) // 60)
    seconds = int(duration % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def parse_youtube_filename(filename):
    """
    Parse a YouTube filename into id and title
    The stored filename is in the format: id___title.ext

    :param filename: filename to parse
    :return: id, title
    """
    parts = filename.split('___')
    id_part = parts[0]
    title_part = parts[1]

    return id_part, title_part

def extract_file_details(root, filename, base_path):
    realfile = os.path.join(root, filename)

    if not os.path.exists(realfile):
        return None

    partial = filename.endswith('.part')
    result = {
        'partial': partial,
        'yt_id': None,
        'title': os.path.splitext(filename)[0],
        'filename': f"{base_path}/{filename}",
    }
    if partial:
        result.update({
            'created': os.path.getctime(realfile),
        })
    else:
        thumbnail = get_thumbnail(realfile, ThumbnailFormat.WEBP, ThumbnailFormat.JPG)
        info = get_basic_save_video_info(realfile)
        result.update({
            'thumbnail': thumbnail,
            'created': info.created,
            'filesize': info.size,
            'width': info.width,
            'height': info.height,
            'duration': info.duration,
            'resolution': info.resolution,
            'stereo': info.stereo
        })
    return result

def list_files(directory='videos'):
    extracted_details = []
    base_path = f"/static/{directory}"

    for root, dirs, files in os.walk(os.path.join(get_static_directory(), directory), followlinks=True):
        # Exclude directories that start with a dot
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for filename in files:
            # ignore part-Frag and ytdl files
            if 'part-Frag' in filename or filename.endswith('.ytdl'):
                continue

            common_details = extract_file_details(root, filename, base_path)

            # only for videos directory
            if directory == 'videos':
                url_id, url_info = find_url_info(filename)
                common_details.update({
                    'url_id': url_id,
                    'orig_link': url_info['url'] if url_info and 'url' in url_info else None,
                    'video_url': url_info['video_url'] if url_info and 'video_url' in url_info else None,
                    'downloaded_date': url_info['downloaded_date'] if url_info and 'downloaded_date' in url_info else None
                })

                if filename.count('___') == 1:
                    yt_id, title = parse_youtube_filename(filename)
                    common_details.update({
                        'yt_id': yt_id,
                        'title': title,
                        'filename': f"{base_path}/youtube/{filename}"
                    })
                else:
                    common_details.update({
                        'filename': f"{base_path}/direct/{filename}"
                    })
            extracted_details.append(common_details)

    extracted_details.sort(key=lambda x: x['created'], reverse=True)
    return extracted_details


def move_to_library(video_path):
    """
    Move a video file from the videos folder to the library folder
    all thumbnails will be moved as well

    :param video_path: full path to video file
    :return: json object with success and library_path
    """
    push_text_to_client(f"Move file to library: {video_path}")
    static_dir = get_static_directory()
    if '/static/videos/' in video_path:
        relative_path = video_path.replace('/static/videos/', '')
        real_path = os.path.join(static_dir, 'videos', relative_path)

        if not os.path.exists(real_path):
            return {"success": False, "error": "Video file does not exist"}

        base_name = os.path.basename(real_path)
        library_path = os.path.join(static_dir, 'library', base_name)

        if os.path.exists(library_path):
            return {"success": False, "error": f"Target exists in library: {base_name}"}

        # Move the video file
        shutil.move(real_path, library_path)

        # Move the thumbnails
        thumbnail_dir = os.path.join(os.path.dirname(real_path), '.thumb')
        if os.path.exists(thumbnail_dir):
            for ext in ['.thumb.webp', '.thumb.jpg', '.thumb.webm']:
                thumbnail_path = os.path.join(thumbnail_dir, f"{base_name}{ext}")
                if os.path.exists(thumbnail_path):
                    library_thumbnail_dir = os.path.join(os.path.dirname(library_path), '.thumb')
                    os.makedirs(library_thumbnail_dir, exist_ok=True)
                    shutil.move(thumbnail_path, os.path.join(library_thumbnail_dir, f"{base_name}{ext}"))



        return {"success": True, "library_path": library_path}
    else:
        return {"success": False, "error": "Invalid video path"}

