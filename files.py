import os
import shutil

from loguru import logger
from bus import push_text_to_client
from cache import cache
from database import get_downloads_db
from globals import get_static_directory, VideoInfo, get_real_path_from_url, get_url_map, \
    VideoFolder, THUMBNAIL_DIR_NAME, ServerResponse, FolderState, UNKNOWN_VIDEO_EXTENSION, get_application_path
from utils import check_folder, get_mime_type
from thumbnail import ThumbnailFormat, get_video_info, get_thumbnails, update_file_info


@cache(maxsize=128, ttl=3600)
def library_subfolders() -> list:
    subfolders = []

    folder, folder_state = check_folder(os.path.join(get_static_directory(), VideoFolder.library.dir))
    if folder_state != FolderState.ACCESSIBLE:
        push_text_to_client(f"(For Subfolder) Library folder not accessible: {folder} - state: {folder_state}")
        logger.warning(f"(For Subfolder) Library folder not accessible: {folder} - state: {folder_state}")
        return subfolders

    for root, dirs, files in os.walk(folder, followlinks=True):
        # Exclude directories that start with a dot
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        subfolder = os.path.relpath(root, os.path.join(get_static_directory(), VideoFolder.library.dir)).replace('\\', '/')
        if subfolder != '.':
            subfolders.append(subfolder)
    return subfolders

@cache(maxsize=128, ttl=18000)
def list_files(directory: VideoFolder) -> list:
    extracted_details = []
    base_path = directory.web_path

    folder, folder_state = check_folder(os.path.join(get_static_directory(),  directory.dir))
    if folder_state != FolderState.ACCESSIBLE:
        push_text_to_client(f"(For list) Folder: {directory.dir} not accessible: {folder} - state: {folder_state}")
        logger.warning(f"(For list) Folder: {directory.dir} not accessible: {folder} - state: {folder_state}")
        return extracted_details

    for root, dirs, files in os.walk(folder, followlinks=True):
        # Exclude directories that start with a dot
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for filename in files:
            # ignore part-Frag and ytdl files
            if 'part-Frag' in filename or filename.endswith('.ytdl'):
                continue

            # ignore symbolic links for files, cause not mounted dirs are files on os.walk
            checkf = os.path.join(root, filename)
            if os.path.islink(checkf):
                continue

            subfolder = os.path.relpath(root, folder).replace('\\', '/')
            if subfolder == '.':
                subfolder = ''

            # for unknown files special handling
            if filename.endswith(UNKNOWN_VIDEO_EXTENSION):
                common_details = generic_file_details(root, filename, base_path, subfolder)
                extracted_details.append(common_details)
                continue

            common_details = extract_file_details(root, filename, base_path, subfolder)

            # only for videos directory
            if directory == VideoFolder.videos:
                download_id = filename.split('____')[0][:14]
                url_info = get_url_map().get(download_id, {})
                common_details.update({
                    'url_id': download_id,
                    **({k: url_info.get(k) for k in ['url', 'failed', 'download_date']} if url_info else {})
                })
            extracted_details.append(common_details)

    # check for duplicates
    duplicate_details = []
    if directory == VideoFolder.videos:
        # find extracted infos for library as well and add to duplicate list
        duplicate_details.extend(list_files(VideoFolder.library))
    duplicate_details.extend(extracted_details)

    uids: dict = {}
    for details in duplicate_details:
        uid = details.get('uid')
        if uid:
            if uid in uids:
                original_file = uids[uid]
                details['may_exist'] = f"id[{uid}]\n filename.[{details.get('filename')}]\n duplicate[{original_file}]"
                for original_details in duplicate_details:
                    if original_details.get('filename') == original_file:
                        original_details['may_exist'] = f"id[{uid}]\n filename.[{original_file}]\n duplicate[{details.get('filename')}]"
                        break
            else:
                uids[uid] = details.get('filename')

    extracted_details.sort(key=lambda x: x.get('created',0), reverse=True)
    return extracted_details


