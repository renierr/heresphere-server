import base64
import os
import urllib.parse
from api import list_files
from globals import get_static_directory
from thumbnail import get_thumbnail, ThumbnailFormat, get_thumbnails


def generate_heresphere_json(server_path):
    result_json = {
        "access": 0,
        "library": [
            {
                "name": "Library",
                "list": []
            },
            {
                "name": "Downloads",
                "list": []
            }
        ]
    }

    files = list_files('library')
    url_list = []

    for file in files:
        filename = file['filename']
        file_base64 = base64.urlsafe_b64encode(filename.encode()).decode()
        url = f"{server_path}/heresphere/{file_base64}"
        url_list.append(url)
    result_json["library"][0]["list"] = url_list

    files = list_files('videos')
    url_list = []

    for file in files:
        filename = file['filename']
        file_base64 = base64.urlsafe_b64encode(filename.encode()).decode()
        url = f"{server_path}/heresphere/{file_base64}"
        url_list.append(url)
    result_json["library"][1]["list"] = url_list

    return result_json

def generate_heresphere_json_item(server_path, file_base64):
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