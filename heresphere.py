import base64
import datetime
import os
import urllib.parse
from datetime import datetime
from flask import Blueprint, jsonify, request
from files import list_files, get_basic_save_video_info
from globals import get_static_directory
from thumbnail import ThumbnailFormat, get_thumbnails

heresphere_bp = Blueprint('heresphere', __name__)

@heresphere_bp.route('/heresphere', methods=['POST', 'GET'])
def heresphere():
    try:
        response = jsonify(generate_heresphere_json(request.root_url.rstrip('/')))
        response.headers['heresphere-json-version'] = '1'
        return response
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@heresphere_bp.route('/heresphere/<file_base64>', methods=['POST', 'GET'])
def heresphere_file(file_base64):
    try:
        return jsonify(generate_heresphere_json_item(request.root_url.rstrip('/'), file_base64))
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def generate_heresphere_json(server_path):
    """
    Generate the main JSON for the Heresphere VR player
    To present the overview of the library and downloads

    :param server_path: root path of the server
    :return: json object in the Heresphere format
    """

    result_json = {
        "access": 0,
        "library": [
            {"name": "Library", "list": []},
            {"name": "Downloads", "list": []}
        ]
    }

    for i, category in enumerate(['library', 'videos']):
        files = list_files(category)
        url_list = [
            f"{server_path}/heresphere/{base64.urlsafe_b64encode(file['filename'].encode()).decode()}"
            for file in files
        ]
        result_json["library"][i]["list"] = url_list

    return result_json

def generate_heresphere_json_item(server_path, file_base64):
    """
    Generate the JSON for a single item for the Heresphere VR player
    Heresphere VR player will make a request for each item in the library

    :param server_path: root path of the server
    :param file_base64: base64 encoded filename which is the path to the video file
    :return: json object in the Heresphere format for a single item
    """

    filename = base64.urlsafe_b64decode(file_base64.encode()).decode()
    base_name = os.path.basename(filename)
    static_dir = get_static_directory()
    if '/static/videos/' in filename:
        relative_path = filename.replace('/static/videos/', '')
        real_path = os.path.join(static_dir, 'videos', relative_path)
    else:
        relative_path = filename.replace('/static/library/', '')
        real_path = os.path.join(static_dir, 'library', relative_path)

    if not os.path.exists(real_path):
        return {}

    thumbnails = get_thumbnails(real_path)
    thumbnail_url = thumbnails[ThumbnailFormat.JPG]
    if thumbnail_url is None:
        thumbnail_url = "/static/images/placeholder.png"
    thumbnail = f"{server_path}{urllib.parse.quote(thumbnail_url)}"

    thumbnail_video_url = thumbnails[ThumbnailFormat.WEBM]
    if thumbnail_video_url is None:
        thumbnail_video_url = ''
    thumbnail_video = f"{server_path}{urllib.parse.quote(thumbnail_video_url)}"

    # get video info from the file
    get_basic_save_video_info(real_path)
    info = get_basic_save_video_info(real_path)
    date_added = datetime.fromtimestamp(info.created).strftime('%Y-%m-%d')

    result = {
        "title": os.path.splitext(base_name)[0],
        "description": "",
        "thumbnailImage": f"{thumbnail}",
        "thumbnailVideo": f"{thumbnail_video}",
        "dateReleased": "",
        "dateAdded": date_added,
        "duration": info.duration * 1000,
        "projection": "",
        "stereo": info.stereo,
        "isEyeSwapped": "",
        "fov": "",
        "lens": "",
        "tags": [],
        "media": [
            {
                "name": "Video",
                "sources": [
                    {
                        "resolution": info.resolution,
                        "height": info.height,
                        "width": info.width,
                        "size": os.path.getsize(real_path),
                        "url": f"{server_path}{urllib.parse.quote(filename)}",
                        "stream": ""
                    }
                ]
            }
        ],
        "favorites": 0,
        "comments": [],
        "rating": 0,
        "isFavorite": False,
        "writeFavorite": False,
    }
    return result
