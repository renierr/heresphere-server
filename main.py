import json
import os
import logging
import socket
import subprocess
import sys
import threading
import time

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from enum import Enum
from typing import Optional
from werkzeug.exceptions import NotFound

import cache
import argparse

from waitress import serve
from queue import Queue
from threading import Event
from loguru import logger
from flask import Flask, Response, render_template, jsonify, send_from_directory, request
from files import library_subfolders, cleanup, list_files
from heresphere import heresphere_bp
from bus import client_remove, client_add, event_stream, push_text_to_client, clean_client_task, last_sse_messages
from globals import get_static_directory, set_debug, is_debug, get_application_path, VideoFolder, ServerResponse, \
    get_data_directory, get_frozen_static_directory
from migrate.migrate import migrate
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
UPDATE_SCRIPT_NAME = 'update.sh'

# Hide Flask debug banner
cli = sys.modules['flask.cli']
cli.show_server_banner = lambda *x: None

static_folder_path = get_static_directory()
logger.debug(f"Static Folder Path: {static_folder_path}")

class MultiStaticFlask(Flask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.static_folders = []
        if self.static_folder:
            self.static_folders.append(self.static_folder)

    def add_static_folder(self, folder):
        if folder not in self.static_folders and os.path.isdir(folder):
            self.static_folders.append(folder)

    def send_static_file(self, filename):
        for folder in self.static_folders:
            try:
                return send_from_directory(folder, filename)
            except NotFound:
                continue
        raise NotFound()

#app = Flask(__name__, static_folder=static_folder_path)
app = MultiStaticFlask(__name__, static_folder=static_folder_path)
frozen_static_path = get_frozen_static_directory()
if frozen_static_path:
    logger.debug(f"Using additional frozen static path: {frozen_static_path}")
    app.add_static_folder(frozen_static_path)

if is_debug():
    app.config['DEBUG'] = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
app.logger.setLevel(logging.WARNING)

# avoid jinja template directive conflict
app.jinja_env.variable_start_string = '[['
app.jinja_env.variable_end_string = ']]'


# own json encode to handle ServerResponse class
class ServerResponseJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ServerResponse):
            return obj.__dict__
        if isinstance(obj, Enum):
            return obj.name
        return super().default(obj)


app.json_encoder = ServerResponseJSONEncoder

# Register blueprints
app.register_blueprint(heresphere_bp)
app.register_blueprint(api_bp)
app.register_blueprint(video_bp)
app.register_blueprint(thumbnail_bp)

@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, NotFound):
        return jsonify(ServerResponse(False, "Not Found")), 404

    if is_debug():
        logger.exception(f"An error occurred: {e}")
    else:
        logger.error(f"An error occurred: {e}")

    response = {
        "error": "An unexpected error occurred",
        "message": str(e)
    }
    return jsonify(response), 500


@app.after_request
def add_cache_control(response):
    if 'static' in request.path:
        if 'v' in request.args:
            response.headers['Cache-Control'] = 'public, max-age=31536000'  # Cache for 1 year
    return response


@app.route('/favicon.png')
def favicon():
    return send_from_directory(app.static_folder, 'favicon.png', mimetype='image/png')


@app.route('/manifest.json')
def manifest():
    return send_from_directory(get_application_path(True), 'manifest.json', mimetype='application/json')


@app.route('/service-worker.js')
def service_worker():
    return send_from_directory(get_application_path(True), 'service-worker.js')


@app.context_processor
def inject_globals():
    return {
        'library_subfolders': library_subfolders(),
        'server_update_possible': os.path.exists(UPDATE_SCRIPT_NAME),
        'DEBUG': is_debug()
    }


@app.route('/')
@app.route('/bookmarks')
@app.route('/mosaic')
@app.route('/online')
def home():
    return render_template('index.html')


