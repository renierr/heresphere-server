import json
import os
import shutil

from loguru import logger
from bus import push_text_to_client
from cache import cache
from database.video_database import get_video_db
from database.video_models import Downloads
from globals import get_static_directory, VideoInfo, get_real_path_from_url, \
    VideoFolder, THUMBNAIL_DIR_NAME, ServerResponse, FolderState, UNKNOWN_VIDEO_EXTENSION, get_application_path, get_url_from_path, get_thumbnail_directory, ID_NAME_SEPERATOR
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


def find_file_info(video_url: str) -> dict | None:
    file_path, folder = get_real_path_from_url(video_url)
    if not file_path:
        return None

    root = os.path.dirname(file_path)
    subfolder = os.path.relpath(root, os.path.join(get_static_directory(),  folder.dir)).replace('\\', '/')
    if subfolder == '.':
        subfolder = ''

    return extract_file_details(root, os.path.basename(file_path), folder.web_path, subfolder)


@cache(maxsize=128)
def list_files() -> list:
    """
    List all files
    The returned list contains dictionaries with the following keys:

    - title: the title of the file
    - filename: the full url path to the file
    - folder: the subfolder of the file
    - created: the creation date of the file
    - filesize: the size of the file
    - mimetype: the mimetype of the file
    - duration: the duration of the video file
    - width: the width of the video file
    - height: the height of the video file
    - resolution: the resolution of the video file
    - stereo: the stereo mode of the video file
    - uid: the unique id of the video file
    - favorite: the favorite status of the video file
    - preview: the preview thumbnail of the video file
    - thumbnail: the thumbnail of the video file
    - partial: the partial status of the video file
    - download_id: the download id of the video file
    - url: the download url of the video file
    - download_date: the download date of the video file
    - may_exist: the possible duplicate file info


    :return: list of dictionaries with file details
    """
    extracted_details = []

    for directory in VideoFolder:
        base_path = directory.web_path
        folder, folder_state = check_folder(os.path.join(get_static_directory(),  directory.dir))
        if folder_state != FolderState.ACCESSIBLE:
            push_text_to_client(f"(For list) Folder: {directory.dir} not accessible: {folder} - state: {folder_state}")
            logger.warning(f"(For list) Folder: {directory.dir} not accessible: {folder} - state: {folder_state}")
            continue

        with get_video_db() as db:
            failed_downloads = [download.file_name for download in db.session.query(Downloads).filter_by(failed=True).all()]

        for root, dirs, files in os.walk(folder, followlinks=True):
            # Exclude directories that start with a dot
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            for filename in files:
                # ignore part-Frag and ytdl files
                if 'part-Frag' in filename or filename.endswith('.ytdl'):
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
                    if filename in failed_downloads:
                        common_details['failed'] = True
                extracted_details.append(common_details)

    # check for duplicates
    uids: dict = {}
    for details in extracted_details:
        uid = details.get('uid')
        if uid:
            if uid in uids:
                original_file = uids[uid]
                details['may_exist'] = json.dumps({
                    "id": uid,
                    "file": { "url": details.get('filename'), "title": details.get('title'), "img": details.get('thumbnail') },
                    "dup": { "url": original_file.get('filename'), "title": original_file.get('title'), "img": original_file.get('thumbnail') }
                })
                for original_details in extracted_details:
                    if original_details == original_file:
                        original_details['may_exist'] = json.dumps({
                            "id": uid,
                            "file": { "url": original_file.get('filename'), "title": original_file.get('title'), "img": original_file.get('thumbnail') },
                            "dup": { "url": details.get('filename'), "title": details.get('title'), "img": details.get('thumbnail') }
                        })
                        break
            else:
                uids[uid] = details

    extracted_details.sort(key=lambda x: x.get('created',0), reverse=True)
    return extracted_details


