import os
import shutil

from bus import push_text_to_client
from cache import cache
from globals import get_static_directory, find_url_info, VideoInfo, get_real_path_from_url
from thumbnail import get_thumbnail, ThumbnailFormat, get_video_info

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

            common_details = extract_file_details(root, filename, base_path)

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
                        'filename': f"{base_path}/youtube/{filename}"
                    })
                else:
                    common_details.update({
                        'filename': f"{base_path}/direct/{filename}"
                    })
            extracted_details.append(common_details)

    extracted_details.sort(key=lambda x: x['created'], reverse=True)
    return extracted_details


def extract_file_details(root, filename, base_path):
    realfile = os.path.join(root, filename)

    if not os.path.exists(realfile):
        return None

    partial = filename.endswith('.part')
    result = {
        'partial': partial,
        'yt_id': None,
        'title': os.path.splitext(filename)[0],
        'filename': f"{base_path}/{filename}",
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
        stereo = 'sbs' if width / height == 2 else ''
    else:
        duration = 0
        width = 0
        height = 0
        resolution = 0
        stereo = ''
    return VideoInfo(created, size, duration, width, height, resolution, stereo)


def move_to_library(video_path):
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
        library_path = os.path.join(static_dir, 'library', base_name)

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


        list_files.cache_clear()
        push_text_to_client(f"File moved to library: {base_name}")
        return {"success": True, "library_path": library_path}
    else:
        return {"success": False, "error": "Invalid video path"}


def delete_file(url):
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
    list_files.cache_clear()
    push_text_to_client(f"File deleted: {base_name}")
    return {"success": True, "message": f"File {base_name} deleted"}
