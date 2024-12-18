import base64
import os
import urllib.parse
from api import list_files
from globals import get_static_directory
from thumbnail import get_thumbnail, ThumbnailFormat, get_thumbnails

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

    result = {
        "title": os.path.splitext(base_name)[0],
        "description": "",
        "thumbnailImage": f"{thumbnail}",
        "thumbnailVideo": f"{thumbnail_video}",
        "dateReleased": "",
        "dateAdded": "",
        "duration": "",
        "projection": "",
        "stereo": "",
        "isEyeSwapped": "",
        "fov": "",
        "lens": "",
        "tags": [],
        "media": [
            {
                "name": "Video",
                "sources": [
                    {
                        "resolution": "",
                        "height": "",
                        "width": "",
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