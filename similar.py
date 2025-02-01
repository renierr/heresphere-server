import os
from xml.sax.handler import all_features

import numpy as np
from PIL import Image
import sqlite3
from keras.src.saving import load_model
from tensorflow.keras.applications.vgg16 import VGG16, preprocess_input
from tensorflow.keras.preprocessing import image
from sklearn.metrics.pairwise import cosine_similarity

from database import get_similarity_db
from globals import get_static_directory, VideoFolder, THUMBNAIL_DIR_NAME, get_data_directory

# Load pre-trained VGG16 model + higher level layers
data_dir = get_data_directory()
model_file = os.path.join(data_dir, 'vgg16_model.keras')
if not os.access(model_file, os.F_OK):
    base_model = VGG16(weights='imagenet', include_top=False)
    base_model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    print("Saving pre-trained model")
    base_model.save(model_file, include_optimizer=False)
else:
    print("Loading pre-trained model")
    base_model = load_model(model_file)
    base_model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

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

def combine_features(features_list):
    return np.mean(features_list, axis=0)

static_dir = get_static_directory()
video_dir = os.path.join(static_dir, VideoFolder.videos.dir)

# Extract features for all images
features = []
image_paths = []

for root, dirs, files in os.walk(video_dir, followlinks=True):
    # Exclude directories that start with a dot
    dirs[:] = [d for d in dirs if not d.startswith('.')]

    for filename in files:
        if filename.endswith(('.mp4', '.mkv', '.avi', '.webm')):
            relative_path = os.path.relpath(root, get_static_directory()).replace('\\', '/')
            video_path = f"/static/{relative_path}/{filename}"
            print(f"Processing video: {video_path}")
            thumbnail_dir = os.path.join(root, THUMBNAIL_DIR_NAME)

            thumbnail_file = os.path.join(thumbnail_dir, f"{filename}.thumb.webp")
            if os.access(thumbnail_file, os.F_OK):
                image_paths.append(thumbnail_file)
                # Check if features already exist in the database
                with get_similarity_db() as db:
                    features_row = db.get_features(video_path)
                    if features_row:
                        combined_features = np.frombuffer(features_row['features'], dtype=np.float32)
                    else:
                        frames = extract_frames_from_webp(thumbnail_file)
                        features_list = [extract_features(frame, base_model) for frame in frames]
                        combined_features = combine_features(features_list)
                        db.upsert_similarity(video_path=video_path, image_path=thumbnail_file, features=combined_features)
                features.append(combined_features)

print(f"Extracted features for {len(features)} images")


def get_similar_images(provided_video_path, similarity_threshold=0.4):

    similar_images = []
    with (get_similarity_db() as db):
        features_row = db.get_features(provided_video_path)
        if features_row:
            combined_features = np.frombuffer(features_row['features'], dtype=np.float32)
        else:
            raise ValueError(f"Features for the provided image {provided_video_path} not found in the database")

        all_features = db.fetch_all('SELECT * FROM features')

        for row in all_features:
            video_path = row.get('video_path')
            features_blob = row.get('features')
            stored_features = np.frombuffer(features_blob, dtype=np.float32)

            # Compute cosine similarity
            similarity = cosine_similarity([combined_features], [stored_features])[0][0]

            if similarity > similarity_threshold:
                similar_images.append((video_path, similarity))


    # Sort similar images by similarity score in descending order
    similar_images.sort(key=lambda x: x[1], reverse=True)

    return similar_images

# Example usage
provided_image_path = '/static/videos/direct/test.mp4'
similar_images = get_similar_images(provided_image_path, similarity_threshold=0.3)
print(f"Similar to [{provided_image_path}] :")
for img_path, similarity in similar_images:
    print(f" - {img_path} (similarity: {similarity})")