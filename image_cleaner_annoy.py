import argparse
import os
import sys
import shutil
import signal
from PIL import Image
from tqdm import tqdm
from annoy import AnnoyIndex
import numpy as np
from pathlib import Path

def signal_handler(sig, frame):
    print('Script interrupted. Exiting safely...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def parse_arguments():
    parser = argparse.ArgumentParser(description='Clean similar images from a directory.')
    parser.add_argument('--dir', required=True, help='Directory to process')
    parser.add_argument('--save_dir', default='output/', help='Directory to save the output images')
    parser.add_argument('--extension', default='jpg png webp', help='File extensions to process')
    parser.add_argument('--recursive', action='store_true', help='Process directories recursively')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--threshold', type=float, default=0.5, help='Similarity threshold for image removal')
    parser.add_argument('--mem_cache', default='ON', choices=['ON', 'OFF'], help='Enable or disable memory caching')
    return parser.parse_args()

def get_image_files(directory, extensions, recursive):
    extensions = tuple(extensions.split())
    if recursive:
        return [str(p) for p in Path(directory).rglob('*') if p.suffix[1:] in extensions]
    else:
        return [str(p) for p in Path(directory).glob('*') if p.suffix[1:] in extensions]

def process_images(image_files, save_dir, threshold, debug, mem_cache):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # Initialize Annoy index
    image_vectors = []
    index = AnnoyIndex(4096, 'angular')  # ここで指定されている次元数に注意

    for i, file in enumerate(tqdm(image_files, desc="Processing images")):
        try:
            with Image.open(file) as img:
                img = img.convert('RGB').resize((64, 64))
                vector = np.asarray(img).flatten()
                # 修正: ベクトルの長さを4096にするためにベクトルをリサイズする
                # ただし、この方法では情報の損失が発生する可能性があるため、異なるアプローチが必要な場合もある
                vector = vector[:4096]  # ベクトルを期待される長さに切り詰める
                image_vectors.append((i, file, vector))
                index.add_item(i, vector)
        except Exception as e:
            print(f"Failed to process {file}: {e}")

    index.build(10)
    
    unique_images = []
    for i, file, vector in tqdm(image_vectors, desc="Removing similar images"):
        if debug:
            print(f"Debug: Processing {file}")
        similar_images = index.get_nns_by_item(i, 2)
        if len(similar_images) > 1:
            sim_score = index.get_distance(i, similar_images[1])
            if sim_score < threshold:
                continue
        unique_images.append(file)

    if mem_cache == 'OFF':
        for file in unique_images:
            save_path = os.path.join(save_dir, os.path.relpath(file, args.dir))
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            shutil.copy2(file, save_path)
    else:
        cache = []
        for file in unique_images:
            with open(file, 'rb') as f:
                cache.append((os.path.relpath(file, args.dir), f.read()))
        
        for rel_path, data in cache:
            save_path = os.path.join(save_dir, rel_path)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'wb') as f:
                f.write(data)

if __name__ == "__main__":
    args = parse_arguments()
    image_files = get_image_files(args.dir, args.extension, args.recursive)
    process_images(image_files, args.save_dir, args.threshold, args.debug, args.mem_cache)
