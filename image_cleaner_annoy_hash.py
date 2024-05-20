import os
import sys
import signal
import shutil  # shutilをインポート
from PIL import Image
import imagehash
from tqdm import tqdm
from annoy import AnnoyIndex
import numpy as np
from pathlib import Path
import argparse
import random  # randomをインポート

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
    parser.add_argument('--threshold', type=int, default=5, help='Hamming distance threshold for image removal')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    return parser.parse_args()

def get_image_files(directory, extensions, recursive):
    extensions = tuple(extensions.split())
    if recursive:
        return [str(p) for p in Path(directory).rglob('*') if p.suffix[1:] in extensions]
    else:
        return [str(p) for p in Path(directory).glob('*') if p.suffix[1:] in extensions]

def hash_image(image_path):
    try:
        with Image.open(image_path) as img:
            return imagehash.phash(img)
    except Exception as e:
        print(f"Failed to process {image_path}: {e}")
        return None

def process_images(image_files, save_dir, threshold, debug):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    hash_size = 64
    index = AnnoyIndex(hash_size, 'hamming')
    file_hashes = []

    for i, file in enumerate(tqdm(image_files, desc="Processing images")):
        image_hash = hash_image(file)
        if image_hash is not None:
            binary_hash_array = image_hash_to_binary_array(image_hash)
            file_hashes.append((i, file, image_hash))
            index.add_item(i, binary_hash_array)

    index.build(10)

    # 重複画像群を追跡するための辞書
    duplicates = {}

    for i, file, image_hash in tqdm(file_hashes, desc="Identifying duplicates"):
        if debug:
            print(f"Debug: Processing {file}")
        similar_images = index.get_nns_by_item(i, 2, search_k=-1, include_distances=True)
        for sim_i, distance in zip(*similar_images):
            if i != sim_i and distance < threshold:
                if i in duplicates or sim_i in duplicates:
                    continue
                duplicates[i] = sim_i

    # 重複していない画像と重複群から選ばれた一枚を保存する
    unique_images = set(range(len(file_hashes))) - set(duplicates.keys())
    for index in list(unique_images) + list(set(duplicates.values())):
        _, file, _ = file_hashes[index]
        save_path = os.path.join(save_dir, os.path.relpath(file, args.dir))
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        shutil.copy2(file, save_path)

def image_hash_to_binary_array(image_hash):
    binary_string = bin(int(str(image_hash), 16))[2:].zfill(64)
    binary_array = np.array(list(binary_string), dtype=int)
    return binary_array

if __name__ == "__main__":
    args = parse_arguments()
    image_files = get_image_files(args.dir, args.extension, args.recursive)
    process_images(image_files, args.save_dir, args.threshold, args.debug)
