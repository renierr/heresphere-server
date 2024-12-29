import os
import json
import re
import sys

DEBUG = False
url_map = {}
url_counter = 1

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
    with open(file_path, 'w') as f:
        json.dump(url_map, f)

def load_url_map(file_path='url_map.json'):
    global url_counter
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
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
