import base64
import os

from api import list_library_files
from globals import get_static_directory


def generate_heresphere_json(server_path):
    result_json = {
        "access": 0,
        "library": [
            {
                "name": "Newest",
                "list": []
            }
        ]
    }

    files = list_library_files()
    url_list = []

    for file in files:
        filename = file['filename']
        file_base64 = base64.urlsafe_b64encode(filename.encode()).decode()
        url = f"{server_path}/heresphere/{file_base64}"
        url_list.append(url)
    result_json["library"][0]["list"] = url_list
    return result_json

def generate_heresphere_json_item(server_path, file_base64):
    filename = base64.urlsafe_b64decode(file_base64.encode()).decode()
    base_name = os.path.basename(filename)
    static_dir = get_static_directory()
    real_path = os.path.join(static_dir, 'library', base_name)

    if not os.path.exists(real_path):
        return {}

    thumbnail_path = os.path.join(static_dir, 'library/.thumb', f"{base_name}.thumb.jpg")
    if os.path.exists(thumbnail_path):
        thumbnail = f"{server_path}/static/library/.thumb/{os.path.basename(thumbnail_path)}"
    else:
        thumbnail = f"{server_path}/static/images/placeholder.png"

    thumbnail_video_path = os.path.join(static_dir, 'library/.thumb', f"{base_name}.thumb.webm")
    if os.path.exists(thumbnail_video_path):
        thumbnail_video = f"{server_path}/static/library/.thumb/{os.path.basename(thumbnail_video_path)}"
    else:
        thumbnail_video = ""

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
                        "url": f"{server_path}{filename}",
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