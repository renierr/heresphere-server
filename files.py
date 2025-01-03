import os
import shutil

from loguru import logger
from bus import push_text_to_client
from cache import cache
from globals import get_static_directory, find_url_info, VideoInfo, get_real_path_from_url, get_url_map, save_url_map
from thumbnail import get_thumbnail, ThumbnailFormat, get_video_info

@cache(maxsize=512, ttl=3600)
def library_subfolders():
    subfolders = []
    for root, dirs, files in os.walk(os.path.join(get_static_directory(), 'library'), followlinks=True):
        # Exclude directories that start with a dot
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        subfolder = os.path.relpath(root, os.path.join(get_static_directory(), 'library')).replace('\\', '/')
        if subfolder != '.':
            subfolders.append(subfolder)
    return subfolders

@cache(maxsize=512, ttl=120)
def list_files(directory='videos'):
    extracted_details = []
    base_path = f"/static/{directory}"

    for root, dirs, files in os.walk(os.path.join(get_static_directory(), directory), followlinks=True):
        # Exclude directories that start with a dot
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for filename in files:
            # ignore part-Frag and ytdl files
            if 'part-Frag' in filename or filename.endswith('.ytdl'):
                continue

            subfolder = os.path.relpath(root, os.path.join(get_static_directory(), directory)).replace('\\', '/')
            if subfolder == '.':
                subfolder = ''
            common_details = extract_file_details(root, filename, base_path, subfolder)

            # only for videos directory
            if directory == 'videos':
                url_id, url_info = find_url_info(filename)
                common_details.update({
                    'url_id': url_id,
                    **({k: url_info.get(k) for k in ['url', 'video_url', 'downloaded_date', 'may_exist']} if url_info else {})
                })

                if filename.count('___') == 1:
                    yt_id, title = parse_youtube_filename(filename)
                    common_details.update({
                        'yt_id': yt_id,
                        'title': title,
                    })
            extracted_details.append(common_details)

    extracted_details.sort(key=lambda x: x['created'], reverse=True)
    return extracted_details


def extract_file_details(root, filename, base_path, subfolder):
    realfile = os.path.join(root, filename)

    if not os.path.exists(realfile):
        return None

    partial = filename.endswith('.part')
    result = {
        'partial': partial,
        'yt_id': None,
        'title': os.path.splitext(filename)[0],
        'filename': f"{base_path}/{subfolder + '/' if subfolder else ''}{filename}",
        'folder' : subfolder,
    }
    if partial:
        result.update({
            'created': os.path.getctime(realfile),
        })
    else:
        thumbnail = get_thumbnail(realfile, ThumbnailFormat.WEBP, ThumbnailFormat.JPG)
        info = get_basic_save_video_info(realfile)
        result.update({
            'thumbnail': thumbnail,
            'created': info.created,
            'filesize': info.size,
            'width': info.width,
            'height': info.height,
            'duration': info.duration,
            'resolution': info.resolution,
            'stereo': info.stereo
        })
    return result


def parse_youtube_filename(filename):
    """
    Parse a YouTube filename into id and title
    The stored filename is in the format: id___title.ext

    :param filename: filename to parse
    :return: id, title
    """
    parts = filename.split('___')
    id_part = parts[0]
    title_part = parts[1]

    return id_part, title_part


@cache(maxsize=512)
def get_basic_save_video_info(filename):
    size = os.path.getsize(filename)
    created = os.path.getctime(filename)
    video_info = get_video_info(filename)
    if video_info is not None:
        duration = int(float(video_info['format'].get('duration', 0))) if 'format' in video_info else 0
        width = video_info['streams'][0].get('width', 0) if 'streams' in video_info and len(
            video_info['streams']) > 0 else 0
        height = video_info['streams'][0].get('height', 0) if 'streams' in video_info and len(
            video_info['streams']) > 0 else 0
        resolution = max(width, height)
        stereo = 'sbs' if (height > 0 and (width / height == 2)) else ''
    else:
        duration = 0
        width = 0
        height = 0
        resolution = 0
        stereo = ''
    return VideoInfo(created, size, duration, width, height, resolution, stereo)


