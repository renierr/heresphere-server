import atexit
from flask import Flask, Response, render_template, request, jsonify
import os
import logging
import sys
from loguru import logger
from videos import download_yt, get_stream, download_direct, is_youtube_url, get_static_directory
import api
import argparse
from bus import event_bus, push_text_to_client
import threading
import traceback
from globals import find_url_info, save_url_map, load_url_map, get_url_counter, get_url_map, increment_url_counter
import re

parser = argparse.ArgumentParser(description='Start the server.')
parser.add_argument('--port', type=int, default=5000, help='Port to run the server on')
parser.add_argument('--debug', action='store_true', default=False, help='Run the server in debug mode')
args = parser.parse_args()

DEBUG = args.debug
UI_PORT = args.port

log_level = 'DEBUG' if DEBUG else 'INFO'
logger.remove()
logger.add(sys.stdout, level=log_level)


# Hide Flask debug banner
cli = sys.modules['flask.cli']
cli.show_server_banner = lambda *x: None

static_folder_path = get_static_directory()

logger.debug(f"Static Folder Path: {static_folder_path}")

app = Flask(__name__, static_folder=static_folder_path)
if DEBUG:
    app.config['TEMPLATES_AUTO_RELOAD'] = True
app.logger.setLevel(logging.WARNING)

def remove_ansi_codes(text):
    ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)

def download_progress(d):
    output = ''
    fname = os.path.splitext(os.path.basename(d['filename']))[0]
    if d['status'] == 'downloading':
        idnr, _ = find_url_info(fname)
        output = f"Downloading...[{idnr}] - {remove_ansi_codes(d['_percent_str'])} complete at {remove_ansi_codes(d['_speed_str'])}, ETA {remove_ansi_codes(d['_eta_str'])}"
    elif d['status'] == 'finished':
        output = f"Download completed: {fname}"
    push_text_to_client(output)
    logger.debug(output)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/sse')
def sse():
    def event_stream():
        while True:
            # Wait for a message from the event bus
            message = event_bus.get()
            yield f'data: {message}\n\n'
    return Response(event_stream(), mimetype="text/event-stream")


@app.route('/connection_test')
def connection_test():
    return jsonify({"success": True})

@app.route('/api/list')
def get_files():
    return jsonify(api.list_files())


@app.route('/cleanup')
def cleanup_maps():
    url_map = get_url_map()
    static_dir = get_static_directory()

    to_remove = []
    for url_id, url_info in url_map.items():
        filename = url_info.get('filename')
        logger.debug(f"Checking file: {filename}")
        if filename:
            youtube_dir = os.path.join(static_dir, 'videos', 'youtube')
            direct_dir = os.path.join(static_dir, 'videos', 'direct')
            youtube_files = os.listdir(youtube_dir)
            direct_files = os.listdir(direct_dir)
            if not any(f.startswith(filename) for f in youtube_files) and not any(f.startswith(filename) for f in direct_files):
                to_remove.append(url_id)

    logger.debug(f"to removed: {to_remove}")
    for url_id in to_remove:
        del url_map[url_id]

    save_url_map()
    return jsonify({"success": True, "removed": to_remove})

def download_video(url):
    url_map = get_url_map()
    url_id = get_url_counter()
    url_map[url_id] = {'url': url, 'filename': None, 'video_url': None}
    increment_url_counter()

    try:
        video_url = None
        if is_youtube_url(url):
            video_url = download_yt(url, download_progress, url_id)
        else:
            video_url = download_direct(url, download_progress, url_id)
        url_map[url_id]['video_url'] = video_url
        push_text_to_client(f"Download finished: {video_url}")
    except Exception as e:
        error_message = f"Failed to download video: {e}\n{traceback.format_exc()}"
        logger.error(error_message)
        push_text_to_client(f"Download failed: {e}")
    #finally:
    #    del url_map[url_id]

@app.route('/download', methods=['POST'])
def download():
    push_text_to_client(f"Downloag triggered")
    data = request.get_json()
    url = data.get("sourceUrl")

    if not url:
        logger.error("No direct video URL provided in the request")
        return jsonify({"success": False, "error": "No URL provided"}), 400


    # Start a new thread for the download process
    download_thread = threading.Thread(target=download_video, args=(url,))
    download_thread.daemon = True
    download_thread.start()

    push_text_to_client(f"Download started in the background")

    return jsonify({"success": True, "message": "Download started in the background"})

@app.route('/stream', methods=['POST'])
def resolve_yt():
    data = request.get_json()
    url = data.get("url")

    if not url:
        logger.error("No URL provided in the request")
        return jsonify({"success": False, "error": "No URL provided"}), 400

    video_url, audio_url = get_stream(url)
    if video_url is None and audio_url is None:
        return jsonify({"success": False, "error": "Failed to retrieve video and audio streams"}), 500
    return jsonify({"success": True, "videoUrl": video_url, "audioUrl": audio_url})

def start_server():
    # Load url_map on startup
    load_url_map()

    # Register save_url_map to be called on application exit
    atexit.register(save_url_map)

    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')

    logger.info(f"""
Serving most likely on: http://localhost:{UI_PORT}
    """)

    app.run(debug=DEBUG, port=UI_PORT, use_reloader=False, host='0.0.0.0')

if __name__ == '__main__':
    start_server()

