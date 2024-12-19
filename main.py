import atexit
import os
import logging
import sys
from queue import Queue
from threading import Event

import cache
import argparse

from loguru import logger
from flask import Flask, Response, render_template, jsonify
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


# Hide Flask debug banner
cli = sys.modules['flask.cli']
cli.show_server_banner = lambda *x: None

static_folder_path = get_static_directory()

logger.debug(f"Static Folder Path: {static_folder_path}")

app = Flask(__name__, static_folder=static_folder_path)
if is_debug():
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

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/library')
def library():
    return render_template('library.html')

@app.route('/cache')
def cache_stats():
    return cache.get_all_cache_stats()

@app.route('/cache/clear')
def cache_clear():
    return cache.clear_caches()

@app.route('/sse')
def sse():
    client_queue = Queue()
    stop_event = Event()
    client_add(client_queue, stop_event)

    def cleanup():
        client_remove(client_queue, stop_event)

    response = Response(event_stream(client_queue, stop_event), mimetype="text/event-stream")
    response.call_on_close(cleanup)
    return response

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
    push_text_to_client(f"Cleanup tracking map finished (removed: {len(to_remove)} entries).")
    return jsonify({"success": True, "message": "Cleanup tracking map finished"})


def start_server():
    # Load url_map on startup
    load_url_map()

    # Register save_url_map to be called on application exit
    atexit.register(save_url_map)

    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')

    logger.info(f"Serving most likely on: http://localhost:{UI_PORT}")
    app.run(debug=is_debug(), port=UI_PORT, use_reloader=False, host='0.0.0.0')

if __name__ == '__main__':
    start_server()