def move_to_library(video_path, subfolder):
    """
    Move a video file from the videos folder to the library folder
    all thumbnails will be moved as well

    :param video_path: full path to video file
    :return: json object with success and library_path
    """
    push_text_to_client(f"Move file to library: {video_path}")
    static_dir = get_static_directory()
    if '/static/videos/' in video_path:
        relative_path = video_path.replace('/static/videos/', '')
        real_path = os.path.join(static_dir, 'videos', relative_path)

        if not os.path.exists(real_path):
            return {"success": False, "error": "Video file does not exist"}

        base_name = os.path.basename(real_path)

        if subfolder and subfolder not in library_subfolders():
            return {"success": False, "error": "Invalid subfolder name"}

        library_path = os.path.join(static_dir, 'library', subfolder, base_name)

        if os.path.exists(library_path):
            return {"success": False, "error": f"Target exists in library: {base_name}"}

        # Move the video file
        shutil.move(real_path, library_path)

        # Move the thumbnails
        thumbnail_dir = os.path.join(os.path.dirname(real_path), '.thumb')
        if os.path.exists(thumbnail_dir):
            for fmt in ThumbnailFormat:
                thumbnail_path = os.path.join(thumbnail_dir, f"{base_name}{fmt.extension}")
                if os.path.exists(thumbnail_path):
                    library_thumbnail_dir = os.path.join(os.path.dirname(library_path), '.thumb')
                    os.makedirs(library_thumbnail_dir, exist_ok=True)
                    shutil.move(thumbnail_path, os.path.join(library_thumbnail_dir, f"{base_name}{fmt.extension}"))


        list_files.cache__clear()
        push_text_to_client(f"File moved to library: {base_name}")
        return {"success": True, "moved": base_name}
    else:
        return {"success": False, "error": "Invalid video path"}


def delete_file(url):
    """
    Delete a file from the videos directory and all thumbnails
    only allow delete from videos directory

    :param url: url path to file
    :return: object with success and message
    """
    if not url:
        return {"success": False, "error": "URL missing"}

    # only allow delete from videos directory
    if not '/static/videos/' in url:
        return {"success": False, "error": "Invalid URL"}

    real_path = get_real_path_from_url(url)
    if not real_path:
        return {"success": False, "error": "File not found"}

    # delete the file and thumbnails
    base_name = os.path.basename(real_path)
    thumbnail_dir = os.path.join(os.path.dirname(real_path), '.thumb')
    if os.path.exists(thumbnail_dir):
        for fmt in ThumbnailFormat:
            thumbnail_path = os.path.join(thumbnail_dir, f"{base_name}{fmt.extension}")
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
    os.remove(real_path)
    list_files.cache__clear()
    push_text_to_client(f"File deleted: {base_name}")
    return {"success": True, "message": f"File {base_name} deleted"}

def cleanup():
    """
    Cleanup the tracking map by removing entries that no longer exist.
    Also cleanup thumbnails that no longer have a corresponding video file.

    :return: object with success and message
    """
    url_map = get_url_map()
    static_dir = get_static_directory()

    to_remove = []
    for url_id, url_info in url_map.items():
        filename = url_info.get('filename')
        logger.debug(f"Checking file: {filename}")
        if filename:
            youtube_dir = os.path.join(static_dir, 'videos', 'youtube')
            direct_dir = os.path.join(static_dir, 'videos', 'direct')
            youtube_files = os.listdir(youtube_dir)
            direct_files = os.listdir(direct_dir)
            if not any(f.startswith(filename) for f in youtube_files) and not any(f.startswith(filename) for f in direct_files):
                to_remove.append(url_id)

    logger.debug(f"to removed: {to_remove}")
    for url_id in to_remove:
        del url_map[url_id]

    save_url_map()
    push_text_to_client(f"Cleanup tracking map finished (removed: {len(to_remove)} entries).")

    # cleanup thumbnails from .thumb directory that no longer have a corresponding video file for both videos and library directory
    to_remove = []
    for directory in ['videos', 'library']:
        # get all files from .thumb sub folders
        for root, dirs, files in os.walk(os.path.join(static_dir, directory), followlinks=True):
            if '.thumb' in dirs:
                thumb_dir = os.path.join(root, '.thumb')
                root_files = os.listdir(root)
                for filename in os.listdir(thumb_dir):
                    if not any(filename.startswith(f) for f in root_files):
                        thumb_file = os.path.join(thumb_dir, filename)
                        to_remove.append(thumb_file)
                        os.remove(thumb_file)

    push_text_to_client(f"Cleanup thumbnails finished (removed: {len(to_remove)} orphan entries).")
    list_files.cache__clear()
    return {"success": True, "message": "Cleanup finished"}