def generic_file_details(root: str, filename: str, base_weburl: str, subfolder: str) -> dict:
    """
    Extract details from a file in given directory
    The returned dictionary contains the following keys:

    - mimetype: the mimetype of the file
    - unknown: True
    - title: the title of the file
    - filename: the full url path to the file
    - folder: the subfolder of the file
    - created: the creation date of the file
    - filesize: the size of the file

    :param root: root of the directory
    :param filename: the file to get details from
    :param base_weburl: base weburl of the file (url part)
    :param subfolder: subfolder of the file
    :return:  dictionary with extracted details
    """
    realfile = os.path.join(root, filename)
    if not os.path.isfile(realfile):
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
    The returned dictionary contains the following keys:

    - title: the title of the file
    - filename: the full url path to the file
    - basename: the base name of the file
    - folder: the subfolder of the file
    - created: the creation date of the file
    - filesize: the size of the file
    - mimetype: the mimetype of the file
    - duration: the duration of the video file
    - width: the width of the video file
    - height: the height of the video file
    - resolution: the resolution of the video file
    - stereo: the stereo mode of the video file
    - uid: the unique id of the video file
    - favorite: the favorite status of the video file
    - preview: the preview thumbnail of the video file
    - thumbnail: the thumbnail of the video file
    - partial: the partial status of the video file
    - download_id: the download id of the video file
    - url: the download url of the video file
    - download_date: the download date of the video file


    :param root: the root directory
    :param filename: the filename
    :param base_weburl: base weburl of the file (url part)
    :param subfolder: subfolder of the file
    :return: dictionary with extracted details
    """

    realfile = os.path.join(root, filename)
    if not os.path.isfile(realfile):
        return {}

    partial = filename.endswith('.part')
    download_id = filename.split('____')[0][:14]
    result = {
        'partial': partial,
        'title': os.path.splitext(filename)[0],
        'filename': f"{base_weburl}{subfolder + '/' if subfolder else ''}{filename}",
        'basename': filename,
        'download_id': download_id,
        'folder' : subfolder,
        'favorite': False,
    }
    if partial:
        with get_video_db() as db:
            # find stuff for current download
            video_url = f"{download_id}{ID_NAME_SEPERATOR}downloading"
            download = db.for_download_table.get_download(video_url)
            if download:
                split_filename = os.path.splitext(filename)[0].split('____')
                file_title = split_filename[1] if len(split_filename) > 1 else split_filename[0]
                result.update({
                    'url': download.original_url,
                    'download_date': download.download_date,
                    'title': download.title if download.title else file_title,
                })
        result.update({
            'created': os.path.getctime(realfile),
        })
    else:
        mimetype, _ = get_mime_type(realfile)
        thumbnails = get_thumbnails(realfile)
        thumbnail = thumbnails.get(ThumbnailFormat.WEBP, thumbnails.get(ThumbnailFormat.JPG))
        preview = thumbnails.get(ThumbnailFormat.WEBM)
        info = get_basic_save_video_info(realfile)
        favorite = info.infos.get('favorite', False)
        download_date = info.infos.get('download_date')
        url = info.infos.get('original_url')

        result.update({
            'mimetype': mimetype,
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
        uid = infos.get('video_uid', infos.get('unique_info', None))    # unique_info is the old name
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

def move_file_for(video_path: str, subfolder: str) -> ServerResponse:
    """
    Move a file for a VideoFolder to or inside the library folder
    all thumbnails will be moved as well

    special subfolder name to move library file back to videos/direct directory: '~videos~'

    :param video_path: full path to video file
    :param subfolder: subfolder in library
    :return: json object with success and library_path
    """

    push_text_to_client(f"Move file to/inside library: {video_path}")
    static_dir = get_static_directory()
    real_path, _ = get_real_path_from_url(video_path)

    if not os.path.exists(real_path):
        return ServerResponse(False, "Video file does not exist")

    base_name = os.path.basename(real_path)

    if subfolder and subfolder not in library_subfolders() and subfolder != '~videos~':
        return ServerResponse(False, "Invalid subfolder name")

    # check special folder name to move library file back to videos/direct directory
    if subfolder == '~videos~':
        target_path = os.path.join(static_dir, VideoFolder.videos.dir, 'direct', base_name)
    else:
        target_path = os.path.join(static_dir, VideoFolder.library.dir, subfolder, base_name)

    if os.path.exists(target_path):
        return ServerResponse(False, f"Target exists in library: {base_name}")

    move_file_with_thumbnails(real_path, target_path)
    return ServerResponse(True, f"moved {base_name} to {subfolder}")


def move_file_with_thumbnails(file_path: str, target_path: str) -> None:
    """
    Move a file and all thumbnails to a new location
    push a message to the client and clear the list cache

    :param file_path: file path to move
    :param target_path: target path to move to
    :return: None
    """

    # Move the video file
    from_url = get_url_from_path(file_path)
    shutil.move(file_path, target_path)
    to_url = get_url_from_path(target_path)

    # update db
    if from_url and to_url:
        with get_video_db() as db:
            db.move_video(from_url, to_url)

    # Move the thumbnails
    base_name = os.path.basename(file_path)
    thumbnail_dir = get_thumbnail_directory(file_path)
    if os.path.exists(thumbnail_dir):
        for fmt in ThumbnailFormat:
            thumbnail_path = os.path.join(thumbnail_dir, f"{base_name}{fmt.extension}")
            if os.path.exists(thumbnail_path):
                library_thumbnail_dir = get_thumbnail_directory(target_path)
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

    real_path, vid_folder = get_real_path_from_url(url)
    if not real_path:
        return ServerResponse(False, "File not found")

    # delete the file and thumbnails
    base_name = os.path.basename(real_path)
    thumbnail_dir = get_thumbnail_directory(real_path)
    if os.path.exists(thumbnail_dir):
        for fmt in ThumbnailFormat:
            thumbnail_path = os.path.join(thumbnail_dir, f"{base_name}{fmt.extension}")
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
    os.remove(real_path)

    # delete from db
    with get_video_db() as db:
        db.for_video_table.delete_video(url)
        db.for_download_table.delete_download(url)

    list_files.cache__clear()
    push_text_to_client(f"File deleted: {base_name}")
    return ServerResponse(True, f"File {base_name} deleted")

def cleanup() -> ServerResponse:
    """
    Cleanup the tracking map by removing entries that no longer exist.
    Also, cleanup thumbnails that no longer have a corresponding video file.

    :return: object with success and message
    """

    to_remove = []
    with get_video_db() as db:
        all_downloads = db.for_download_table.list_downloads()
        for download in all_downloads:
            pk = download.id
            video_url = download.video_url
            if video_url:
                check_file = os.path.normpath(os.path.join(get_application_path(), video_url.lstrip('/')))
                logger.debug(f"Cleanup for download: {check_file}")
                if not os.path.isfile(check_file):
                    logger.debug(f"Removing: {video_url} for download")
                    to_remove.append(pk)
                    db.get_session().delete(download)
        all_videos = db.for_video_table.list_videos()
        for video in all_videos:
            video_url = video.video_url
            if video_url:
                check_file = os.path.normpath(os.path.join(get_application_path(), video_url.lstrip('/')))
                logger.debug(f"Cleanup for video: {check_file}")
                if not os.path.isfile(check_file):
                    logger.debug(f"Removing: {video_url} for video")
                    to_remove.append(video_url)
                    db.get_session().delete(video)

    logger.debug(f"removed orphan db entries: {to_remove}")
    push_text_to_client(f"Cleanup db entries finished (removed: {len(to_remove)} entries).")

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

    real_path, _ = get_real_path_from_url(video_path)
    if not real_path:
        return ServerResponse(False, "File not found")

    with get_video_db() as db:
        db.change_title(video_path, new_title)

    # title update dict
    title_update = {
        'title': new_title,
    }
    update_file_info(real_path, title_update)

    # clear the cache and push/return info
    get_basic_save_video_info.cache__evict(real_path)
    list_files.cache__clear()
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
    real_path, _ = get_real_path_from_url(video_path)
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
    with get_video_db() as db:
        db.set_favorite(video_path, favorite)

    # clear the cache and push/return info
    get_basic_save_video_info.cache__evict(real_path)
    list_files.cache__clear()
    push_text_to_client(f"File favorite changed to {favorite}: {base_name}")
    return ServerResponse(True, f"File {base_name} favorite changed")


def toggle_favorite(video_path: str) -> ServerResponse:
    """
    Toggle the favorite status of a video file

    :param video_path: url to video file
    :return: json object with success
    """
    return set_favorite(video_path)
