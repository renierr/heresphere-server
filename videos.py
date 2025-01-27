import os
import re
import threading
import time

import yt_dlp
from datetime import datetime
from flask import Blueprint, request, jsonify
from loguru import logger
from yt_dlp import ImpersonateTarget

from database import get_downloads_db
from files import list_files
from bus import push_text_to_client
from globals import get_url_map, get_application_path, \
    remove_ansi_codes, VideoFolder, ServerResponse, UNKNOWN_VIDEO_EXTENSION, ID_NAME_SEPERATOR
from thumbnail import generate_thumbnail_for_path

root_path = get_application_path()
video_bp = Blueprint('video', __name__)

@video_bp.route('/download', methods=['POST'])
def download():
    push_text_to_client("Download triggered")
    data = request.get_json()
    # use sourceUrl except if heresphere is in name
    url = data.get("sourceUrl")
    title = None
    if 'heresphere' in url:
        url = data.get("videoUrl")
        title = data.get("title")

    if not url:
        logger.error("No direct video URL provided in the request")
        return jsonify(ServerResponse(False, "No URL provided")), 400

    # Start a new thread for the download process
    push_text_to_client("Starting download in background")
    download_thread = threading.Thread(target=download_video, args=(url, title,))
    download_thread.daemon = True
    download_thread.start()

    return jsonify(ServerResponse(True, "Download started in the background"))


@video_bp.route('/stream', methods=['POST'])
def request_stream():
    data = request.get_json()
    url = data.get("url")

    if not url:
        logger.error("No URL provided in the request")
        return jsonify(ServerResponse(False, "No URL provided")), 400

    video_url, audio_url, title, cookies = get_stream(url)
    if video_url is None and audio_url is None:
        return jsonify(ServerResponse(False, "Failed to retrieve video and audio streams")), 500
    return jsonify({"success": True, "videoUrl": video_url, "audioUrl": audio_url, "title": title, "cookies": cookies })


def filename_with_ext(filename, youtube=True):
    path = os.path.join(root_path, 'static', VideoFolder.videos.dir, 'youtube')
    if not youtube: path = os.path.join(root_path, 'static', VideoFolder.videos.dir, 'direct')

    for file in os.listdir(path):
        basename, _ = os.path.splitext(file)
        if basename == filename:
            return file

    return None


def is_youtube_url(url: str):
    """Check if the provided URL is a valid YouTube URL."""
    pattern = r'^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.+$'
    return bool(re.match(pattern, url.strip()))


def get_yt_dl_video_info(url):
    ydl_opts = {
        'quiet': True,
        'simulate': True,
        'download': False,
        'impersonate': ImpersonateTarget('chrome'),
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        vid = info_dict.get('id', None)
        video_title = info_dict.get('title', vid)
        filename = re.sub(r'\W+', '_', video_title)
        return vid, filename, video_title


def get_stream(url) -> tuple:
    ydl_opts = {
        'format': '(bv+ba/b)[protocol^=http][protocol!=dash] / (bv*+ba/b)',
        'quiet': True,  # Suppresses most of the console output
        'simulate': True,  # Do not download the video
        'geturl': True,  # Output only the urls
        'impersonate': ImpersonateTarget('chrome'),
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = audio_url = cookies = None
            title = info.get('title', None)
            if is_youtube_url(url):
                if 'requested_formats' in info:
                    video_url = info['requested_formats'][0]['url']
                    audio_url = info['requested_formats'][1]['url']
                if not video_url and not audio_url:
                    raise ValueError("Could not retrieve both video and audio URLs")

            else:
                if info.get('_type') == 'playlist' and 'entries' in info and len(info['entries']) > 0:
                    info = info['entries'][0]

                if 'url' not in info:
                    raise ValueError("Could not retrieve video URL")

                video_url = info['url']
                audio_url = None
                cookies = info.get('cookies', None)

            return video_url, audio_url, title, cookies
    except Exception as e:
        logger.error(f"Error retrieving video and audio streams: {e}")
        return None, None, None


def download_video(url, title):
    download_random_id = None
    url_map = get_url_map()

    try:
        with get_downloads_db() as db:
            download_random_id = db.next_download(url)

        push_text_to_client(f"Downloading video {download_random_id}")
        youtube_video = is_youtube_url(url)
        subfolder = 'youtube' if youtube_video else 'direct'
        url_map[download_random_id] = {'url': url, 'title': title, 'failed': False}
        ydl_opts = {
            'format': '(bv+ba/b)[protocol^=http][protocol!=dash] / (bv*+ba/b)',
            'restrictfilenames': True,
            'outtmpl': os.path.join('static', VideoFolder.videos.dir, subfolder) + f"/{download_random_id}{ID_NAME_SEPERATOR}%(title)s.%(ext)s",
            'progress_hooks': [download_progress],
            'nocolor': True,
            'updatetime': False,
            'impersonate': ImpersonateTarget('chrome'),
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            download_result = ydl.extract_info(url, download=True, extra_info={'video_id': download_random_id})

        filename = download_result.get('requested_downloads', {})[0].get('filename', None)
        if not filename:
            raise ValueError("No filename found in the download result")

        basename = os.path.basename(filename)
        video_url = '/' + filename.replace('\\', '/')
        title = download_result.get('title', None) or title
        url_map[download_random_id]['title'] = title

        with get_downloads_db() as db:
            db.store_download(url=url, video_url=video_url, filename=basename, title=title)

        # only generate thumbnails if download is a video check for file with extension ".unknown_video" this is not a video
        if not video_url.endswith(UNKNOWN_VIDEO_EXTENSION):
            generate_thumbnail_for_path(video_url)
        list_files.cache__evict(VideoFolder.videos)
        logger.debug(f"Download finished: {video_url}")
        push_text_to_client(f"Download finished: {video_url}")
    except Exception as e:
        error_message = f"Failed to download video: {e}"
        url_map[download_random_id]['failed'] = True
        logger.error(error_message)
        list_files.cache__evict(VideoFolder.videos)
        push_text_to_client(f"Download failed [{download_random_id}] - {e}")


last_call_time = 0
last_zero_percent = ''
throttle_delay = 1
def download_progress(d):

    global last_call_time
    current_time = time.time()

    output = ''
    video_id = d.get('info_dict', {}).get('video_id', None)
    if d['status'] == 'downloading':
        # Throttle the output to prevent spamming the client - let 0.0% through to indicate new file download
        percent = remove_ansi_codes(d.get('_percent_str', ''))
        message = f"Downloading...[{video_id}] - {percent} complete"
        logger.debug(message)
        if ' 0.0%' in percent:
            global last_zero_percent
            if last_zero_percent == message:
                return
            last_zero_percent = message
            list_files.cache__evict(VideoFolder.videos)
        elif current_time - last_call_time < throttle_delay:
            return
        last_call_time = current_time
        output = f"{message} at {remove_ansi_codes(d['_speed_str'])}, ETA {remove_ansi_codes(d['_eta_str'])}"
    elif d['status'] == 'finished':
        fname = os.path.splitext(os.path.basename(d['filename']))[0]
        output = f"Downloading...[{video_id}] - 100.0% complete: {fname}"
    push_text_to_client(output)


