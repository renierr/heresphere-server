import os
import subprocess
import json
import threading
from enum import Enum
from flask import Blueprint, jsonify, request
from loguru import logger
from bus import push_text_to_client
from cache import cache, clear_cache_by_name
from globals import is_debug, get_static_directory, get_real_path_from_url


class ThumbnailFormat(Enum):
    JPG = ("jpg", ".thumb.jpg")
    WEBP = ("webp", ".thumb.webp")
    WEBM = ("webm", ".thumb.webm")
    JSON = ("json", ".thumb.json")

    def __init__(self, fmt, extension):
        self.fmt = fmt
        self.extension = extension


thumbnail_bp = Blueprint('thumbnail', __name__)

@thumbnail_bp.route('/api/library/generate_thumbnails', methods=['POST'])
def glt():
    return generate_thumbnails(library=True)

@thumbnail_bp.route('/api/generate_thumbnails', methods=['POST'])
def gts(library=False):
    try:
        thumbnail_thread = threading.Thread(target=generate_thumbnails, args=(library,))
        thumbnail_thread.daemon = True
        thumbnail_thread.start()

        push_text_to_client(f"Generate Thumbnails {'for library' if library else ''} started in the background")
        return jsonify({"success": True, "message": "Generate Thumbnails started in the background"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@thumbnail_bp.route('/api/generate_thumbnail', methods=['POST'])
def gt():
    data = request.get_json()
    video_path = data.get("video_path")

    if not video_path:
        return jsonify({"success": False, "error": "No video path provided"}), 400

    try:
        result = generate_thumbnail_for_path(video_path)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@cache(maxsize=512)
def get_video_info(video_path):
    """
    (cached; max time in cache CACHE_EXPIRATION_TIME)
    Get video info using ffprobe, try to load from .thumb folder first
    if not found, run ffprobe command and store the json in .thumb folder

    Example:
    {
        "streams": [ ... ],
        "format": { ... }
    }

    :param video_path: full path to video file
    :return: json object or None
    """

    try:
        # exclude file with '.part' extension
        if video_path.endswith('.part'):
            return None

        # find the video json in .thumb folder first
        json_path = os.path.join(os.path.dirname(video_path), '.thumb', os.path.basename(video_path)) + '.thumb.json'
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                logger.debug(f"Loading pre existing video info from {json_path}")
                info = json.load(f)
                return info

        logger.debug(f"Running ffprobe for {video_path}")
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format', '-show_entries', 'stream', '-of', 'json', video_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
        )
        info = json.loads(result.stdout)

        # store json to .thumb folder
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(info, f, indent=2, ensure_ascii=False)

        return info
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get video info for {video_path}: {e}")
        return None

def generate_thumbnails(library=False):
    """
    Generate thumbnails for all videos in the static/videos or static/library folder

    :param library: if true use the library folder instead of videos
    :return: json object with success and generated_thumbnails
    """
    static_dir = get_static_directory()
    video_dir = os.path.join(static_dir, 'videos' if not library else 'library')
    generated_thumbnails = []
    thumbnail_errors = []
    logger.debug(f"Generating thumbnails for {video_dir}")
    push_text_to_client(f"Generating thumbnails for {'library' if library else 'videos'}")

    for root, dirs, files in os.walk(video_dir, followlinks=True):
        # Exclude directories that start with a dot
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for filename in files:
            if filename.endswith(('.mp4', '.mkv', '.avi', '.webm')):
                video_path = os.path.join(root, filename)
                thumbnail_dir = os.path.join(root, '.thumb')
                os.makedirs(thumbnail_dir, exist_ok=True)
                thumbnail_path = os.path.join(thumbnail_dir, f"{filename}.thumb.webp")

                logger.debug(f"Checking thumbnail for {filename}")
                # if one of the thumbs for file is missing, generate all thumbs
                if not os.path.exists(thumbnail_path) or not os.path.exists(os.path.splitext(thumbnail_path)[0] + '.jpg') or not os.path.exists(os.path.splitext(thumbnail_path)[0] + '.webm'):
                    success = generate_thumbnail(video_path, thumbnail_path)
                    if success:
                        generated_thumbnails.append(thumbnail_path)
                    else:
                        thumbnail_errors.append(video_path)

    push_text_to_client(f"Generate thumbnails finished with {len(generated_thumbnails)} thumbnails {'(' + str(len(thumbnail_errors)) + ' failed)' if thumbnail_errors else ''}")
    return {"success": True, "generated_thumbnails": generated_thumbnails}


def generate_thumbnail(video_path, thumbnail_path):
    """
    Generate thumbnail for video file using ffmpeg
    this method will generate a webp, jpg and webm thumbnails

    :param video_path: full path to video file
    :param thumbnail_path: full path to thumbnail file that will be generated (default webp)
    :return: true if success, false if failed
    """
    try:
        # exclude file with '.part' extension
        if video_path.endswith('.part'):
            return None

        push_text_to_client(f"Generating thumbnail and info for {os.path.basename(video_path)}")
        logger.debug(f"Evict cache for {video_path}")
        get_thumbnails.cache__evict(video_path)   # evict cache for thumbnails

        video_info = get_video_info(video_path)
        if not video_info:
            logger.error(f"Failed to get video info for {video_path}")
            return False

        duration = float(video_info['format']['duration'])
        midpoint = duration / 2
        logger.debug(f"Video duration: {duration} seconds - taking thumbnail at {midpoint} seconds")

        # find aspect ratio
        aspect_ratio = None
        for stream in video_info['streams']:
            if stream['codec_type'] == 'video':
                if 'display_aspect_ratio' in stream:
                    aspect_ratio = stream['display_aspect_ratio']
                else:
                    # try calc with width and heigth
                    width = stream['width'] if 'width' in stream else 0
                    height = stream['height'] if 'height' in stream else 0
                    # check if 2:1 aspect ratio
                    if width > 0 and height > 0 and width / height == 2:
                        aspect_ratio = '2:1'
                break
        sbs_video = True if aspect_ratio == '2:1' else False
        crop_filter = "" if not sbs_video else "crop=in_w/2:in_h:0:0,"
        clip_duration = 8
        if midpoint + clip_duration > duration:
            clip_duration = int((duration - midpoint - 1) if duration - midpoint - 1 > 0 else 1)

        with open(os.devnull, 'w') as devnull:
            stdout = None if is_debug() else devnull
            execution_timelimit = 120

            logger.debug(f"Starting ffmpeg for webp")
            cmd = ['ffmpeg', '-ss', str(midpoint), '-an', '-t', str(clip_duration), '-y', '-i', video_path, '-loop', '0', '-vf', crop_filter + 'fps=1,scale=w=1024:h=768:force_original_aspect_ratio=decrease', thumbnail_path]
            logger.debug(f"Running command: {' '.join(cmd)}")
            try:
                subprocess.run(cmd, check=True, stdout=stdout, stderr=stdout, timeout=execution_timelimit)
            except subprocess.TimeoutExpired:
                logger.error(f"Failed to generate thumbnail for webp (timeout): {video_path}")
                return False

            logger.debug(f"Starting ffmpeg for jpg")
            cmd = ['ffmpeg', '-ss', str(midpoint), '-an', '-y', '-i', video_path, '-vf', crop_filter + 'fps=1,scale=w=1024:h=768:force_original_aspect_ratio=decrease', '-frames:v', '1', '-update', '1', os.path.splitext(thumbnail_path)[0] + '.jpg']
            logger.debug(f"Running command: {' '.join(cmd)}")
            try:
                subprocess.run(cmd, check=True, stdout=stdout, stderr=stdout, timeout=execution_timelimit)
            except subprocess.TimeoutExpired:
                logger.error(f"Failed to generate thumbnail for jpg (timeout): {video_path}")
                return False

            logger.debug(f"Starting ffmpeg for webm")
            cmd = ['ffmpeg', '-ss', str(midpoint), '-t', str(clip_duration), '-y', '-i', video_path, '-vf', crop_filter + 'scale=380:-1', '-c:v', 'libvpx', '-deadline', 'realtime', '-cpu-used', '16', '-crf', '8', '-b:v', '256k', '-c:a', 'libvorbis', os.path.splitext(thumbnail_path)[0] + '.webm']
            logger.debug(f"Running command: {' '.join(cmd)}")
            try:
                subprocess.run(cmd, check=True, stdout=stdout, stderr=stdout, timeout=execution_timelimit)
            except subprocess.TimeoutExpired:
                logger.error(f"Failed to generate thumbnail for webm (timeout): {video_path}")
                return False

        return True
    except Exception as e:
        logger.error(f"Failed to generate thumbnail for {video_path}: {e}")
        return False

def get_thumbnail(filename, *formats):
    """
    Get the thumbnail url for a video file in a specific format

    :param filename: full path to video file
    :param formats: ThumbnailFormat objects ordered by priority on which to return the thumbnail
    :return:
    """
    thumbs = get_thumbnails(filename)
    for fmt in formats:
        if thumbs[fmt]:
            return thumbs[fmt]
    return None

@cache(maxsize=512, ttl=3600)
def get_thumbnails(filename):
    """
    Get thumbnail object with all possible thumbnail formats as url paths for a video file
    if thumbnail format does not exist, return None on this position

    :param filename: full path to video file
    :return: object with all thumbnail formats as url paths
    """

    base_name = os.path.basename(filename)
    thumbnail_directory = os.path.join(os.path.dirname(filename), '.thumb')
    # check for all thumbnail formats if there exist here
    result = {}
    for fmt in ThumbnailFormat:
        result[fmt] = None
        if os.path.exists(os.path.join(thumbnail_directory, f"{base_name}{fmt.extension}")):
            p = os.path.relpath(thumbnail_directory, get_static_directory()).replace('\\', '/')
            result[fmt] = f"/static/{p}/{base_name}{fmt.extension}"
    return result


def generate_thumbnail_for_path(video_path):
    """
    Generate thumbnail for a single provided video url link
    will always generate a new set of thumbnails

    the video_path should be an url path to the video file it should be in the static/videos or static/library folder
    the url is used to determine the thumbnail path (library or videos)

    :param video_path: url part of the video file
    :return: json object with success and message
    """

    real_path = get_real_path_from_url(video_path)
    if not real_path:
        return {"success": False, "error": "Invalid video path"}

    base_name = os.path.basename(real_path)
    thumbnail_dir = os.path.join(os.path.dirname(real_path), '.thumb')
    os.makedirs(thumbnail_dir, exist_ok=True)
    thumbnail_path = os.path.join(thumbnail_dir, f"{base_name}.thumb.webp")

    if not os.path.exists(real_path):
        return {"success": False, "error": "Video file does not exist"}

    success = generate_thumbnail(real_path, thumbnail_path)
    clear_cache_by_name('list_files')
    push_text_to_client(f"Generate thumbnails finished for {base_name} with {'success' if success else 'failure'}")
    if success:
        return {"success": True, "message": f"Generate thumbnails finished for {base_name}" }
    else:
        return {"success": False, "error": "Failed to generate thumbnail"}
