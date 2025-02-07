import os

import cv2
import numpy as np

from cache import cache
from database.video_database import get_video_db
from files import list_files, find_file_info
from globals import VideoFolder, get_real_path_from_url, get_thumbnail_directory
from thumbnail import ThumbnailFormat


def similar_compare(features_a, features_b):
    return cv2.compareHist(features_a, features_b, cv2.HISTCMP_CORREL)

@cache(ttl=3600)
def _all_features():
    with get_video_db() as db:
        all_features = db.for_similarity_table.list_similarity()
        return [(row.video.video_url, np.frombuffer(row.features, dtype=np.float32)) for row in all_features]

def find_similar(provided_video_path, similarity_threshold=0.6, limit=10) -> list:
    """
    Find similar videos to the provided video path.
    Currently only compares the similarity of the thumbnail images.
    Current video path is not included in the result

    :param provided_video_path: for which to find similar videos
    :param similarity_threshold: threshold for similarity default 0.4
    :return: list of similar videos with similarity score (tuple)
    """

    all_features = _all_features()
    provided_features = None
    for video_path, features in all_features:
        if video_path == provided_video_path:
            provided_features = features
            break
    if provided_features is None:
        return []

    similars = []
    for video_path, features in all_features:
        if video_path == provided_video_path:    # ignore myself in the comparison
            continue
        similar = similar_compare(provided_features, features)
        if similar > similarity_threshold:
            file_info = find_file_info(video_path)
            similars.append((video_path, int(similar * 100), file_info))
            if len(similars) >= limit:
                break

    # Sort similar images by similarity score in descending order
    similars.sort(key=lambda x: x[1], reverse=True)
    return similars


def build_features_for_video(video_url: str) -> np.ndarray | None:
    """
    Build the features for the given video_url and return the features

    :param video_url: url of the video to build features for
    :return: features for the video
    """

    if not video_url:
        return None

    file_path, _ = get_real_path_from_url(video_url)
    if not file_path:
        return None

    base_name = os.path.basename(file_path)
    thumbnail_dir = get_thumbnail_directory(file_path)
    thumbnail_file = os.path.join(thumbnail_dir, f"{base_name}{ThumbnailFormat.WEBM.extension}")
    if os.access(thumbnail_file, os.F_OK):
        return create_histogram(thumbnail_file)
    return None


def fill_db_with_features(folder: VideoFolder):
    """
    Fill the database with features for all videos in the given folder (generator function)
    Yields a tuple with the state of the processing, the video path and the features
    state: 'start' - starting processing a video
           'existing' - video already has features in the database
           'new' - video has been processed and features added to the database

    uses the thumbnail webm file to get a histogram of the video

    :param folder: VideoFolder to process
    :return: tuple with state, video path and features
    """

    for file in list_files(folder):
        video_path = file.get('filename')
        if not video_path:
            continue

        file_path, _ = get_real_path_from_url(video_path)
        if not file_path:
            continue

        base_name = os.path.basename(file_path)
        thumbnail_dir = get_thumbnail_directory(file_path)
        thumbnail_file = os.path.join(thumbnail_dir, f"{base_name}{ThumbnailFormat.WEBM.extension}")
        if os.access(thumbnail_file, os.F_OK):
            yield 'start', video_path, None
            with get_video_db() as db:
                video = db.for_video_table.get_video(video_path)
                if video is None:
                    yield 'missing', video_path, None
                    continue

                if video.similarity:
                    combined_features = np.frombuffer(video.similarity.features, dtype=np.float32)
                    yield 'exising', video_path, combined_features
                else:
                    try:
                        combined_features = create_histogram(thumbnail_file)
                        db.for_similarity_table.update_features(video, combined_features.tobytes())
                        yield 'new', video_path, combined_features
                    except ValueError:
                        yield 'error', video_path, None


class VideoCaptureContext:
    def __init__(self, video_path):
        self.video_path = video_path
        self.cap = None

    def __enter__(self):
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            raise ValueError(f"Video at path {self.video_path} could not be loaded.")
        return self.cap

    def __exit__(self, exc_type, exc_value, traceback):
        if self.cap is not None:
            self.cap.release()


def create_histogram(video_path: str) -> np.ndarray:
    with VideoCaptureContext(video_path) as cap:
        hist_list = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            hist = cv2.calcHist([frame], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
            hist = cv2.normalize(hist, hist).flatten()
            hist_list.append(hist)

    avg_hist = np.mean(hist_list, axis=0)
    return avg_hist


def main():
    similarity_threshold = 0.5

    # fill db
    # for state, vid, features in fill_db_with_features(VideoFolder.videos):
    #    if state == 'start':
    #        print(f"Processing AI features for {vid}")
    #    else:
    #        print(state, vid, len(features))

    print("\n\nGrouping similar videos")
    with get_video_db() as db:
        all_features = db.for_similarity_table.list_similarity()
        video_data = [(row.video_url, np.frombuffer(row.features, dtype=np.float32)) for row in all_features]

    similarity_matrix = np.array([[similar_compare(f1[1], f2[1]) for f2 in video_data] for f1 in video_data])
    from collections import defaultdict

    similar_groups = defaultdict(list)

    for i in range(len(video_data)):
        for j in range(i + 1, len(video_data)):
            similarity = similar_compare(video_data[i][1], video_data[j][1])
            if similarity > similarity_threshold:
                similar_groups[video_data[i][0]].append((video_data[j][0], similarity))
                similar_groups[video_data[j][0]].append((video_data[i][0], similarity))

    for video, sim_video in similar_groups.items():
        print(f"Video: {video}")
        for similar_video, score in sim_video:
            print(f"  Score: {int(score * 100)} - Similar: {similar_video}")

    print(f"Found {len(video_data)} videos")

if __name__ == '__main__':
    main()