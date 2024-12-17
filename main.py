import atexit
from flask import Flask, Response, render_template, request, jsonify
import os
import logging
import sys
from loguru import logger

import thumbnail
from heresphere import generate_heresphere_json, generate_heresphere_json_item
from videos import get_stream, download_video
import api
import argparse
from bus import event_bus, push_text_to_client
import threading
from globals import save_url_map, load_url_map, get_url_map, get_static_directory, set_debug, is_debug

parser = argparse.ArgumentParser(description='Start the server.')
parser.add_argument('--port', type=int, default=5000, help='Port to run the server on')
parser.add_argument('--debug', action='store_true', default=False, help='Run the server in debug mode')
args = parser.parse_args()

set_debug(args.debug)
UI_PORT = args.port

log_level = 'DEBUG' if is_debug() else 'INFO'
logger.remove()
logger.add(sys.stdout, level=log_level)


# Hide Flask debug banner
cli = sys.modules['flask.cli']
cli.show_server_banner = lambda *x: None

static_folder_path = get_static_directory()

logger.debug(f"Static Folder Path: {static_folder_path}")

app = Flask(__name__, static_folder=static_folder_path)
if is_debug():
    app.config['TEMPLATES_AUTO_RELOAD'] = True
app.logger.setLevel(logging.WARNING)
# app.config['MIMETYPE'] = {
#     '.webp': 'image/webp'
# }


# @app.before_request
# def log_request_info():
#     logger.info(f"Request: {request.method} {request.url}")
#     logger.info(f"Headers: {request.headers}")
#     logger.info(f"Body: {request.get_data()}")
#
# @app.after_request
# def log_response_info(response):
#     logger.info(f"Response: {response.status}")
#     logger.info(f"Headers: {response.headers}")
#     logger.info(f"Body: {response.get_data()}")
#     return response

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/heresphere', methods=['POST', 'GET'])
def heresphere():
    logger.debug(f"HereSphere Request: {request.get_data()}")
    try:
        server_path = f"{request.scheme}://{request.host}"
        response = jsonify(generate_heresphere_json(server_path))
        response.headers['heresphere-json-version'] = '1'
        return response
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/heresphere/<file_base64>', methods=['POST', 'GET'])
def heresphere_file(file_base64):
    logger.debug(f"HereSphere File Request: {request.get_data()}")
    try:
        server_path = f"{request.scheme}://{request.host}"
        return jsonify(generate_heresphere_json_item(server_path, file_base64))
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/library')
def library():
    return render_template('library.html')

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

@app.route('/api/library/list')
def get_library_files():
    return jsonify(api.list_library_files())

@app.route('/api/list')
def get_files():
    try:
        return jsonify(api.list_files())
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/library/generate_thumbnails', methods=['POST'])
def generate_library_thumbnails():
    return generate_thumbnails(library=True)

@app.route('/api/generate_thumbnails', methods=['POST'])
def generate_thumbnails(library=False):
    try:
        thumbnail_thread = threading.Thread(target=thumbnail.generate_thumbnails, args=(library,))
        thumbnail_thread.daemon = True
        thumbnail_thread.start()

        push_text_to_client(f"Generate Thumbnails {'for library' if library else ''} started in the background")
        return jsonify({"success": True, "message": "Generate Thumbnails started in the background"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/generate_thumbnail', methods=['POST'])
def generate_thumbnail():
    data = request.get_json()
    video_path = data.get("video_path")

    if not video_path:
        return jsonify({"success": False, "error": "No video path provided"}), 400

    try:
        result = thumbnail.generate_thumbnail_for_path(video_path)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/move_to_library', methods=['POST'])
def move_to_library():
    data = request.get_json()
    video_path = data.get("video_path")

    if not video_path:
        return jsonify({"success": False, "error": "No video path provided"}), 400

    try:
        result = api.move_to_library(video_path)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

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

    app.run(debug=is_debug(), port=UI_PORT, use_reloader=False, host='0.0.0.0')

if __name__ == '__main__':
    start_server()

