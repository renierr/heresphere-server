import os
import subprocess
import json
import threading
from enum import Enum
from typing import Optional
from flask import Blueprint, jsonify, request
from loguru import logger
from bus import push_text_to_client
from cache import cache, clear_cache_by_name
from database.video_database import get_video_db
from globals import is_debug, get_static_directory, get_real_path_from_url, VideoFolder, \
    THUMBNAIL_DIR_NAME, ServerResponse, FolderState, ID_NAME_SEPERATOR, get_thumbnail_directory, \
    get_url_from_path
from utils import check_folder


class ThumbnailFormat(Enum):
    JPG = ("jpg", ".thumb.jpg")
    WEBP = ("webp", ".thumb.webp")
    WEBM = ("webm", ".thumb.webm")
    JSON = ("json", ".thumb.json")

    def __init__(self, fmt, extension):
        self.fmt = fmt
        self.extension = extension


thumbnail_bp = Blueprint('thumbnail', __name__)

@thumbnail_bp.route('/api/generate_thumbnails', methods=['POST'])
def gts():
    thumbnail_thread = threading.Thread(target=generate_thumbnails)
    thumbnail_thread.daemon = True
    thumbnail_thread.start()

    push_text_to_client(f"Generate Thumbnails started in the background")
    return jsonify(ServerResponse(True, "Generate Thumbnails started in the background"))

@thumbnail_bp.route('/api/generate_thumbnail', methods=['POST'])
def gt():
    data = request.get_json()
    video_path = data.get("video_path")

    if not video_path:
        return jsonify(ServerResponse(False, "No video path provided")), 400

    clear_cache_by_name('list_files')
    return jsonify(generate_thumbnail_for_path(video_path))

@cache(maxsize=4096, bypass_cache_param='force')
def get_video_info(video_path, force=False):
    """
    (cached; max time in cache CACHE_EXPIRATION_TIME)
    Get video info using ffprobe, try to load from .thumb folder first
    if not found, run ffprobe command and store the json in .thumb folder

    Example:
    {
        "streams": [ ... ],
        "format": { ... },
        "infos": { "uid": "..." } // additional infos
    }

    :param force: force to run ffprobe
    :param video_path: full path to video file
    :return: json object or None
    """

    try:
        # exclude file with '.part' extension
        if video_path.endswith('.part'):
            return None

        # find the video json in .thumb folder first
        infos = {}
        json_path = os.path.join(get_thumbnail_directory(video_path), os.path.basename(video_path)) + ThumbnailFormat.JSON.extension
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        if os.access(json_path, os.F_OK):
            with open(json_path, 'r', encoding='utf-8') as f:
                logger.debug(f"Loading pre existing video info from {json_path} - force: {force}")
                info = json.load(f)
            if 'infos' in info:
                infos = info['infos']
            if not force:
                return info

        logger.debug(f"Running ffprobe for {video_path}")
        push_text_to_client(f"Running ffprobe to get video info for {os.path.basename(video_path)}")
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format', '-show_entries', 'stream', '-of', 'json', video_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
        )
        info = json.loads(result.stdout)

        # additional infos
        info['infos'] = infos

        # find title and stuff from db
        video_url = get_url_from_path(video_path)
        with get_video_db() as db:
            download = db.for_download_table.get_download(video_url)
            download_id = os.path.basename(video_path).split(ID_NAME_SEPERATOR)[0][:14]
            if download:
                infos['download_id'] = download_id
                title = download.title
                if title:
                    infos['title'] = title
                url = download.original_url
                if url:
                    infos['original_url'] = url
                download_date = download.download_date
                if download_date:
                    infos['download_date'] = download_date

        # generate unique info string from specific fields
        format_info = info.get('format', {})
        streams_info = info.get('streams', [])
        video_uid = f"{format_info.get('format_name', '')}_{format_info.get('duration', '')}_{format_info.get('size', '')}"
        for stream in streams_info:
            video_uid += f"_{stream.get('codec_name', '')}_{stream.get('width', '')}_{stream.get('height', '')}_{stream.get('bit_rate', '')}_{stream.get('sample_rate', '')}_{stream.get('channels', '')}"
        infos['video_uid'] = video_uid

        # store json to .thumb folder
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(info, f, indent=2, ensure_ascii=False)

        return info
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get video info for {video_path}: {e}")
        return None

