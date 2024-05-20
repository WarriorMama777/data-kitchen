import os
import sys
import argparse
import signal
import shutil
import numpy as np
from tqdm import tqdm
from milvus import Milvus, DataType
from PIL import Image
from io import BytesIO
from sklearn.preprocessing import normalize
import hashlib

# MILVUSの初期化
milvus_client = Milvus()

def signal_handler(sig, frame):
    print('Interrupt signal received. Exiting gracefully...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def connect_milvus():
    try:
        milvus_client.connect(host='localhost', port='19530')
    except Exception as e:
        print(f"Failed to connect to Milvus: {e}")
        sys.exit(1)

def create_collection(collection_name):
    param = {
        "collection_name": collection_name,
        "fields": [
            {"name": "embedding", "type": DataType.FLOAT_VECTOR, "params": {"dim": 128}},
            {"name": "hash", "type": DataType.INT64}
        ]
    }
    if not milvus_client.has_collection(collection_name):
        milvus_client.create_collection(param)

def extract_features(image_path):
    image = Image.open(image_path)
    image = image.resize((128, 128))
    image = np.array(image).flatten()
    image = normalize([image])[0]
    return image

def image_hash(image_path):
    with open(image_path, 'rb') as f:
        img_bytes = f.read()
    return int(hashlib.md5(img_bytes).hexdigest(), 16)

def process_images(args):
    connect_milvus()
    create_collection(args.collection_name)
    
    image_paths = []
    for root, _, files in os.walk(args.dir):
        for file in files:
            if file.split('.')[-1] in args.extension:
                image_paths.append(os.path.join(root, file))
        if not args.recursive:
            break

    if args.debug:
        print(f"Found {len(image_paths)} images to process.")
        return

    unique_images = []
    cache = []
    for image_path in tqdm(image_paths, desc="Processing images"):
        try:
            features = extract_features(image_path)
            hash_value = image_hash(image_path)
            
            search_param = {
                "metric_type": "L2",
                "params": {"nprobe": 10}
            }
            search_results = milvus_client.search(
                collection_name=args.collection_name,
                query_records=[features],
                top_k=1,
                params=search_param
            )
            if search_results[0].distance > args.threshold:
                unique_images.append(image_path)
                cache.append({"features": features, "hash": hash_value})
            else:
                print(f"Duplicate found: {image_path}")
        except Exception as e:
            print(f"Error processing image {image_path}: {e}")
            continue

    if args.mem_cache == 'ON':
        for item in cache:
            milvus_client.insert(args.collection_name, [item["features"], item["hash"]])
        milvus_client.flush([args.collection_name])

    if not os.path.exists(args.save_dir):
        os.makedirs(args.save_dir)

    for image_path in unique_images:
        rel_path = os.path.relpath(image_path, args.dir)
        save_path = os.path.join(args.save_dir, rel_path)
        if not os.path.exists(os.path.dirname(save_path)):
            os.makedirs(os.path.dirname(save_path))
        shutil.copy2(image_path, save_path)

def main():
    parser = argparse.ArgumentParser(description="Image Cleaner with MILVUS")
    parser.add_argument('--dir', required=True, help='Directory to process')
    parser.add_argument('--save_dir', default="output/", help='Directory to save unique images')
    parser.add_argument('--extension', nargs='+', default=["jpg", "png", "webp"], help='Image file extensions to process')
    parser.add_argument('--recursive', action='store_true', help='Recursively process directories')
    parser.add_argument('--debug', action='store_true', help='Debug mode')
    parser.add_argument('--threshold', type=float, default=0.1, help='Similarity threshold')
    parser.add_argument('--mem_cache', choices=['ON', 'OFF'], default='ON', help='Memory cache enabled')
    parser.add_argument('--collection_name', default='image_collection', help='Milvus collection name')

    args = parser.parse_args()
    process_images(args)

if __name__ == "__main__":
    main()