def generic_file_details(root: str, filename: str, base_weburl: str, subfolder: str) -> dict:
    """
    Extract details from a file in given directory

    :param root: root of the directory
    :param filename: the file to get details from
    :param base_weburl: base weburl of the file (url part)
    :param subfolder: subfolder of the file
    :return:  dictionary with extracted details
    """
    realfile = os.path.join(root, filename)
    if not os.path.exists(realfile):
        return {}
    mimetype, _ = get_mime_type(realfile)
    result = {
        'mimetype': mimetype,
        'unknown': True,
        'title': os.path.splitext(filename)[0],
        'filename': f"{base_weburl}{subfolder + '/' if subfolder else ''}{filename}",
        'filesize': os.path.getsize(realfile),
        'folder' : subfolder,
        'created': os.path.getctime(realfile)
    }
    return result

def extract_file_details(root: str, filename: str, base_weburl: str, subfolder: str) -> dict:
    """
    Extract details from a file in the videos directory

    :param root: the root directory
    :param filename: the filename
    :param base_weburl: base weburl of the file (url part)
    :param subfolder: subfolder of the file
    :return: dictionary with extracted details
    """

    realfile = os.path.join(root, filename)
    if not os.path.exists(realfile):
        return {}

    partial = filename.endswith('.part')
    result = {
        'partial': partial,
        'title': os.path.splitext(filename)[0],
        'filename': f"{base_weburl}{subfolder + '/' if subfolder else ''}{filename}",
        'folder' : subfolder,
        'favorite': False,
    }
    if partial:
        result.update({
            'created': os.path.getctime(realfile),
        })
    else:
        thumbnails = get_thumbnails(realfile)
        thumbnail = thumbnails.get(ThumbnailFormat.WEBP, ThumbnailFormat.JPG)
        preview = thumbnails.get(ThumbnailFormat.WEBM)
        info = get_basic_save_video_info(realfile)
        favorite = info.infos.get('favorite', False)
        url_info = info.infos.get('url_info', {})
        download_date = info.infos.get('download_date', url_info.get('downloaded_date', url_info.get('download_date', None)))
        url = url_info.get('url', None)

        result.update({
            'preview': preview,
            'thumbnail': thumbnail,
            'created': info.created,
            'filesize': info.size,
            'width': info.width,
            'height': info.height,
            'duration': info.duration,
            'resolution': info.resolution,
            'stereo': info.stereo,
            'uid': info.uid,
            'favorite': favorite,
            'download_date': download_date,
            'url': url,
        })
        if info.title:
            result['title'] = info.title
    return result


@cache(maxsize=4096, ttl=7200)
def get_basic_save_video_info(file_path: str) -> VideoInfo:
    """
    Get basic video information from a file,
    including created date, size, duration, width, height, resolution, stereo, uid and title

    :param file_path: the full file path to which information should be extracted
    :return: VideoInfo object with filled data including dict of infos from json
    """

    size = os.path.getsize(file_path)
    created = os.path.getctime(file_path)
    video_info = get_video_info(file_path)
    if video_info is not None:
        duration = int(float(video_info['format'].get('duration', 0))) if 'format' in video_info else 0
        width = video_info['streams'][0].get('width', 0) if 'streams' in video_info and len(
            video_info['streams']) > 0 else 0
        height = video_info['streams'][0].get('height', 0) if 'streams' in video_info and len(
            video_info['streams']) > 0 else 0
        resolution = max(width, height)
        if height > 0 and (width / height == 2):
            stereo = 'sbs'
        elif height > 0 and (width / height == 1):
            stereo = 'tb'
        else:
            stereo = ''
        infos = video_info.get('infos', {})
        uid = infos.get('unique_info', None)
        title = infos.get('title', None)
    else:
        duration = 0
        width = 0
        height = 0
        resolution = 0
        stereo = ''
        uid = None
        title = None
        infos = {}

    return VideoInfo(created, size, duration, width, height, resolution, stereo, uid, title, infos)