def generate_thumbnails() -> ServerResponse:
    """
    Generate thumbnails for all videos

    :return: json object with success and generated_thumbnails
    """
    static_dir = get_static_directory()
    generated_thumbnails = []
    thumbnail_errors = []

    for folder in VideoFolder:
        video_dir = os.path.join(static_dir, folder.dir)
        logger.debug(f"Generating thumbnails for {video_dir}")
        push_text_to_client(f"Generating thumbnails for {folder.name}")

        _, folder_state = check_folder(video_dir)
        if folder_state != FolderState.ACCESSIBLE:
            msg = f"Folder not accessible: {video_dir} - skipping thumbnail generation - state: {folder_state}"
            push_text_to_client(msg)
            logger.warning(msg)
            return ServerResponse(False, msg)

        for root, dirs, files in os.walk(video_dir, followlinks=True):
            # Exclude directories that start with a dot
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            for filename in files:
                if filename.endswith(('.mp4', '.mkv', '.avi', '.webm')):
                    video_path = os.path.join(root, filename)
                    thumbnail_dir = os.path.join(root, THUMBNAIL_DIR_NAME)

                    logger.debug(f"Checking thumbnail for {filename}")
                    # if one of the thumbs for file is missing, generate all thumbs
                    missing = False
                    for fmt in ThumbnailFormat:
                        if not os.access(os.path.join(thumbnail_dir, f"{filename}{fmt.extension}"), os.F_OK):
                            missing = True
                            break

                    if missing:
                        if generate_thumbnail(video_path):
                            generated_thumbnails.append(video_path)
                        else:
                            thumbnail_errors.append(video_path)

    push_text_to_client(f"Generate thumbnails finished with {len(generated_thumbnails)} thumbnails {'(' + str(len(thumbnail_errors)) + ' failed)' if thumbnail_errors else ''}")
    return ServerResponse(True, f"generated_thumbnails: {len(generated_thumbnails)}")


def generate_thumbnail(video_path) -> Optional[bool]:
    """
    Generate thumbnail for video file using ffmpeg
    this method will generate a webp, jpg and webm thumbnails

    :param video_path: full path to video file
    :return: true if success, false if failed
    """
    try:
        # exclude file with '.part' extension
        if video_path.endswith('.part'):
            return None

        if not os.access(video_path, os.F_OK):
            return False

        base_name = os.path.basename(video_path)
        push_text_to_client(f"Generating thumbnail and info for {base_name}")
        logger.debug(f"Evict cache for {video_path}")
        get_thumbnails.cache__evict(video_path)   # evict cache for thumbnails

        thumbnail_dir = get_thumbnail_directory(video_path)
        os.makedirs(thumbnail_dir, exist_ok=True)

        video_info = get_video_info(video_path, force=True)
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
                    # try calc with width and height
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

            outfile = os.path.join(thumbnail_dir, f"{base_name}{ThumbnailFormat.WEBP.extension}")
            logger.debug(f"Starting ffmpeg for webp - {outfile}")
            cmd = ['ffmpeg', '-ss', str(midpoint), '-an', '-t', str(clip_duration), '-y', '-i', video_path, '-loop', '0', '-vf', crop_filter + 'fps=1,scale=w=1024:h=768:force_original_aspect_ratio=decrease', outfile]
            logger.debug(f"Running command - webp: {' '.join(cmd)}")
            try:
                subprocess.run(cmd, check=True, stdout=stdout, stderr=stdout, timeout=execution_timelimit)
            except subprocess.TimeoutExpired:
                logger.error(f"Failed to generate thumbnail for webp (timeout): {video_path}")
                return False

            outfile = os.path.join(thumbnail_dir, f"{base_name}{ThumbnailFormat.JPG.extension}")
            logger.debug(f"Starting ffmpeg for jpg - {outfile}")
            cmd = ['ffmpeg', '-ss', str(midpoint), '-an', '-y', '-i', video_path, '-vf', crop_filter + 'fps=1,scale=w=1024:h=768:force_original_aspect_ratio=decrease', '-frames:v', '1', '-update', '1', outfile]
            logger.debug(f"Running command - jpg: {' '.join(cmd)}")
            try:
                subprocess.run(cmd, check=True, stdout=stdout, stderr=stdout, timeout=execution_timelimit)
            except subprocess.TimeoutExpired:
                logger.error(f"Failed to generate thumbnail for jpg (timeout): {video_path}")
                return False

            outfile = os.path.join(thumbnail_dir, f"{base_name}{ThumbnailFormat.WEBM.extension}")
            logger.debug(f"Starting ffmpeg for webm - {outfile}")
            cmd = ['ffmpeg', '-ss', str(midpoint), '-t', str(clip_duration), '-y', '-i', video_path, '-vf', crop_filter + 'scale=380:-1', '-c:v', 'libvpx', '-b:v', '256k', '-c:a', 'libvorbis', outfile]
            logger.debug(f"Running command - webm: {' '.join(cmd)}")
            try:
                subprocess.run(cmd, check=True, stdout=stdout, stderr=stdout, timeout=execution_timelimit)
            except subprocess.TimeoutExpired:
                logger.error(f"Failed to generate thumbnail for webm (timeout): {video_path}")
                return False

        return True
    except Exception as e:
        logger.error(f"Failed to generate thumbnail for {video_path}: {e}")
        return False

