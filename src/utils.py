import errno
import os
import requests
import re
import mimetypes
from pathlib import Path
from loguru import logger
from globals import FolderState


def get_title_from_url(url, max_bytes=4096):
    """
    Retrieves title from given url
    first tries to get title from head request
    then from content - minimizing data transfer by checking during chunk download

    :param url: the URL of the webpage to get the title from
    :param max_bytes: the maximum number of bytes to download from the webpage - default is 4096
    :return: the title of the webpage or None if not found or an error occurs
    """
    try:
        head_response = requests.head(url, timeout=5)
        head_response.raise_for_status()

        if 'title' in head_response.headers:
            return head_response.headers['title']

        with requests.get(url, stream=True, timeout=10) as response:
            response.raise_for_status()

            content = b''
            for chunk in response.iter_content(chunk_size=512):
                if not chunk:  # Handle empty chunks (end of stream)
                    break

                content += chunk
                html_content = content.decode('utf-8', errors='ignore')

                title_match = re.search(r"<title>(.*?)</title>", html_content, re.IGNORECASE | re.DOTALL)
                if title_match:
                    return title_match.group(1).strip()

                if len(content) > max_bytes:
                    break

            return None # Return None if title not found after reaching max_bytes

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


def check_folder(path) -> tuple[str,FolderState]:
    """
    Checks if provided path accessible and return a state as tuple first is the provided path second is the state.

    Returns:
        FolderState.NOT_FOLDER if the path is not a folder or symlink points to an available mount point,
        FolderState.NOT_MOUNTED if the path is a symlink and  points to an unavailable mount point,
        FolderState.NOT_READABLE if the path is not readable.
        FolderState.NOT_FOLDER if the symlink points to a non-folder target.

    :param path: path to check
    :return: tuple of path and state
    """

    if not os.path.islink(path):
        if not os.path.isdir(path):
            return path, FolderState.NOT_FOLDER  # Target is not a folder
        else:
            # check if folder is readable
            if os.access(path, os.R_OK):
                return path, FolderState.ACCESSIBLE
            else:
                logger.error(f"Folder not readable: {path}")
                return path, FolderState.NOT_READABLE

    target_path = 'unknown'
    try:
        target_path = os.readlink(path)

        # Preliminary checks - faster checks first
        if not os.access(target_path, os.F_OK):
            return path, FolderState.NOT_MOUNTED  # Target does not exist
        if not os.access(target_path, os.R_OK):
            return path, FolderState.NOT_READABLE  # Target is not readable

        # Try to stat the target. If the mount point is unavailable,
        # this should raise an OSError with errno.ENXIO (No such device or address) or potentially other related errors.
        os.stat(target_path)  # Crucial check
        if not os.path.isdir(target_path):
            return path, FolderState.NOT_FOLDER  # Target is not a folder

        return path, FolderState.ACCESSIBLE  # Target is accessible
    except OSError as e:
        if e.errno in (112, errno.ENXIO, errno.ENOENT, errno.ESTALE, errno.ESHUTDOWN): #errno.ESTALE is for NFS stale file handles, 112 is Host down
            return path, FolderState.NOT_MOUNTED # Target is unavailable (likely unmounted)
        else:
            # Handle other OS errors if needed (e.g., permission issues)
            logger.error(f"Unexpected OSError: {e} for link: {path} target: {target_path}")
            return path, FolderState.CHECK_ERROR # Not related to mount point unavailability



def get_mime_type(file_path):
    """
    Determines the MIME type of file based on its extension and content.

    :param file_path: path to file
    :return: A tuple containing the MIME type (string) and encoding (string), or
        (None, None) if the MIME type cannot be determined.
        Raises FileNotFoundError if the file does not exist.
    """

    file_path = Path(file_path) # Convert to Path object for easier handling
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    mime_type, encoding = mimetypes.guess_type(str(file_path))

    # For more robust mime type detection (especially for files without extensions or with unusual extensions)
    if mime_type is None:
        # Check file signature for common file types
        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)  # Read first few bytes for signature detection

                # Check for common file signatures
                if header.startswith(b'\xFF\xD8\xFF'):  # JPEG
                    mime_type = 'image/jpeg'
                elif header.startswith(b'\x89PNG\r\n\x1a\n'):  # PNG
                    mime_type = 'image/png'
                elif header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):  # GIF
                    mime_type = 'image/gif'
                elif header.startswith(b'%PDF'):  # PDF
                    mime_type = 'application/pdf'
                elif header[0:4] == b'PK\x03\x04':  # ZIP, DOCX, XLSX, etc.
                    mime_type = 'application/zip'
                elif header.startswith(b'\x25\x21'):  # PostScript
                    mime_type = 'application/postscript'
                # Video formats
                elif header.startswith(b'\x00\x00\x00\x18ftypmp42'):  # MP4 (MPEG-4 Part 14)
                    mime_type = 'video/mp4'
                elif header.startswith(b'\x00\x00\x00\x1cftypmp42'):  # MP4
                    mime_type = 'video/mp4'
                elif header.startswith(b'\x00\x00\x00\x20ftypisom'):  # MP4 (ISO Base Media)
                    mime_type = 'video/mp4'
                elif header.startswith(b'\x00\x00\x00\x20ftypM4V'):  # M4V
                    mime_type = 'video/x-m4v'
                elif header.startswith(b'\x1A\x45\xDF\xA3'):  # MKV (Matroska)
                    mime_type = 'video/x-matroska'
                elif header.startswith(b'RIFF') and b'AVI' in header:  # AVI
                    mime_type = 'video/x-msvideo'
                elif header.startswith(b'OggS'):  # OGG (container for Theora, etc.)
                    mime_type = 'video/ogg'
                elif header.startswith(b'\x00\x00\x00\x14ftyf'):  # MPEG-4 video
                    mime_type = 'video/mp4'
                elif header.startswith(b'\x1C\x00\x00\x00') and b'webm' in header:  # WebM
                    mime_type = 'video/webm'
                elif header.startswith(b'\x00\x00\x01\xBA') or header.startswith(b'\x00\x00\x01\xB3'):  # MPEG (1/2)
                    mime_type = 'video/mpeg'
                elif header.startswith(b'FLV'):  # Flash Video
                    mime_type = 'video/x-flv'
                # Add more signature checks as needed

        except IOError as e:
            logger.warning(f"Could not read file for signature check: {e}")

    # Try using file command if available (Unix/Linux/macOS)
    if mime_type is None and os.name != 'nt':  # Not Windows
        try:
            import subprocess
            output = subprocess.check_output(['file', '--mime-type', '-b', str(file_path)])
            mime_type = output.decode('utf-8').strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning("Could not determine MIME type using 'file' command")

    return mime_type, encoding

