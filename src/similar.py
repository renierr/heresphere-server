import os

import cv2
import numpy as np

from database.video_database import get_video_db
from database.video_models import Similarity
from globals import get_static_directory, VideoFolder, THUMBNAIL_DIR_NAME
from thumbnail import ThumbnailFormat


def similar_compare(features_a, features_b):
    return cv2.compareHist(features_a, features_b, cv2.HISTCMP_CORREL)


def find_similar(provided_video_path, similarity_threshold=0.6) -> list:
    """
    Find similar videos to the provided video path.
    Currently only compares the similarity of the thumbnail images.
    Current video path is not included in the result

    :param provided_video_path: for which to find similar videos
    :param similarity_threshold: threshold for similarity default 0.4
    :return: list of similar videos with similarity score (tuple)
    """
    similars = []
    with (get_video_db() as db):
        similarity = db.for_similarity_table.get_similarity(provided_video_path)
        if similarity:
            combined_features = np.frombuffer(similarity.features, dtype=np.float32)
        else:
            return []

        # load all features for compare - TODO maybe cache this
        all_features = db.for_similarity_table.list_similarity()
        for row in all_features:
            video_path = row.video_url
            if video_path == provided_video_path:  # ignore myself in the comparison
                continue
            features_blob = row.features
            stored_features = np.frombuffer(features_blob, dtype=np.float32)
            similar = similar_compare(combined_features, stored_features)
            if similar > similarity_threshold:
                similars.append((video_path, int(similar * 100)))

    # Sort similar images by similarity score in descending order
    similars.sort(key=lambda x: x[1], reverse=True)
    return similars


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
    video_dir = os.path.join(get_static_directory(), folder.dir)
    for root, dirs, files in os.walk(video_dir, followlinks=True):
        # Exclude directories that start with a dot
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for filename in files:
            if filename.endswith(('.mp4', '.mkv', '.avi', '.webm')):
                relative_path = os.path.relpath(root, get_static_directory()).replace('\\', '/')
                video_path = f"/static/{relative_path}/{filename}"
                thumbnail_dir = os.path.join(root, THUMBNAIL_DIR_NAME)
                thumbnail_file = os.path.join(thumbnail_dir, f"{filename}{ThumbnailFormat.WEBM.extension}")
                if os.access(thumbnail_file, os.F_OK):
                    yield 'start', video_path, None
                    with get_video_db() as db:
                        similarity = db.for_similarity_table.get_similarity(video_path)
                        if similarity:
                            combined_features = np.frombuffer(similarity.features, dtype=np.float32)
                            yield 'exising', video_path, combined_features
                        else:
                            try:
                                combined_features = create_histogram(thumbnail_file)
                                db.for_similarity_table.upsert_similarity(video_path,
                                    Similarity(video_url=video_path, features=combined_features.tobytes())
                                )
                                yield 'new', video_path, combined_features
                            except ValueError as e:
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


if __name__ == '__main__':
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
