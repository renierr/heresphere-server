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

def clear_similarity_cache():
    _all_features.cache__clear()

@cache(ttl=3600)
def _all_features():
    with get_video_db() as db:
        all_features = db.for_similarity_table.list_similarity()
        return [(row.video.video_url, np.frombuffer(row.histogramm, dtype=np.float32)) for row in all_features]

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

    # Sort similar images by similarity score in descending order
    similars.sort(key=lambda x: x[1], reverse=True)
    return similars[:limit]


def build_features_for_video(video_url: str) -> tuple[np.ndarray | None, np.ndarray | None]:
    """
    Build the features for the given video_url and return the features
    uses the thumbnail webm file to get a histogram and phash of the video

    :param video_url: url of the video to build features for
    :return: features for the video tuple (histogram, phash) or None if not possible
    """

    if not video_url:
        return None, None

    file_path, _ = get_real_path_from_url(video_url)
    if not file_path:
        return None, None

    base_name = os.path.basename(file_path)
    thumbnail_dir = get_thumbnail_directory(file_path)
    thumbnail_file = os.path.join(thumbnail_dir, f"{base_name}{ThumbnailFormat.WEBM.extension}")
    if os.access(thumbnail_file, os.F_OK):
        return _create_video_features_for_similarity_compare(thumbnail_file)
    return None, None


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


def _create_video_features_for_similarity_compare(video_path: str, skip_frames=10) -> tuple[np.ndarray, np.ndarray]:
    with VideoCaptureContext(video_path) as cap:
        hist_list = []
        phash_list = []

        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count > 0 and frame_count % skip_frames != 0:
                continue
            frame_count += 1

            # Calculate histogram
            hist_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            hist = cv2.calcHist([hist_frame], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
            hist = cv2.normalize(hist, hist).flatten()
            hist_list.append(hist)

            # Calculate phash
            phash_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            dct = cv2.dct(np.float32(phash_frame))
            dct_low_freq = dct[:8, :8]
            median = np.median(dct_low_freq)
            phash = (dct_low_freq > median).astype(int)
            phash_list.append(phash.flatten())

    avg_hist = np.mean(hist_list, axis=0)
    avg_phash = np.mean(phash_list, axis=0)
    binary_avg_phash = (avg_phash > 0.5).astype(int)
    return avg_hist, binary_avg_phash


def main():
    similarity_threshold = 0.99

    print("\n\nGrouping similar videos")
    with get_video_db() as db:
        all_features = db.for_similarity_table.list_similarity()
        video_data = [(row.video.video_url, np.frombuffer(row.histogramm, dtype=np.float32)) for row in all_features]

    similarity_matrix = np.array([[similar_compare(f1[1], f2[1]) for f2 in video_data] for f1 in video_data])
    from collections import defaultdict

    similar_groups = defaultdict(list)

    for i in range(len(video_data)):
        for j in range(i + 1, len(video_data)):
            similarity = similarity_matrix[i][j]
            if similarity > similarity_threshold:
                similar_groups[video_data[i][0]].append((video_data[j][0], similarity))
                similar_groups[video_data[j][0]].append((video_data[i][0], similarity))

    #for i in range(len(video_data)):
    #    for j in range(i + 1, len(video_data)):
    #        similarity = similar_compare(video_data[i][1], video_data[j][1])
    #        if similarity > similarity_threshold:
    #            similar_groups[video_data[i][0]].append((video_data[j][0], similarity))
    #            similar_groups[video_data[j][0]].append((video_data[i][0], similarity))

    for video, sim_video in similar_groups.items():
        print(f"Video: {video}")
        for similar_video, score in sim_video:
            print(f"  Score: {int(score * 100)} - Similar to: {similar_video}")

    print(f"Found {len(video_data)} videos")

if __name__ == '__main__':
    main()