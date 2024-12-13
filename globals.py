import os

url_map = {}
url_counter = 1

def find_url_info(filename):
    for idnr, url_info in url_map.items():
        filename_check = os.path.splitext(filename.rstrip('.part'))[0]
        if url_info['filename'] == filename_check:
            return idnr, url_info
    return None, None
