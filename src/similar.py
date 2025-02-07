import os

import cv2
import numpy as np

from database.video_database import get_video_db
from files import list_files
from globals import VideoFolder, get_real_path_from_url, get_thumbnail_directory
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
        video = db.for_video_table.get_video(provided_video_path)
        if video:
            combined_features = np.frombuffer(video.similarity.features, dtype=np.float32)
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