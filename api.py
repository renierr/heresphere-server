import base64
import json
import math
import os
import shutil

from flask import Blueprint, jsonify, request
from bus import push_text_to_client
from cache import cache
from thumbnail import get_thumbnail, ThumbnailFormat
from globals import find_url_info, get_static_directory, get_real_path_from_url
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

@api_bp.route('/api/bookmarks', methods=['GET'])
def gb():
    try:
        return jsonify(list_bookmarks())
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route('/api/bookmarks', methods=['POST'])
def sb():
    try:
        data = request.get_json()
        title = data.get("title")
        url = data.get("url")
        return jsonify(save_bookmark(data.get("title"),  data.get("url")))
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route('/api/bookmarks', methods=['DELETE'])
def db():
    try:
        encoded_url = request.args.get('url')
        decoded_url = base64.urlsafe_b64decode(encoded_url).decode('utf-8')
        return jsonify(delete_bookmark(decoded_url))
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route('/api/files', methods=['DELETE'])
def df():
    try:
        encoded_url = request.args.get('url')
        decoded_url = base64.urlsafe_b64decode(encoded_url).decode('utf-8')
        return jsonify(delete_file(decoded_url))
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
                    **({k: url_info.get(k) for k in ['url', 'video_url', 'downloaded_date']} if url_info else {})
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
            for fmt in ThumbnailFormat:
                thumbnail_path = os.path.join(thumbnail_dir, f"{base_name}{fmt.extension}")
                if os.path.exists(thumbnail_path):
                    library_thumbnail_dir = os.path.join(os.path.dirname(library_path), '.thumb')
                    os.makedirs(library_thumbnail_dir, exist_ok=True)
                    shutil.move(thumbnail_path, os.path.join(library_thumbnail_dir, f"{base_name}{fmt.extension}"))


        push_text_to_client(f"File moved to library: {base_name}")
        return {"success": True, "library_path": library_path}
    else:
        return {"success": False, "error": "Invalid video path"}

@cache(maxsize=128, ttl=3600)
def list_bookmarks():
    bookmarks = []
    bookmarks_file = os.path.join(get_static_directory(), 'bookmarks.json')
    if os.path.exists(bookmarks_file):
        with open(bookmarks_file, 'r') as f:
            bookmarks = json.load(f)
    return sorted(bookmarks, key=lambda x: x['title'].lower())

def write_bookmarks(bookmarks):
    bookmarks_file = os.path.join(get_static_directory(), 'bookmarks.json')
    with open(bookmarks_file, 'w') as f:
        json.dump(bookmarks, f)
    list_bookmarks.cache__clear()

def save_bookmark(title, url):#
    if not title or not url:
        return {"success": False, "error": "Title or URL missing"}

    bookmarks = list_bookmarks()
    bookmark = next((b for b in bookmarks if b['url'] == url), None)

    if bookmark:
        bookmark['title'] = title
    else:
        bookmarks.append({"title": title, "url": url})

    write_bookmarks(bookmarks)
    return {"success": True, "message": "Bookmark added"}

def delete_bookmark(url):
    if not url:
        return {"success": False, "error": "URL missing"}

    bookmarks_before = list_bookmarks()
    bookmarks = [b for b in bookmarks_before if b['url'] != url]
    if len(bookmarks) == len(bookmarks_before):
        return {"success": False, "error": "Bookmark not found"}
    else:
        write_bookmarks(bookmarks)

    return {"success": True, "message": "Bookmark deleted"}

def delete_file(url):
    if not url:
        return {"success": False, "error": "URL missing"}

    # only allow delete from videos directory
    if not '/static/videos/' in url:
        return {"success": False, "error": "Invalid URL"}

    real_path = get_real_path_from_url(url)
    if not real_path:
        return {"success": False, "error": "File not found"}

    # delete the file and thumbnails
    base_name = os.path.basename(real_path)
    thumbnail_dir = os.path.join(os.path.dirname(real_path), '.thumb')
    if os.path.exists(thumbnail_dir):
        for fmt in ThumbnailFormat:
            thumbnail_path = os.path.join(thumbnail_dir, f"{base_name}{fmt.extension}")
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
    os.remove(real_path)
    push_text_to_client(f"File deleted: {base_name}")
    return {"success": True, "message": f"File {base_name} deleted"}
