import argparse
import re

from files import list_files, rename_file_title
from globals import VideoFolder


def video_folder_type(folder_name):
    try:
        return VideoFolder[folder_name]
    except KeyError:
        raise argparse.ArgumentTypeError(f"Invalid folder name: {folder_name}")

def multi_rename(folder: VideoFolder):
    print('This small script will rename all file titles (not filenames) in the video folder to a new (better) name.')
    print('By removing all _ in Title and other tweaks.\n')

    files = list_files(VideoFolder.videos)
    count = 0
    # find rename candidates
    for file in files:
        filename = file.get('filename')
        if filename is None:
            continue

        title = file.get('title')
        original_title = title
        if title is None:
            continue

        # remove everything before ___ characters inclusive
        title = title.split('____')[-1]
        # remove [] and everything inside
        title = re.sub(r'\[.*?\]', '', title)
        # remove _ from title
        title = title.replace('_', ' ')
        # trim title
        title = title.strip()

        if title == original_title:
            continue

        print(f"Will rename Title: {original_title} -> {title}")
        rename_file_title(filename, title)
        count += 1

    print(f"Renamed {count} files.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Rename file titles in the specified video folder.')
    parser.add_argument('folder', type=video_folder_type, help='The folder to process')
    try:
        args = parser.parse_args()
    except Exception as e:
        parser.print_help()
        print(f"Parsing error: {e}")
        exit(1)

    if not args.folder:
        parser.print_help()
        exit(1)
    multi_rename(args.folder)
