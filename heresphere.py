import base64
import datetime
import os
import urllib.parse
from datetime import datetime
from flask import Blueprint, jsonify, request
from files import list_files, get_basic_save_video_info, library_subfolders
from globals import get_static_directory, VideoFolder
from thumbnail import ThumbnailFormat, get_thumbnails, get_video_info

heresphere_bp = Blueprint('heresphere', __name__)

@heresphere_bp.route('/heresphere', methods=['POST', 'GET'])
def heresphere():
    response = jsonify(generate_heresphere_json(request.root_url.rstrip('/')))
    response.headers['heresphere-json-version'] = '1'
    return response

@heresphere_bp.route('/heresphere/<file_base64>', methods=['POST', 'GET'])
def heresphere_file(file_base64):
    return jsonify(generate_heresphere_json_item(request.root_url.rstrip('/'), file_base64))


def generate_heresphere_json(server_path):
    """
    Generate the main JSON for the Heresphere VR player
    To present the overview of the library and downloads

    :param server_path: root path of the server
    :return: json object in the Heresphere format
    """

    result_json = {
        "access": 1,
        "library": []
    }

    subfolders = library_subfolders()
    all_library_files = list_files(VideoFolder.library)

    for subfolder in [''] + subfolders:
        files = [file for file in all_library_files if file.get('folder', '') == subfolder]
        url_list = [
            f"{server_path}/heresphere/{base64.urlsafe_b64encode(file['filename'].encode()).decode()}"
            for file in files
        ]
        name = "Library" if subfolder == '' else f"Library - {subfolder}"
        result_json["library"].append({"name": name, "list": url_list})

    # Add Downloads section
    files = list_files(VideoFolder.videos)
    url_list = [
        f"{server_path}/heresphere/{base64.urlsafe_b64encode(file['filename'].encode()).decode()}"
        for file in files
    ]
    result_json["library"].append({"name": "Downloads", "list": url_list})

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
    if VideoFolder.videos.web_path in filename:
        relative_path = filename.replace(VideoFolder.videos.web_path, '')
        real_path = os.path.join(static_dir, VideoFolder.videos.dir, relative_path)
    else:
        relative_path = filename.replace(VideoFolder.library.web_path, '')
        real_path = os.path.join(static_dir, VideoFolder.library.dir, relative_path)

    folders = os.path.dirname(relative_path)

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
    info = get_basic_save_video_info(real_path)
    date_added = datetime.fromtimestamp(info.created).strftime('%Y-%m-%d')
    favorite = info.infos.get('favorite', False)

    title = info.title
    if not title:
        title = os.path.splitext(base_name)[0]

    result = {
        "access": 1,
        "title": title,
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
        "isFavorite": favorite,
        "writeFavorite": False,
    }

    if folders:
        result["tags"] = [
            {
                "name": folders,
            }
        ]

    result.update(detect_vr_format(base_name, info.stereo))
    return result


def detect_vr_format(filename, sbs):
    """
    Detect VR video format from filename

    :param filename: filename to detect the VR format
    :param sbs: predefined stereo format - use it if exist (calculated from video resolution)
    :return: dictionary with VR format information
    """
    filename_lower = filename.lower()

    # check for stereo, possible values are "mono", "sbs", "tb"
    stereo = "mono"
    if sbs:
        stereo = sbs
    elif any(x in filename_lower for x in ["sbs", "side-by-side", "sidebyside", "_3d", "stereoscopic", "_lr", "_rl"]):
        stereo = "sbs"
    elif any(x in filename_lower for x in ["_tb", "_bt"]):
        stereo = "tb"

    # check for projection, possible values are "perspective", "equirectangular", "equirectangular360", "fisheye", "cubemap", "equiangularCubemap"
    projection = "perspective"
    if any(x in filename_lower for x in ["_180_", "180x180"]) or sbs == "sbs" or sbs == "tb":
        projection = "equirectangular"
    elif any(x in filename_lower for x in ["_360_", "360x180"]):
        projection = "equirectangular360"
    elif any(x in filename_lower for x in ["fisheye"]):
        projection = "fisheye"
    elif any(x in filename_lower for x in ["cubemap", "equiangularCubemap"]):
        projection = "cubemap"
    elif any(x in filename_lower for x in ["equiangularCubemap"]):
        projection = "equiangularCubemap"

    # check for fov, possible values is a decimal number with the actual FOV of the video (180.0 for example)
    fov = ""
    if any(x in filename_lower for x in ["_180_", "180x180"]):
        fov = 180.0
    elif any(x in filename_lower for x in ["_360_", "360x180"]):
        fov = 360.0
    elif any(x in filename_lower for x in ["_90_", "90x90"]):
        fov = 90.0

    # check for lens, possible values are "Linear", "MKX220", "MKX200", "VRCA220"
    lens = "Linear"
    if any(x in filename_lower for x in ["MKX220"]):
        lens = "MKX220"
    elif any(x in filename_lower for x in ["MKX200"]):
        lens = "MKX200"
    elif any(x in filename_lower for x in ["VRCA220"]):
        lens = "VRCA220"

    return {
        "projection": projection,
        "stereo": stereo,
        "fov": fov,
        "lens": lens
    }