def move_file_for(source_folder: VideoFolder, video_path: str, subfolder: str) -> ServerResponse:
    """
    Move a file for a VideoFolder to or inside the library folder
    all thumbnails will be moved as well

    :param source_folder: source folder as VideoFolder enum
    :param video_path: full path to video file
    :param subfolder: subfolder in library
    :return: json object with success and library_path
    """

    push_text_to_client(f"Move file for {source_folder.dir} to/inside library: {video_path}")
    static_dir = get_static_directory()
    if source_folder.web_path in video_path:
        relative_path = video_path.replace(source_folder.web_path, '')
        real_path = os.path.join(static_dir, source_folder.dir, relative_path)

        if not os.path.exists(real_path):
            return ServerResponse(False, "Video file does not exist")

        base_name = os.path.basename(real_path)

        if subfolder and subfolder not in library_subfolders():
            return ServerResponse(False, "Invalid subfolder name")

        library_path = os.path.join(static_dir, VideoFolder.library.dir, subfolder, base_name)

        if os.path.exists(library_path):
            return ServerResponse(False, f"Target exists in library: {base_name}")

        move_file_with_thumbnails(real_path, library_path)
        return ServerResponse(True, f"moved {base_name} to {subfolder}")
    else:
        return ServerResponse(False, "Invalid video path")


def move_file_with_thumbnails(file_path: str, target_path: str) -> None:
    """
    Move a file and all thumbnails to a new location
    push a message to the client and clear the list cache

    :param file_path: file path to move
    :param target_path: target path to move to
    :return: None
    """

    # Move the video file
    shutil.move(file_path, target_path)

    # Move the thumbnails
    base_name = os.path.basename(file_path)
    thumbnail_dir = os.path.join(os.path.dirname(file_path), THUMBNAIL_DIR_NAME)
    if os.path.exists(thumbnail_dir):
        for fmt in ThumbnailFormat:
            thumbnail_path = os.path.join(thumbnail_dir, f"{base_name}{fmt.extension}")
            if os.path.exists(thumbnail_path):
                library_thumbnail_dir = os.path.join(os.path.dirname(target_path), THUMBNAIL_DIR_NAME)
                os.makedirs(library_thumbnail_dir, exist_ok=True)
                shutil.move(thumbnail_path, os.path.join(library_thumbnail_dir, f"{base_name}{fmt.extension}"))


    list_files.cache__clear()
    push_text_to_client(f"File and all thumbnails moved: {base_name}")



def delete_file(url: str) -> ServerResponse:
    """
    Delete a file from the videos directory and all thumbnails
    only allow to delete from videos directory

    :param url: url path to file
    :return: object with success and message
    """

    if not url:
        return ServerResponse(False, "URL missing")

    # only allow to delete from videos directory
    if VideoFolder.videos.web_path not in url:
        return ServerResponse(False, "Invalid URL")

    real_path, vid_folder = get_real_path_from_url(url)
    if not real_path:
        return ServerResponse(False, "File not found")

    # delete the file and thumbnails
    base_name = os.path.basename(real_path)
    thumbnail_dir = os.path.join(os.path.dirname(real_path), THUMBNAIL_DIR_NAME)
    if os.path.exists(thumbnail_dir):
        for fmt in ThumbnailFormat:
            thumbnail_path = os.path.join(thumbnail_dir, f"{base_name}{fmt.extension}")
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
    os.remove(real_path)
    list_files.cache__evict(vid_folder)
    push_text_to_client(f"File deleted: {base_name}")
    return ServerResponse(True, f"File {base_name} deleted")

