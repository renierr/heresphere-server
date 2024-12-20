import os
import re
import threading
import traceback
from collections import namedtuple

import yt_dlp
from datetime import datetime
from flask import Blueprint, request, jsonify
from loguru import logger
from bus import push_text_to_client
from cache import cache
from globals import get_url_map, find_url_id, get_url_counter, increment_url_counter, get_application_path, \
    find_url_info, remove_ansi_codes
from thumbnail import get_video_info, generate_thumbnail_for_path

VideoInfo = namedtuple('VideoInfo', ['created', 'size', 'duration', 'width', 'height', 'resolution', 'stereo'])

root_path = os.path.dirname(os.path.abspath(__file__))
is_windows = os.name == 'nt'
if is_windows:
    ffmpeg_path = os.path.join(get_application_path(), 'ffmpeg_x64', 'ffmpeg.exe')
    logger.debug(f"Windows detected, using ffmpeg binary from {ffmpeg_path}")
else:
    ffmpeg_path = None

video_bp = Blueprint('video', __name__)


@video_bp.route('/download', methods=['POST'])
def download():
    push_text_to_client(f"Download triggered")
    data = request.get_json()
    url = data.get("sourceUrl")

    if not url:
        logger.error("No direct video URL provided in the request")
        return jsonify({"success": False, "error": "No URL provided"}), 400

    # Start a new thread for the download process
    push_text_to_client(f"Starting download in background")
    download_thread = threading.Thread(target=download_video, args=(url,))
    download_thread.daemon = True
    download_thread.start()

    return jsonify({"success": True, "message": "Download started in the background"})


@video_bp.route('/stream', methods=['POST'])
def request_stream():
    data = request.get_json()
    url = data.get("url")

    if not url:
        logger.error("No URL provided in the request")
        return jsonify({"success": False, "error": "No URL provided"}), 400

    video_url, audio_url = get_stream(url)
    if video_url is None and audio_url is None:
        return jsonify({"success": False, "error": "Failed to retrieve video and audio streams"}), 500
    return jsonify({"success": True, "videoUrl": video_url, "audioUrl": audio_url})


def filename_with_ext(filename, youtube=True):
    path = os.path.join(root_path, 'static', 'videos', 'youtube')
    if not youtube: path = os.path.join(root_path, 'static', 'videos', 'direct')

    # Fix path for Windows Pyinstaller directory
    if is_windows and '_internal' in root_path:
        path = os.path.join(os.path.dirname(root_path), 'static', 'videos', 'youtube')
        if not youtube: os.path.join(os.path.dirname(root_path), 'static', 'videos', 'direct')

    for file in os.listdir(path):
        basename, _ = os.path.splitext(file)
        if basename == filename:
            return file

    return None


def is_youtube_url(url):
    """Check if the provided URL is a valid YouTube URL."""
    pattern = r'^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.+$'
    return bool(re.match(pattern, url))


def get_yt_dl_video_info(url):
    with yt_dlp.YoutubeDL() as ydl:
        info_dict = ydl.extract_info(url, download=False)
        vid = info_dict.get('id', None)
        video_title = info_dict.get('title', vid)
        filename = re.sub(r'\W+', '_', video_title)
        return vid, filename, video_title


def get_stream(url):
    ydl_opts = {
        'format': '(bv+ba/b)[protocol^=http][protocol!=dash] / (bv*+ba/b)',
        'quiet': True,  # Suppresses most of the console output
        'simulate': True,  # Do not download the video
        'geturl': True,  # Output only the urls
    }

    if is_windows:
        logger.debug(f"Windows detected, using ffmpeg binary from {ffmpeg_path}")
        ydl_opts['ffmpeg_location'] = ffmpeg_path

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = audio_url = None

            if is_youtube_url(url):
                if 'requested_formats' in info:
                    video_url = info['requested_formats'][0]['url']
                    audio_url = info['requested_formats'][1]['url']
                if not video_url and not audio_url:
                    raise Exception("Could not retrieve both video and audio URLs")

            else:
                if info.get('_type') == 'playlist' and 'entries' in info and len(info['entries']) > 0:
                    info = info['entries'][0]

                if 'url' not in info:
                    raise Exception("Could not retrieve video URL")

                video_url = info['url']
                audio_url = None

            return video_url, audio_url
    except Exception as e:
        logger.error(f"Error retrieving video and audio streams: {e}")
        return None, None


