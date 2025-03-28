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
        try:
            import magic # python-magic library (install with: pip install python-magic)
            mime = magic.Magic(mime=True) #Detect MIME from file content
            mime_type = mime.from_file(str(file_path))
        except ImportError:
            print("python-magic is not installed. Using only extension-based MIME type detection.")
        except magic.MagicException as e:
            print(f"Error during magic detection: {e}")

    return mime_type, encoding

