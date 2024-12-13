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
from globals import url_map, url_counter

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

def download_progress(d):
    output = ''
    if d['status'] == 'downloading':
        output = f"Downloading... {d['_percent_str']} complete at {d['_speed_str']}, ETA {d['_eta_str']}"
    elif d['status'] == 'finished':
        output = "Download completed", d['filename']
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


def download_video(url):
    global url_counter
    url_id = url_counter
    url_map[url_id] = {'url': url, 'filename': None}
    url_counter += 1

    try:
        video_url = None
        if is_youtube_url(url):
            video_url = download_yt(url, download_progress, url_id)
        else:
            video_url = download_direct(url, download_progress, url_id)
        push_text_to_client(f"Download finished: {video_url}")
    except Exception as e:
        error_message = f"Failed to download video: {e}\n{traceback.format_exc()}"
        logger.error(error_message)
        push_text_to_client(f"Download failed: {e}")
    finally:
        del url_map[url_id]

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
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')

    logger.info(f"""
Serving most likely on: http://localhost:{UI_PORT}
    """)

    app.run(debug=DEBUG, port=UI_PORT, use_reloader=False, host='0.0.0.0')

if __name__ == '__main__':
    start_server()