def download_yt(url, progress_function, url_id):
    vid, filename, title = get_yt_dl_video_info(url)
    filename = f"{vid}___{filename}"
    logger.debug(f"Downloading YouTube video {filename}")
    url_map = get_url_map()
    url_map[url_id]['filename'] = filename
    url_map[url_id]['title'] = title

    ydl_opts = {
        'format': '(bv+ba/b)[protocol^=http][protocol!=dash] / (bv*+ba/b)',
        'outtmpl': os.path.join('static', 'videos', 'youtube', filename) + '.%(ext)s',
        'progress_hooks': [progress_function],
        'nocolor': True,
        'updatetime': False,
    }

    if is_windows:
        logger.debug(f"Windows detected, using ffmpeg binary from {ffmpeg_path}")
        ydl_opts['ffmpeg_location'] = ffmpeg_path

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        logger.debug(f"Downloaded YouTube video {filename}")
    except Exception as e:
        logger.error(f"Error downloading YouTube video: {e}")
        return None
    return f"/static/videos/youtube/{filename_with_ext(filename)}"


def download_direct(url, progress_function, url_id):
    _, filename, title = get_yt_dl_video_info(url)

    logger.debug(f"Downloading direct video {filename}")
    url_map = get_url_map()
    url_map[url_id]['filename'] = filename
    url_map[url_id]['title'] = title

    ydl_opts = {
        'outtmpl': os.path.join('static', 'videos', 'direct', filename) + '.%(ext)s',
        'progress_hooks': [progress_function],
        'nocolor': True,
        'updatetime': False,
    }

    if is_windows:
        logger.debug(f"Windows detected, using ffmpeg binary from {ffmpeg_path}")
        ydl_opts['ffmpeg_location'] = ffmpeg_path

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        logger.debug(f"Downloaded direct video {filename}")
    except Exception as e:
        logger.error(f"Error downloading direct video: {e}")
        return None
    return f"/static/videos/direct/{filename_with_ext(filename, False)}"


def download_video(url):
    url_map = get_url_map()
    url_id = find_url_id(url)
    if url_id is None:
        url_id = get_url_counter()
        increment_url_counter()
        url_map[url_id] = {'url': url, 'filename': None, 'video_url': None,
                           'downloaded_date': int(datetime.now().timestamp())}
    else:
        url_map[url_id]['url'] = url
        url_map[url_id]['downloaded_date'] = int(datetime.now().timestamp())

    push_text_to_client(f"Downloading video {url_id}...")
    try:
        if is_youtube_url(url):
            video_url = download_yt(url, download_progress, url_id)
        else:
            video_url = download_direct(url, download_progress, url_id)
        url_map[url_id]['video_url'] = video_url
        generate_thumbnail_for_path(video_url)
        push_text_to_client(f"Download finished: {video_url}")
    except Exception as e:
        error_message = f"Failed to download video: {e}\n{traceback.format_exc()}"
        logger.error(error_message)
        push_text_to_client(f"Download failed: {e}")


def download_progress(d):
    output = ''
    fname = os.path.splitext(os.path.basename(d['filename']))[0]
    if d['status'] == 'downloading':
        idnr, _ = find_url_info(fname)
        output = f"Downloading...[{idnr}] - {remove_ansi_codes(d['_percent_str'])} complete at {remove_ansi_codes(d['_speed_str'])}, ETA {remove_ansi_codes(d['_eta_str'])}"
    elif d['status'] == 'finished':
        output = f"Download completed: {fname}"
    push_text_to_client(output)


@cache(maxsize=512)
def get_basic_save_video_info(filename):
    size = os.path.getsize(filename)
    created = os.path.getctime(filename)
    video_info = get_video_info(filename)
    if video_info is not None:
        duration = int(float(video_info['format'].get('duration', 0))) if 'format' in video_info else 0
        width = video_info['streams'][0].get('width', 0) if 'streams' in video_info and len(
            video_info['streams']) > 0 else 0
        height = video_info['streams'][0].get('height', 0) if 'streams' in video_info and len(
            video_info['streams']) > 0 else 0
        resolution = max(width, height)
        stereo = 'sbs' if width / height == 2 else ''
    else:
        duration = 0
        width = 0
        height = 0
        resolution = 0
        stereo = ''
    return VideoInfo(created, size, duration, width, height, resolution, stereo)
