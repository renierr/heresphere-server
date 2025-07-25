import os
import re
import threading
import time
from datetime import datetime
import json

import yt_dlp
from flask import Blueprint, request, jsonify
from loguru import logger
from yt_dlp.networking.impersonate import ImpersonateTarget

from bus import push_text_to_client
from database.video_database import get_video_db
from database.video_models import Videos, Similarity, Online
from files import list_files
from globals import get_application_path, \
    remove_ansi_codes, VideoFolder, ServerResponse, UNKNOWN_VIDEO_EXTENSION, ID_NAME_SEPERATOR, get_real_path_from_url
from onlines import list_onlines
from similar import build_features_for_video, clear_similarity_cache
from thumbnail import generate_thumbnail_for_path, get_video_info
from utils import check_video_url_stale

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


@video_bp.route('/scan')
def sfv():
    thumbnail_thread = threading.Thread(target=scan_for_videos)
    thumbnail_thread.daemon = True
    thumbnail_thread.start()

    push_text_to_client("Scanning Videos started in the background")
    return jsonify(ServerResponse(True, "Scanning Videos started in the background"))


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
        content_length = None
        # find entry in DB and serve from their if available
        with get_video_db() as db:
            online = db.for_online_table.get_online(url)
            if online and online.video_url:
                # check if video url is stale
                stale, content_length = check_video_url_stale(online.video_url)
                if not stale:
                    # if not stale, return the online video url
                    logger.debug(f"Serving video from online database: {online.video_url}")
                    if content_length:
                        online.size = content_length
                    online.stream_count += 1
                    return online.video_url, None, online.title, None

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = audio_url = cookies = None
            title = info.get('title', None)
            duration = info.get('duration', None)
            description = info.get('description', None)
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

            # store in online database
            if video_url:
                online_thumbnail = info.get('thumbnail', None)
                online_resolution = info.get('resolution', None)
                with get_video_db() as db:
                    online = Online(video_url=video_url, original_url=url, title=title,
                                    date=int(datetime.now().timestamp()), thumbnail_url=online_thumbnail,
                                    resolution=online_resolution, info=json.dumps(info, default=str),
                                    size=content_length, duration=duration, description=description)
                    db.for_online_table.upsert_online(url, online)
                # clear list cache
                list_onlines.cache__clear()

        return video_url, audio_url, title, cookies
    except Exception as e:
        logger.error(f"Error retrieving video and audio streams: {e}")
        return None, None, None, None


def download_video(url, title):
    download_random_id = None

    try:
        with get_video_db() as db:
            download_random_id, current_download = db.for_download_table.next_download(url, title)

        push_text_to_client(f"Downloading video {download_random_id}")
        youtube_video = is_youtube_url(url)
        subfolder = 'youtube' if youtube_video else 'direct'
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
        download_date = int(datetime.now().timestamp())

        with get_video_db() as db:
            current_download.download_date = download_date
            current_download.file_name = basename
            current_download.title = title
            current_download.video_url = video_url
            current_download.original_url = url
            db.session.merge(current_download)

        list_files.cache__clear()
        # only generate thumbnails if download is a video check for file with extension ".unknown_video" this is not a video
        if not video_url.endswith(UNKNOWN_VIDEO_EXTENSION):
            generate_thumbnail_for_path(video_url)
            real_path, _ = get_real_path_from_url(video_url)
            video_uid = None
            if real_path:
                video_info = get_video_info(real_path)
                if video_info:
                    video_uid = video_info.get('infos', {}).get('video_uid', None)
            with get_video_db() as db:
                similarity = None
                features = build_features_for_video(video_url)
                if features:
                    similarity = Similarity(histogramm=features.histogram.tobytes(),
                                            phash=features.phash.tobytes(),
                                            hog=features.hog.tobytes())
                video = Videos(video_url=video_url, source_url=url, file_name=basename, title=title, download_id=download_random_id,
                               video_uid=video_uid, download_date=download_date, similarity=similarity)
                db.for_video_table.upsert_video(video_url, video)

        clear_similarity_cache()
        list_onlines.cache__clear()
        logger.debug(f"Download finished: {video_url}")
        push_text_to_client(f"Download finished: {video_url}")
    except Exception as e:
        logger.exception( f"Failed to download video: {e}")
        with get_video_db() as db:
            db.for_download_table.mark_download_failed(url)
        list_files.cache__clear()
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
            list_files.cache__clear()
        elif current_time - last_call_time < throttle_delay:
            return
        last_call_time = current_time
        output = f"{message} at {remove_ansi_codes(d['_speed_str'])}, ETA {remove_ansi_codes(d['_eta_str'])}"
    elif d['status'] == 'finished':
        fname = os.path.splitext(os.path.basename(d['filename']))[0]
        output = f"Downloading...[{video_id}] - 100.0% complete: {fname}"
    push_text_to_client(output)

def _add_video_to_db(file):
    video_url = file.get('filename')
    if not video_url:
        return

    with get_video_db() as db:
        video = db.for_video_table.get_video(video_url)
        # declare file variables for later use
        file_vars = {
            'file_name': file.get('basename'),
            'title': file.get('title'),
            'download_id': file.get('download_id'),
            'download_date': file.get('download_date'),
            'video_uid': file.get('uid'),
            'source_url': file.get('url')
        }

        if video:
            # update fields if they have changed
            for attr, value in file_vars.items():
                if getattr(video, attr) != value:
                    setattr(video, attr, value)
            if not video.similarity or video.similarity.histogramm is None or video.similarity.phash is None:
                features = build_features_for_video(video_url)
                if features:
                    video.similarity = Similarity(histogramm=features.histogram.tobytes(),
                                                  phash=features.phash.tobytes(),
                                                  hog=features.hog.tobytes())
        else:
            video = Videos(video_url=video_url, **file_vars)
            features = build_features_for_video(video_url)
            if features:
                video.similarity = Similarity(histogramm=features.histogram.tobytes(),
                                              phash=features.phash.tobytes(),
                                              hog=features.hog.tobytes())
            db.session.add(video)


def scan_for_videos():
    files = list_files()
    try:
        for i, file in enumerate(files):
            if i != 0 and i % 10 == 0:
                push_text_to_client(f"...scanned {i} videos - running")
            _add_video_to_db(file)

        clear_similarity_cache()
        push_text_to_client(f"Scanned {len(files)} videos finished")
    except Exception as e:
        logger.error(f"Error scanning for videos: {e}")
        push_text_to_client(f"Error scanning for videos: {e}")
        return ServerResponse(False, f"Error scanning for videos: {e}")
    return ServerResponse(True, f"Scanned {len(files)} videos")

