import base64

from flask import Blueprint, jsonify, request

from bookmarks import list_bookmarks, save_bookmark, delete_bookmark
from files import list_files, move_to_library, delete_file
from globals import VideoFolder

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/list')
def get_files():
    try:
        return jsonify(list_files())
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/api/library/list')
def get_library_files():
    try:
        return jsonify(list_files(VideoFolder.library))
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/api/move_to_library', methods=['POST'])
def mtl():
    data = request.get_json()
    video_path = data.get("video_path")
    subfolder = data.get("subfolder")

    if not video_path:
        return jsonify({"success": False, "error": "No video path provided"}), 400

    try:
        result = move_to_library(video_path, subfolder)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route('/api/bookmarks', methods=['GET'])
def gb():
    try:
        return jsonify(list_bookmarks())
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route('/api/bookmarks', methods=['POST'])
def sb():
    try:
        data = request.get_json()
        title = data.get("title")
        url = data.get("url")
        return jsonify(save_bookmark(data.get("title"), data.get("url")))
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route('/api/bookmarks', methods=['DELETE'])
def db():
    try:
        encoded_url = request.args.get('url')
        decoded_url = base64.urlsafe_b64decode(encoded_url).decode('utf-8')
        return jsonify(delete_bookmark(decoded_url))
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route('/api/files', methods=['DELETE'])
def df():
    try:
        encoded_url = request.args.get('url')
        decoded_url = base64.urlsafe_b64decode(encoded_url).decode('utf-8')
        return jsonify(delete_file(decoded_url))
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


