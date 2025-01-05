import atexit
import os
import logging
import socket
import subprocess
import sys
import time

import cache
import argparse

from waitress import serve
from queue import Queue
from threading import Event
from loguru import logger
from flask import Flask, Response, render_template, jsonify, send_from_directory, request

from files import library_subfolders, cleanup
from heresphere import heresphere_bp
from bus import client_remove, client_add, event_stream, push_text_to_client
from globals import save_url_map, load_url_map, get_url_map, get_static_directory, set_debug, is_debug
from thumbnail import thumbnail_bp
from videos import video_bp
from api import api_bp

parser = argparse.ArgumentParser(description='Start the server.')
parser.add_argument('--port', type=int, default=5000, help='Port to run the server on')
parser.add_argument('--debug', action='store_true', default=False, help='Run the server in debug mode')
args = parser.parse_args()

set_debug(args.debug)
UI_PORT = args.port

log_level = 'DEBUG' if is_debug() else 'INFO'
logger.remove()
logger.add(sys.stdout, level=log_level)

# Global variables to store ffmpeg and ffprobe version information
ffmpeg_version_info = None
ffprobe_version_info = None

# Hide Flask debug banner
cli = sys.modules['flask.cli']
cli.show_server_banner = lambda *x: None

static_folder_path = get_static_directory()
logger.debug(f"Static Folder Path: {static_folder_path}")

app = Flask(__name__, static_folder=static_folder_path)
if is_debug():
    app.config['DEBUG'] = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
app.logger.setLevel(logging.WARNING)

# avoid jinja template directive conflict
app.jinja_env.variable_start_string = '[['
app.jinja_env.variable_end_string = ']]'

# Register blueprints
app.register_blueprint(heresphere_bp)
app.register_blueprint(api_bp)
app.register_blueprint(video_bp)
app.register_blueprint(thumbnail_bp)

# debug purpose only
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

@app.after_request
def add_cache_control(response):
    if 'static' in request.path:
        if 'v' in request.args:
            response.headers['Cache-Control'] = 'public, max-age=31536000'  # Cache for 1 year
        elif not any(request.path.endswith(ext) for ext in ['.js', '.css', '.html', '.json']):
            response.headers['Cache-Control'] = 'public, max-age=2592000'  # Cache for 1 month
    return response

@app.route('/favicon.png')
def favicon():
    return send_from_directory(app.static_folder, 'favicon.png', mimetype='image/png')

@app.context_processor
def inject_globals():
    return {
        'library_subfolders': library_subfolders(),
    }

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/library')
def library():
    return render_template('library.html')

@app.route('/bookmarks')
def bookmarks():
    return render_template('bookmarks.html')


@app.route('/cache')
def cache_stats():
    return cache.get_all_cache_stats()

@app.route('/cache/clear')
def cache_clear():
    push_text_to_client("Clearing all caches finished")
    return cache.clear_caches()

@app.route('/sse')
def sse():
    client_queue = Queue()
    stop_event = Event()
    client_add(client_queue, stop_event)

    def cleanup():
        client_remove(client_queue, stop_event)

    # send server time on first request
    client_queue.put(f"SSE Connection to Server established at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n\n")

    # Send ffmpeg and ffprobe version information on first request
    if ffmpeg_version_info and ffprobe_version_info:
        client_queue.put(f"Server uses ffmpeg: {ffmpeg_version_info}\n\n")
        client_queue.put(f"Server uses ffprobe: {ffprobe_version_info}\n\n")

    response = Response(event_stream(client_queue, stop_event), mimetype="text/event-stream")
    response.call_on_close(cleanup)
    return response

@app.route('/cleanup')
def cl():
    return jsonify(cleanup())

def start_server():
    global ffmpeg_version_info, ffprobe_version_info

    # Load url_map on startup
    load_url_map()

    # Register save_url_map to be called on application exit
    atexit.register(save_url_map)

    if not is_debug():
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')

    # we need ffmpeg and ffprobe check if it is available in path
    logger.info("Checking for ffmpeg and ffprobe")
    try:
        ffmpeg_version_info = subprocess.check_output(["ffmpeg", "-version"], stderr=subprocess.STDOUT).decode().splitlines()[0]
        ffprobe_version_info = subprocess.check_output(["ffprobe", "-version"], stderr=subprocess.STDOUT).decode().splitlines()[0]
        logger.info(f"found ffmpeg: {ffmpeg_version_info}")
        logger.info(f"found ffprobe: {ffprobe_version_info}")
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg or ffprobe is not available in path, can not run server. Output: {e.output.decode()}")
        return "ffmpeg is not available in path"
    except IndexError:
        logger.error("Unexpected output format from ffmpeg or ffprobe.")

    static_dir = get_static_directory()
    if not os.path.exists(static_dir):
        logger.error("Static directory does not exist, can not run server")
        return "Static directory does not exist"

    # make sure library and video directory exists and if not create them
    library_dir = os.path.join(static_dir, 'library')
    if not os.path.exists(library_dir) and not os.path.islink(library_dir):
        os.makedirs(library_dir, exist_ok=True)

    video_dir = os.path.join(static_dir, 'videos')
    if not os.path.exists(video_dir) and not os.path.islink(video_dir):
        os.makedirs(video_dir, exist_ok=True)

    # inside videos directory there should be a direct and a youtube directory
    direct_dir = os.path.join(video_dir, 'direct')
    if not os.path.exists(direct_dir) and not os.path.islink(direct_dir):
        os.makedirs(direct_dir, exist_ok=True)

    youtube_dir = os.path.join(video_dir, 'youtube')
    if not os.path.exists(youtube_dir) and not os.path.islink(youtube_dir):
        os.makedirs(youtube_dir, exist_ok=True)

    # Get the server's IP address
    hostname = socket.gethostname()
    server_ip = socket.gethostbyname(hostname)
    logger.info(f"Serving most likely on: http://{hostname}:{UI_PORT} or http://{server_ip}:{UI_PORT}")
    #app.run(debug=is_debug(), port=UI_PORT, use_reloader=False, host='0.0.0.0', threaded=True)
    serve(app, host='0.0.0.0', port=UI_PORT, threads=100)

if __name__ == '__main__':
    start_server()

