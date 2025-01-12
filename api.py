import base64

from flask import Blueprint, jsonify, request

from bookmarks import list_bookmarks, save_bookmark, delete_bookmark
from files import list_files, move_to_library, delete_file, move_inside_library
from globals import VideoFolder, ServerResponse

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/list')
def get_files():
    return jsonify(list_files(VideoFolder.videos))


@api_bp.route('/api/library/list')
def get_library_files():
    return jsonify(list_files(VideoFolder.library))


@api_bp.route('/api/move_to_library', methods=['POST'])
def mtl():
    data = request.get_json()
    video_path = data.get("video_path")
    subfolder = data.get("subfolder")

    if not video_path:
        return jsonify(ServerResponse(False, "No video path provided")), 400

    return jsonify(move_to_library(video_path, subfolder))


@api_bp.route('/api/move_inside_library', methods=['POST'])
def mil():
    data = request.get_json()
    video_path = data.get("video_path")
    subfolder = data.get("subfolder")

    if not video_path:
        return jsonify(ServerResponse(False, "No video path provided")), 400

    return jsonify(move_inside_library(video_path, subfolder))


@api_bp.route('/api/bookmarks', methods=['GET'])
def gb():
    return jsonify(list_bookmarks())

@api_bp.route('/api/bookmarks', methods=['POST'])
def sb():
    data = request.get_json()
    return jsonify(save_bookmark(data.get("title"), data.get("url")))

@api_bp.route('/api/bookmarks', methods=['DELETE'])
def db():
    encoded_url = request.args.get('url')
    decoded_url = base64.urlsafe_b64decode(encoded_url).decode('utf-8')
    return jsonify(delete_bookmark(decoded_url))

@api_bp.route('/api/files', methods=['DELETE'])
def df():
    encoded_url = request.args.get('url')
    decoded_url = base64.urlsafe_b64decode(encoded_url).decode('utf-8')
    return jsonify(delete_file(decoded_url))


