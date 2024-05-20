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
    
    # Initialize Annoy index
    hash_size = 64  # pHash bit size, assuming 8x8 hash resulting in 64 bits.
    index = AnnoyIndex(hash_size, 'hamming')
    file_hashes = []

    for i, file in enumerate(tqdm(image_files, desc="Processing images")):
        image_hash = hash_image(file)
        if image_hash is not None:
            # Convert image hash to a binary array of length 64
            binary_hash_array = image_hash_to_binary_array(image_hash)
            file_hashes.append((i, file, image_hash))
            index.add_item(i, binary_hash_array)

    index.build(10)

    unique_images = []
    for i, file, image_hash in tqdm(file_hashes, desc="Removing similar images"):
        if debug:
            print(f"Debug: Processing {file}")
        similar_images = index.get_nns_by_item(i, 2)
        if len(similar_images) > 1:
            hamming_distance = index.get_distance(i, similar_images[1])
            if hamming_distance < threshold:
                continue
        unique_images.append(file)
    
    for file in unique_images:
        save_path = os.path.join(save_dir, os.path.relpath(file, args.dir))
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        shutil.copy2(file, save_path)

def image_hash_to_binary_array(image_hash):
    # Convert the hash (hex) into a binary array of length 64
    binary_string = bin(int(str(image_hash), 16))[2:].zfill(64)
    binary_array = np.array(list(binary_string), dtype=int)
    return binary_array

if __name__ == "__main__":
    args = parse_arguments()
    image_files = get_image_files(args.dir, args.extension, args.recursive)
    process_images(image_files, args.save_dir, args.threshold, args.debug)
