import os
import numpy as np
from PIL import Image
from keras.src.saving import load_model
from tensorflow.keras.applications.vgg16 import VGG16, preprocess_input
from tensorflow.keras.preprocessing import image
from sklearn.metrics.pairwise import cosine_similarity

from database import get_similarity_db
from globals import get_static_directory, VideoFolder, THUMBNAIL_DIR_NAME, get_data_directory
from thumbnail import ThumbnailFormat

# Load pre-trained VGG16 model + higher level layers
vgg16_base_model = None
def init_video_compare_model() -> VGG16:
    global vgg16_base_model
    if vgg16_base_model is not None:
        return vgg16_base_model

    data_dir = get_data_directory()
    model_file = os.path.join(data_dir, 'vgg16_model.keras')
    if not os.access(model_file, os.F_OK):
        base_model = VGG16(weights='imagenet', include_top=False)
        base_model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
        base_model.save(model_file, include_optimizer=False)
    else:
        base_model = load_model(model_file)
        base_model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    vgg16_base_model = base_model
    return base_model


def extract_features(img_path, model):
    img = image.load_img(img_path, target_size=(224, 224))
    img_data = image.img_to_array(img)
    img_data = np.expand_dims(img_data, axis=0)
    img_data = preprocess_input(img_data)
    features = model.predict(img_data)
    return features.flatten()

def extract_frames_from_webp(webp_path):
    frames = []
    with Image.open(webp_path) as img:
        for frame in range(0, img.n_frames):
            img.seek(frame)
            frame_path = f"{webp_path}_frame_{frame}.png"
            img.save(frame_path)
            frames.append(frame_path)
    return frames

def build_similarity_features(thumbnail_file: str) -> np.ndarray:
    base_model = init_video_compare_model()
    frames = extract_frames_from_webp(thumbnail_file)
    features_list = [extract_features(frame, base_model) for frame in frames]
    return np.mean(features_list, axis=0)

def find_similar(provided_video_path, similarity_threshold=0.4) -> list:
    """
    Find similar videos to the provided video path

    :param provided_video_path: for which to find similar videos
    :param similarity_threshold: threshold for similarity default 0.4
    :return: list of similar videos with similarity score (tuple)
    """
    similars = []
    with (get_similarity_db() as db):
        features_row = db.get_features(provided_video_path)
        if features_row:
            combined_features = np.frombuffer(features_row['features'], dtype=np.float32)
        else:
            return []

        all_features = db.fetch_all('SELECT * FROM features')

        for row in all_features:
            video_path = row.get('video_path')
            features_blob = row.get('features')
            stored_features = np.frombuffer(features_blob, dtype=np.float32)
            similarity = cosine_similarity([combined_features], [stored_features])[0][0]
            if similarity > similarity_threshold:
                similars.append((video_path, int(similarity * 100)))

    # Sort similar images by similarity score in descending order
    similars.sort(key=lambda x: x[1], reverse=True)

    return similars


def fill_db_with_features(folder: VideoFolder) -> tuple:
    """
    Fill the database with features for all videos in the given folder (generator function)
    Yields a tuple with the state of the processing, the video path and the features
    state: 'start' - starting processing a video
           'existing' - video already has features in the database
           'new' - video has been processed and features added to the database

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
                thumbnail_file = os.path.join(thumbnail_dir, f"{filename}{ThumbnailFormat.WEBP.extension}")
                if os.access(thumbnail_file, os.F_OK):
                    yield 'start', video_path, None
                    with get_similarity_db() as db:
                        features_row = db.get_features(video_path)
                        if features_row:
                            combined_features = np.frombuffer(features_row['features'], dtype=np.float32)
                            yield 'exising', video_path, combined_features
                        else:
                            combined_features = build_similarity_features(thumbnail_file)
                            db.upsert_similarity(video_path=video_path, image_path=thumbnail_file, features=combined_features)
                            yield 'new', video_path, combined_features

if __name__ == '__main__':
    # Example usage
    similarity_threshold = 0.4
    provided_image_path = '/static/videos/direct/20250131231949____L0tt1e_M@gne.mp4'
    similar_images = find_similar(provided_image_path, similarity_threshold)
    print(f"Similar to [{provided_image_path}] :")
    for img_path, similarity in similar_images:
        print(f" - {img_path} (similarity: {similarity})")

    print("\n\nGrouping similar videos")
    # Example usage with all grouping
    video_paths = []
    features = []
    for state, local_video_path, local_features in fill_db_with_features(VideoFolder.library):
        if state != 'start':
            video_paths.append(local_video_path)
            features.append(local_features)

    print(f"Found {len(video_paths)} videos with length {len(features)}")
    features_array = np.array(features)
    similarity_matrix = cosine_similarity(features_array)

    grouped_videos = []
    visited = set()

    for i, video_path in enumerate(video_paths):
        if i in visited:
            continue

        group = [video_path]
        visited.add(i)

        for j in range(i + 1, len(video_paths)):
            if similarity_matrix[i][j] > similarity_threshold:
                group.append(video_paths[j])
                visited.add(j)

        grouped_videos.append(group)

    for group_id, videos in enumerate(grouped_videos):
        print(f"Group {group_id}:")
        for video in videos:
            print(f" - {video}")