def cleanup() -> ServerResponse:
    """
    Cleanup the tracking map by removing entries that no longer exist.
    Also, cleanup thumbnails that no longer have a corresponding video file.

    :return: object with success and message
    """

    get_url_map().clear()

    to_remove = []
    with get_downloads_db() as db:
        all_downloads = db.fetch_all('select * from downloads')
        for row in all_downloads:
            pk = row.get('id')
            video_url = row.get('video_url')
            if video_url:
                check_file = os.path.normpath(os.path.join(get_application_path(), video_url.lstrip('/')))
                logger.debug(f"Checking file: {check_file}")
                if not os.path.exists(check_file):
                    to_remove.append(pk)
                    db.delete_key(pk)
    logger.debug(f"removed orphan db entries: {to_remove}")
    push_text_to_client(f"Cleanup tracking map finished (removed: {len(to_remove)} entries).")

    # cleanup thumbnails from .thumb directory that no longer have a corresponding video file for both videos and library directory
    known_extensions = [fmt.extension for fmt in ThumbnailFormat]
    to_remove = []
    for directory in VideoFolder:
        folder, folder_state = check_folder(os.path.join(get_static_directory(), directory.dir))
        if folder_state != FolderState.ACCESSIBLE:
            logger.warning(f"Folder not accessible: {folder} - skipping cleanup - state: {folder_state}")
            continue

        # get all files from .thumb sub folders
        for root, dirs, files in os.walk(folder, followlinks=True):
            if THUMBNAIL_DIR_NAME in dirs:
                thumb_dir = os.path.join(root, THUMBNAIL_DIR_NAME)
                root_files = os.listdir(root)
                for filename in os.listdir(thumb_dir):
                    if not any(filename.startswith(f) for f in root_files):
                        if any(filename.endswith(ext) for ext in known_extensions):
                            thumb_file = os.path.join(thumb_dir, filename)
                            to_remove.append(thumb_file)
                            os.remove(thumb_file)

    push_text_to_client(f"Cleanup thumbnails finished (removed: {len(to_remove)} orphan entries).")
    list_files.cache__clear()
    return ServerResponse(True, "Cleanup finished")


def rename_file_title(video_path: str, new_title: str) -> ServerResponse:
    """
    Rename a file title

    :param video_path: url to video file
    :param new_title: the new title for the file
    :return: json object with success and library_path
    """

    push_text_to_client(f"Rename file for: {video_path}")

    if not new_title:
        return ServerResponse(False, "Invalid new title name")

    real_path, vid_folder = get_real_path_from_url(video_path)
    if not real_path:
        return ServerResponse(False, "File not found")

    with get_downloads_db() as db:
        db.change_title(video_path, new_title)

    # title update dict
    title_update = {
        'title': new_title,
        'url_info': {
            'title': new_title
        }
    }
    update_file_info(real_path, title_update)

    # clear the cache and push/return info
    get_basic_save_video_info.cache__evict(real_path)
    list_files.cache__evict(vid_folder)
    push_text_to_client(f"File renamed: {video_path}")
    return ServerResponse(True, f"File {video_path} renamed")


def set_favorite(video_path: str, favorite: bool = None) -> ServerResponse:
    """
    Set the favorite status of a video file

    :param video_path: url to video file
    :param favorite: favorite status to set to (True/False) or None to toggle
    :return: json object with success
    """

    push_text_to_client(f"Set favorite for: {video_path} - {favorite}")
    real_path, vid_folder = get_real_path_from_url(video_path)
    if not real_path:
        return ServerResponse(False, "File not found")

    base_name = os.path.basename(real_path)
    video_info = get_video_info(real_path) or {}
    infos = video_info.get('infos', {})
    current_favorite = infos.get('favorite', False)

    if favorite is None:
        favorite = not current_favorite

    # title update dict
    favorite_update = {
        'favorite': favorite,
    }
    update_file_info(real_path, favorite_update)
    with get_downloads_db() as db:
        db.set_favorite(video_path, favorite)

    # clear the cache and push/return info
    get_basic_save_video_info.cache__evict(real_path)
    list_files.cache__evict(vid_folder)
    push_text_to_client(f"File favorite changed to {favorite}: {base_name}")
    return ServerResponse(True, f"File {base_name} favorite changed")


def toggle_favorite(video_path: str) -> ServerResponse:
    """
    Toggle the favorite status of a video file

    :param video_path: url to video file
    :return: json object with success
    """
    return set_favorite(video_path)
