import math
import os
import re
import sys
from collections import namedtuple
from dataclasses import dataclass
from enum import Enum
from typing import Tuple, Optional

DEBUG: bool = False
url_map = {}
url_counter: int = 1

ID_NAME_SEPERATOR = '____'
URL_MAP_JSON = 'url_map.json'
THUMBNAIL_DIR_NAME: str = '.thumb'
UNKNOWN_VIDEO_EXTENSION: str = '.unknown_video'
VideoInfo = namedtuple('VideoInfo', ['created', 'size', 'duration', 'width', 'height', 'resolution', 'stereo', 'uid', 'title', 'infos'])

class VideoFolder(Enum):
    library = ("library", "/static/library/")
    videos = ("videos", "/static/videos/")

    def __init__(self, directory, web_path):
        self.dir: str = directory
        self.web_path: str = web_path

class FolderState(Enum):
    ACCESSIBLE = 1
    NOT_READABLE = 2
    NOT_FOLDER = 3
    NOT_MOUNTED = 4
    CHECK_ERROR = 5

@dataclass
class ServerResponse:
    success: bool
    message: str

def set_debug(value) -> None:
    global DEBUG
    DEBUG = value

def is_debug() -> bool:
    return DEBUG

def get_url_map() -> dict:
    return url_map

application_path = None
def get_application_path() -> str:
    global application_path
    if application_path:
        return application_path

    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    else:
        try:
            app_full_path = os.path.realpath(__file__)
            application_path = os.path.dirname(app_full_path)
        except NameError:
            application_path = os.getcwd()
    return application_path


def get_static_directory() -> str:
    application_path = get_application_path()
    return os.path.join(application_path, 'static')

def get_data_directory() -> str:
    application_path = get_application_path()
    return os.path.join(application_path, 'data')


def remove_ansi_codes(text) -> str:
    ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)

def get_real_path_from_url(url) -> Tuple[Optional[str], Optional[VideoFolder]]:
    if not url:
        return None, None

    static_dir = get_static_directory()
    vid_folder = None
    if VideoFolder.library.web_path in url:
        relative_path = url.replace(VideoFolder.library.web_path, '')
        real_path = os.path.join(static_dir, VideoFolder.library.dir, relative_path)
        vid_folder = VideoFolder.library
    else:
        relative_path = url.replace(VideoFolder.videos.web_path, '')
        real_path = os.path.join(static_dir, VideoFolder.videos.dir, relative_path)
        vid_folder = VideoFolder.videos

    real_path = os.path.normpath(real_path)
    if not os.access(real_path, os.F_OK):
        return None, None

    return real_path, vid_folder


def format_duration(duration) -> str:
    """
    Format a duration in seconds to HH:MM:SS

    :param duration: duration in seconds
    :return: formatted duration string
    """
    hours = int(duration // 3600)
    minutes = int((duration % 3600) // 60)
    seconds = int(duration % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def format_byte_size(size_bytes) -> str:
    """
    Format a byte size into a human-readable string.

    :param size_bytes: size in bytes
    :return: formatted size string
    """
    if size_bytes == 0:
        return "0B"

    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"


