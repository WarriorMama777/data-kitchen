import os
import sys
import signal
import shutil
from PIL import Image
import imagehash
from tqdm import tqdm
from annoy import AnnoyIndex
import numpy as np
from pathlib import Path
import argparse
import random
import gc  # ガベージコレクションを制御するためにインポート

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
    parser.add_argument('--preserve_own_folder', action='store_true', help='Preserve the directory itself in the save location')
    parser.add_argument('--preserve_structure', action='store_true', help='Preserve the directory structure when saving files')
    parser.add_argument('--processes', type=int, default=1, help='Number of processes to use')
    parser.add_argument('--multi_threading', action='store_true', help='Enable multi-threading processing')
    parser.add_argument('--gc-disable', action='store_true', help='Disable garbage collection')
    parser.add_argument('--by_folder', action='store_true', help='Process each folder in the directory individually')
    return parser.parse_args()

def get_image_files(directory, extensions, recursive, by_folder):
    all_files = []
    extensions = tuple(extensions.split())
    if by_folder:
        subfolders = [f.path for f in os.scandir(directory) if f.is_dir()]
        for folder in subfolders:
            if recursive:
                all_files.extend([str(p) for p in Path(folder).rglob('*') if p.suffix[1:] in extensions])
            else:
                all_files.extend([str(p) for p in Path(folder).glob('*') if p.suffix[1:] in extensions])
    else:
        if recursive:
            all_files = [str(p) for p in Path(directory).rglob('*') if p.suffix[1:] in extensions]
        else:
            all_files = [str(p) for p in Path(directory).glob('*') if p.suffix[1:] in extensions]
    return all_files

def hash_image(image_path):
    try:
        with Image.open(image_path) as img:
            return imagehash.phash(img)
    except Exception as e:
        print(f"Failed to process {image_path}: {e}")
        return None

def process_images(image_files, save_dir, threshold, debug, preserve_own_folder, preserve_structure, gc_disable):
    if gc_disable:
        gc.disable()

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

    unique_images = set(range(len(file_hashes))) - set(duplicates.keys())
    for index in list(unique_images) + list(set(duplicates.values())):
        _, file, _ = file_hashes[index]
        if preserve_structure:
            save_path = os.path.join(save_dir, os.path.relpath(file, Path(args.dir).parent if preserve_own_folder else args.dir))
        else:
            if preserve_own_folder:
                base_dir_name = os.path.basename(os.path.normpath(args.dir))
                save_path = os.path.join(save_dir, base_dir_name, os.path.basename(file))
            else:
                save_path = os.path.join(save_dir, os.path.basename(file))

        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        shutil.copy2(file, save_path)

    # 処理結果の表示
    original_count = len(image_files)
    processed_count = len(unique_images) + len(set(duplicates.values()))
    reduced_count = original_count - processed_count
    print(f"{reduced_count}枚削減されました。")

def image_hash_to_binary_array(image_hash):
    binary_string = bin(int(str(image_hash), 16))[2:].zfill(64)
    binary_array = np.array(list(binary_string), dtype=int)
    return binary_array

if __name__ == "__main__":
    args = parse_arguments()
    image_files = get_image_files(args.dir, args.extension, args.recursive, args.by_folder)
    process_images(image_files, args.save_dir, args.threshold, args.debug, args.preserve_own_folder, args.preserve_structure, args.gc_disable)

