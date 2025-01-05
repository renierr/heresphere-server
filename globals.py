import math
import os
import json
import re
import sys
from collections import namedtuple

DEBUG = False
url_map = {}
url_counter = 1

VideoInfo = namedtuple('VideoInfo', ['created', 'size', 'duration', 'width', 'height', 'resolution', 'stereo', 'uid'])

def set_debug(value):
    global DEBUG
    DEBUG = value

def is_debug():
    return DEBUG

def get_url_map():
    return url_map

def get_url_counter():
    return url_counter

def increment_url_counter():
    global url_counter
    url_counter += 1
    return url_counter

def find_url_id(url):
    for url_id, url_info in url_map.items():
        if url_info.get('url') == url:
            return url_id
    return None

def find_url_info(filename):
    for idnr, url_info in url_map.items():
        filename_check = os.path.splitext(filename.rstrip('.part'))[0]
        filename_info = url_info.get('filename', None)
        if filename and filename_info and filename_check.startswith(filename_info):
            return idnr, url_info
    return None, None

def save_url_map(file_path='url_map.json'):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(url_map, f, indent=2, ensure_ascii=False)

def load_url_map(file_path='url_map.json'):
    global url_counter
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            loaded_url_map = json.load(f)
            url_map.update(loaded_url_map)
            if loaded_url_map:
                url_counter = max(int(key) for key in loaded_url_map.keys()) + 1


def get_application_path():
    application_path = os.path.dirname(os.path.abspath(__file__))
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    else:
        try:
            app_full_path = os.path.realpath(__file__)
            application_path = os.path.dirname(app_full_path)
        except NameError:
            application_path = os.getcwd()
    return application_path


def get_static_directory():
    application_path = get_application_path()
    return os.path.join(application_path, 'static')


def remove_ansi_codes(text):
    ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)

def get_real_path_from_url(url):
    if not url:
        return None

    static_dir = get_static_directory()
    if '/static/library/' in url:
        relative_path = url.replace('/static/library/', '')
        real_path = os.path.join(static_dir, 'library', relative_path)
    else:
        relative_path = url.replace('/static/videos/', '')
        real_path = os.path.join(static_dir, 'videos', relative_path)

    real_path = os.path.normpath(real_path)
    if not os.path.exists(real_path):
        return None

    return real_path


def format_duration(duration):
    """
    Format a duration in seconds to HH:MM:SS

    :param duration: duration in seconds
    :return: formatted duration string
    """
    hours = int(duration // 3600)
    minutes = int((duration % 3600) // 60)
    seconds = int(duration % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def format_byte_size(size_bytes):
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
