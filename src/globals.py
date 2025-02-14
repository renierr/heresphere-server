import math
import os
import re
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Tuple, Optional, NamedTuple

DEBUG: bool = False
url_counter: int = 1

ID_NAME_SEPERATOR = '____'
THUMBNAIL_DIR_NAME: str = '.thumb'
UNKNOWN_VIDEO_EXTENSION: str = '.unknown_video'

class VideoInfo(NamedTuple):
    created: float
    size: int
    duration: int
    width: int
    height: int
    resolution: str
    stereo: str
    uid: str
    title: str
    infos: Optional[dict]

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

application_path = None
def get_application_path() -> str:
    """
    Get the application path
    The application path is the directory where the application started from

    :return: application path
    """
    global application_path
    if application_path:
        return application_path

    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.getcwd()
    return application_path


def get_static_directory() -> str:
    """
    Get the static directory path
    The static directory is used to store the static files for the web interface - access via /static/
    Also where the videos are stored and served from.
    Thumbnails are stored in subfolders of the video directories

    :return: static directory path
    """
    application_path = get_application_path()
    return os.path.join(application_path, 'static')

def get_data_directory() -> str:
    """
    Get the data directory path
    The data directory is used to store the database and other data files
    """
    application_path = get_application_path()
    return os.path.join(application_path, 'data')


def remove_ansi_codes(text) -> str:
    ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)

def get_url_from_path(file_path, add_subfolder=None) -> Optional[str]:
    """
    Get the url from the given file path
    The URL is the relative path from the static directory, used to access the file from the web

    :param file_path: file path to get the url for
    :param add_subfolder: add a subfolder to the url
    :return: url for the given file path
    """
    if not file_path or not os.access(file_path, os.F_OK):
        return None
    base_name = os.path.basename(file_path)
    base_directory = os.path.dirname(file_path) if add_subfolder is None else os.path.join(os.path.dirname(file_path), add_subfolder)
    relative_path = os.path.relpath(base_directory, get_static_directory()).replace('\\', '/')
    return f"/static/{relative_path}/{base_name}"

def get_thumbnail_directory(file_path) -> str:
    """
    Get the thumbnail directory for the given file path

    :param file_path: file path to get the thumbnail directory for
    :return: thumbnail directory
    """
    if not file_path:
        raise ValueError("File path to get thumbnails dir for is None")
    base_directory = os.path.dirname(file_path)
    return os.path.join(base_directory, THUMBNAIL_DIR_NAME)

def get_real_path_from_url(url) -> Tuple[Optional[str], Optional[VideoFolder]]:
    """
    Get the real path from the given url

    :param url: url to get the real path for
    :return: real path and VideoFolder tuple
    """
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