@cache(maxsize=4096, ttl=3600)
def get_thumbnails(filename):
    """
    Get thumbnail object with all possible thumbnail formats as url paths for a video file
    if thumbnail format does not exist, return None on this position

    :param filename: full path to video file
    :return: object with all thumbnail formats as url paths
    """

    base_name = os.path.basename(filename)
    thumbnail_directory = get_thumbnail_directory(filename)
    relative_path = os.path.relpath(thumbnail_directory, get_static_directory()).replace('\\', '/')

    return {
        fmt: f"/static/{relative_path}/{base_name}{fmt.extension}"
        for fmt in ThumbnailFormat
        if os.access(os.path.join(thumbnail_directory, f"{base_name}{fmt.extension}"), os.F_OK)
    }


def generate_thumbnail_for_path(video_path):
    """
    Generate thumbnail for a single provided video url link
    will always generate a new set of thumbnails

    the video_path should be an url path to the video file it should be in the static/videos or static/library folder
    the url is used to determine the thumbnail path (library or videos)

    :param video_path: url part of the video file
    :return: json object with success and message
    """

    real_path, _ = get_real_path_from_url(video_path)
    if not real_path:
        logger.debug(f"Invalid video path: {video_path}")
        return ServerResponse(False, "Invalid video path")

    if not os.access(real_path, os.F_OK):
        logger.debug(f"Video file does not exist: {real_path}")
        return ServerResponse(False, "Video file does not exist")

    base_name = os.path.basename(real_path)
    success = generate_thumbnail(real_path)
    push_text_to_client(f"Generate thumbnails finished for {base_name} with {'success' if success else 'failure'}")
    if success:
        return ServerResponse(True, f"Generate thumbnails finished for {base_name}")
    else:
        return ServerResponse(False, "Failed to generate thumbnail")

def update_file_info(file_path: str, updated_dict: dict) -> None:
    """
    Change the file info for a video file in the json file

    :param file_path: full path to video file
    :param updated_dict: info to update
    :return: none
    """
    base_name = os.path.basename(file_path)
    json_path = os.path.join(get_thumbnail_directory(file_path), base_name) + ThumbnailFormat.JSON.extension
    if os.access(json_path, os.F_OK):
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            infos = data.get('infos')
            # add info to existing infos if None
            if infos is None:
                infos = {}
                data['infos'] = infos

        infos.update(updated_dict)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        get_video_info.cache__evict(file_path)