@app.route('/update')
def update():
    # check if update.sh file is present in root folder
    no_update_done = False
    if os.path.exists(UPDATE_SCRIPT_NAME):
        push_text_to_client("Update triggered, try to update server - possible connection lost, look for reconnect")
        try:
            process = subprocess.Popen(['sh', UPDATE_SCRIPT_NAME], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            # Read stdout line by line and push to client
            for line in process.stdout:
                push_text_to_client(line.strip())
                if "no restart required" in line:
                    no_update_done = True

            stderr_output = process.stderr.read().strip()
            if stderr_output:
                push_text_to_client(stderr_output)
        except Exception as e:
            push_text_to_client(f"Error during update call: {e}")
    else:
        push_text_to_client("Update triggered, no update.sh in root folder present!")
    return jsonify(ServerResponse(True, f"update finished {'no update/restart required' if no_update_done else ''}"))


@app.route('/cache')
def cache_stats():
    cache_stats = cache.get_all_cache_stats()
    return Response(json.dumps(cache_stats, cls=ServerResponseJSONEncoder), mimetype='application/json')

@app.route('/cache/clear')
@app.route('/cache/clear/<path:cache_name>')
def cache_clear(cache_name=None):
    if cache_name:
        ret = cache.clear_cache_by_name(cache_name)
    else:
        ret = cache.clear_caches()
    push_text_to_client(f"Clearing cache {cache_name if cache_name else ''} finished")
    return ret


@app.route('/sse')
def sse():
    client_queue: Queue = Queue()
    stop_event: Event = Event()
    client_add(client_queue, stop_event)

    def cleanup_client():
        stop_event.set()
        client_remove(client_queue, stop_event)

    if len(last_sse_messages) > 0:
        for msg in last_sse_messages:
            client_queue.put(f" - {msg}\n\n")
        client_queue.put("↓↓↓↓↓↓↓↓↓↓ Last 10 messages ↓↓↓↓↓↓↓↓↓↓\n\n")

    # send server time on first request
    client_queue.put(f"SSE Connection to Server established at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n\n")

    response = Response(event_stream(client_queue, stop_event), mimetype="text/event-stream")
    response.call_on_close(cleanup_client)
    return response


@app.route('/cleanup')
def cl():
    return jsonify(cleanup())


def start_server() -> Optional[str]:
    global ffmpeg_version_info, ffprobe_version_info

    if not is_debug():
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')

    logger.info(f"Server uses Python version: {sys.version}")

    # we need ffmpeg and ffprobe check if it is available in path
    try:
        ffmpeg_version_info = subprocess.check_output(["ffmpeg", "-version"], stderr=subprocess.STDOUT).decode().splitlines()[0]
        ffprobe_version_info = subprocess.check_output(["ffprobe", "-version"], stderr=subprocess.STDOUT).decode().splitlines()[0]
        logger.info(f"found ffmpeg: {ffmpeg_version_info}")
        logger.info(f"found ffprobe: {ffprobe_version_info}")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"ffmpeg or ffprobe is not available in path, can not run server.")
        return "ffmpeg is not available in path"
    except IndexError:
        logger.error("Unexpected output format from ffmpeg or ffprobe.")

    static_dir = get_static_directory()
    # make sure library and video directory exists and if not create them
    library_dir = os.path.join(static_dir, VideoFolder.library.dir)
    if not os.path.exists(library_dir) and not os.path.islink(library_dir):
        os.makedirs(library_dir, exist_ok=True)

    video_dir = os.path.join(static_dir, VideoFolder.videos.dir)
    if not os.path.exists(video_dir) and not os.path.islink(video_dir):
        os.makedirs(video_dir, exist_ok=True)

    # inside videos directory there should be a direct and a youtube directory
    direct_dir = os.path.join(video_dir, 'direct')
    if not os.path.exists(direct_dir) and not os.path.islink(direct_dir):
        os.makedirs(direct_dir, exist_ok=True)

    youtube_dir = os.path.join(video_dir, 'youtube')
    if not os.path.exists(youtube_dir) and not os.path.islink(youtube_dir):
        os.makedirs(youtube_dir, exist_ok=True)

    clean_client_task()

    logger.info("populating files cache in thread")
    threading.Thread(target=list_files, daemon=True).start()


    # Get the server's IP address
    hostname = socket.gethostname()
    server_ip = socket.gethostbyname(hostname)
    logger.info(f"Serving most likely on: http://{hostname}:{UI_PORT} or http://{server_ip}:{UI_PORT}")
    #app.run(debug=is_debug(), port=UI_PORT, use_reloader=False, host='0.0.0.0', threaded=True)
    serve(app, host='0.0.0.0', port=UI_PORT, threads=20)

def main():
    data_dir = get_data_directory()
    if not os.path.exists(data_dir) and not os.path.islink(data_dir):
        os.makedirs(data_dir, exist_ok=True)
    migrate()

    result = start_server()
    if result:
        logger.error(f"Server could not start: {result}")
        sys.exit(1)

if __name__ == '__main__':
    main()
