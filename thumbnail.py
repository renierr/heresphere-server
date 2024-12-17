import os
import subprocess

from loguru import logger

from bus import push_text_to_client
from globals import get_static_directory


def generate_thumbnails(library=False):
    static_dir = get_static_directory()
    video_dir = os.path.join(static_dir, 'videos' if not library else 'library')
    generated_thumbnails = []
    logger.debug(f"Generating thumbnails for videos in {video_dir}")
    push_text_to_client(f"Generating thumbnails for videos")

    for root, dirs, files in os.walk(video_dir):
        # Exclude directories that start with a dot
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for filename in files:
            if filename.endswith(('.mp4', '.mkv', '.avi', '.webm')):
                video_path = os.path.join(root, filename)
                thumbnail_dir = os.path.join(root, '.thumb')
                os.makedirs(thumbnail_dir, exist_ok=True)
                thumbnail_path = os.path.join(thumbnail_dir, f"{filename}.thumb.webp")

                if not os.path.exists(thumbnail_path):
                    success = generate_thumbnail(video_path, thumbnail_path)
                    if success:
                        generated_thumbnails.append(thumbnail_path)
    push_text_to_client(f"Generated thumbnails finished with {len(generated_thumbnails)} thumbnails")
    return {"success": True, "generated_thumbnails": generated_thumbnails}


def generate_thumbnail(video_path, thumbnail_path):
    try:
        # Use ffmpeg to generate a thumbnail
        #ffmpeg -i input_video.mp4 -vf "select='not(mod(n\,floor(n/10)))',scale=320:-1" -vsync vfr -frames:v 10 preview_%02d.png
        with open(os.devnull, 'w') as devnull:
            subprocess.run([
                'ffmpeg', '-i', video_path, '-loop', '0', '-vf', 'thumbnail,scale=w=1024:h=768:force_original_aspect_ratio=decrease', '-ss', '00:00:10.000', '-frames:v', '5', thumbnail_path
            ], check=True, stdout=devnull, stderr=devnull)
            subprocess.run([
                'ffmpeg', '-i', video_path, '-vf', 'thumbnail,scale=w=1024:h=768:force_original_aspect_ratio=decrease', '-ss', '00:00:10.000', '-frames:v', '1', os.path.splitext(thumbnail_path)[0] + '.jpg'
            ], check=True, stdout=devnull, stderr=devnull)
            subprocess.run([
                'ffmpeg', '-i', video_path, '-vf', 'thumbnail,scale=w=380:h=240:force_original_aspect_ratio=decrease', '-ss', '00:00:10.000', '-frames:v', '5', os.path.splitext(thumbnail_path)[0] + '.webm'
            ], check=True, stdout=devnull, stderr=devnull)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to generate thumbnail for {video_path}: {e}")
        return False


def get_thumbnail(filename):
    static_path = 'videos' if 'videos' in filename else '.'
    base_name = os.path.basename(filename)
    thumbfile = os.path.join(os.path.dirname(filename), '.thumb', f"{base_name}.thumb.webp")
    if not os.path.exists(thumbfile):
        return None
    relative_thumbfile = os.path.relpath(thumbfile, start=os.path.join(os.path.dirname(filename), '..')).replace('\\', '/')
    return f"/static/{static_path}/{relative_thumbfile}"
