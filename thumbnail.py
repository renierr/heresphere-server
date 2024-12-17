import os
import subprocess
import json
from loguru import logger
from bus import push_text_to_client
from globals import is_debug, get_static_directory


def get_video_info(video_path):
    """
    Get video info using ffprobe, try to load from .thumb folder first
    if not found, run ffprobe command

    Example:
    {
        "streams": [ ... ],
        "format": { ... }
    }

    :param video_path: full path to video file
    :return: json object or None
    """
    try:
        # find the video json in .thumb folder first
        json_path = os.path.join(os.path.dirname(video_path), '.thumb', os.path.basename(video_path)) + '.thumb.json'
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                logger.debug(f"Loading pre existing video info from {json_path}")
                info = json.load(f)
                return info

        logger.debug(f"Running ffprobe for {video_path}")
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format', '-show_entries', 'stream', '-of', 'json', video_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
        )
        info = json.loads(result.stdout)
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

    push_text_to_client(f"Generated thumbnails finished with {len(generated_thumbnails)} thumbnails")
    return {"success": True, "generated_thumbnails": generated_thumbnails}


def generate_thumbnail(video_path, thumbnail_path):
    """
    Generate thumbnail for video file using ffmpeg
    this method will generate a webp, jpg and webm thumbnails
    also generate a json file with video info retrieved from video_path (if not exists)

    :param video_path: full path to video file
    :param thumbnail_path: full path to thumbnail file that will be generated (default webp)
    :return: true if success, false if failed
    """
    try:
        push_text_to_client(f"Generating thumbnail and info for {os.path.basename(video_path)}")

        video_info = get_video_info(video_path)
        if not video_info:
            logger.error(f"Failed to get video info for {video_path}")
            return False

        duration = float(video_info['format']['duration'])
        logger.debug(f"Video duration: {duration} seconds")

        # store json to .thumb folder
        json_path = os.path.splitext(thumbnail_path)[0] + '.json'
        with open(json_path, 'w') as f:
            json.dump(video_info, f, indent=2)

        with open(os.devnull, 'w') as devnull:
            stdout = None if is_debug() else devnull
            logger.debug(f"Starting ffmpeg for webp")
            subprocess.run([
                'ffmpeg', '-y', '-i', video_path, '-loop', '0', '-vf', 'thumbnail,scale=w=1024:h=768:force_original_aspect_ratio=decrease', '-ss', '00:00:10.000', '-frames:v', '5', thumbnail_path
            ], check=True, stdout=stdout, stderr=stdout)
            logger.debug(f"Starting ffmpeg for jpg")
            subprocess.run([
                'ffmpeg', '-y', '-i', video_path, '-vf', 'thumbnail,scale=w=1024:h=768:force_original_aspect_ratio=decrease', '-ss', '00:00:10.000', '-frames:v', '1', os.path.splitext(thumbnail_path)[0] + '.jpg'
            ], check=True, stdout=stdout, stderr=stdout)
            logger.debug(f"Starting ffmpeg for webm")
            subprocess.run([
                'ffmpeg', '-y', '-i', video_path, '-vf', 'thumbnail,scale=w=380:h=240:force_original_aspect_ratio=decrease', '-ss', '00:00:10.000', '-frames:v', '5', os.path.splitext(thumbnail_path)[0] + '.webm'
            ], check=True, stdout=stdout, stderr=stdout)
        logger.debug(f"Generating thumbnail for {video_path} finished.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to generate thumbnail for {video_path}: {e}")
        return False


def get_thumbnail(filename):
    """
    Get thumbnail path for video file
    if thumbnail does not exist, return None

    :param filename: full path to video file
    :return: url path to thumbnail or None
    """
    static_path = 'videos' if 'videos' in filename else '.'
    base_name = os.path.basename(filename)
    thumbfile = os.path.join(os.path.dirname(filename), '.thumb', f"{base_name}.thumb.webp")
    if not os.path.exists(thumbfile):
        return None
    relative_thumbfile = os.path.relpath(thumbfile, start=os.path.join(os.path.dirname(filename), '..')).replace('\\', '/')
    return f"/static/{static_path}/{relative_thumbfile}"


def generate_thumbnail_for_path(video_path):
    """
    Generate thumbnail for a single provided video url link
    will always generate a new set of thumbnails

    the video_path should be a url path to the video file it should be in the static/videos or static/library folder
    the url is used to determine the thumbnail path (library or videos)

    :param video_path: url part of the video file
    :return: json object with success and message
    """
    static_dir = get_static_directory()
    if '/static/library/' in video_path:
        relative_path = video_path.replace('/static/library/', '')
        real_path = os.path.join(static_dir, 'library', relative_path)
    else:
        relative_path = video_path.replace('/static/videos/', '')
        real_path = os.path.join(static_dir, 'videos', relative_path)

    base_name = os.path.basename(real_path)
    thumbnail_dir = os.path.join(os.path.dirname(real_path), '.thumb')
    os.makedirs(thumbnail_dir, exist_ok=True)
    thumbnail_path = os.path.join(thumbnail_dir, f"{base_name}.thumb.webp")

    if not os.path.exists(real_path):
        return {"success": False, "error": "Video file does not exist"}

    success = generate_thumbnail(real_path, thumbnail_path)
    if success:
        return {"success": True, "message": "generate thumbnail finished" }
    else:
        return {"success": False, "error": "Failed to generate thumbnail"}
