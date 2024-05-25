import os
import cv2
import numpy as np
import argparse
from tqdm import tqdm
from PIL import Image
import hashlib
import signal
import gc
import shutil

# dhash implementation
def dhash(image, hash_size=8):
    resized = cv2.resize(image, (hash_size + 1, hash_size))
    diff = resized[:, 1:] > resized[:, :-1]
    return sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])

# Signal handler for safe termination
def signal_handler(sig, frame):
    print('Process interrupted! Exiting gracefully...')
    exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def parse_arguments():
    parser = argparse.ArgumentParser(description='Image Cleaner Script')
    parser.add_argument('--dir', required=True, help='Directory to process')
    parser.add_argument('--save_dir', default='output/', help='Directory to save non-duplicate images')
    parser.add_argument('--save_dir_duplicate', help='Directory to save duplicate images')
    parser.add_argument('--extension', default='jpg png webp', help='Extensions of images to process')
    parser.add_argument('--recursive', action='store_true', help='Recursively search directories')
    parser.add_argument('--debug', action='store_true', help='Debug mode')
    parser.add_argument('--threshold', type=int, default=10, help='Hamming distance threshold for duplicates')
    parser.add_argument('--preserve_own_folder', action='store_true', help='Preserve own folder structure')
    parser.add_argument('--preserve_structure', action='store_true', help='Preserve directory structure')
    parser.add_argument('--gc_disable', action='store_true', help='Disable garbage collection')
    parser.add_argument('--by_folder', action='store_true', help='Process folders one by one')
    parser.add_argument('--process_group', type=int, default=2, help='Number of images in a processing group')
    parser.add_argument('--mem_cache', action='store_true', default=True, help='Enable in-memory caching')
    return parser.parse_args()

def ensure_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)

def get_image_files(directory, extensions, recursive=False):
    image_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.split('.')[-1].lower() in extensions:
                image_files.append(os.path.join(root, file))
        if not recursive:
            break
    return image_files

def remove_duplicates(image_files, threshold, save_dir, save_dir_duplicate, debug, mem_cache, args):
    hash_dict = {}
    duplicates = []
    saved_images_count = 0  # 保存された画像の数を追跡
    cache = []  # メモリキャッシュ用

    for img_path in tqdm(image_files, desc="Processing images"):
        try:
            image = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if image is None:
                continue

            img_hash = dhash(image)

            is_duplicate = False
            for existing_hash in hash_dict.keys():
                if bin(img_hash ^ existing_hash).count('1') <= threshold:
                    duplicates.append((img_path, hash_dict[existing_hash]))
                    is_duplicate = True
                    break

            if not is_duplicate:
                hash_dict[img_hash] = img_path

        except Exception as e:
            print(f"Error processing {img_path}: {e}")

    if debug:
        print("Debug mode enabled. No files will be moved.")
        return

    ensure_directory(save_dir)
    ensure_directory(save_dir_duplicate)

    # `--preserve_structure` または `--preserve_own_folder` が有効な場合の処理
    if args.preserve_structure or args.preserve_own_folder:
        if args.preserve_own_folder:
            base_folder_name = os.path.basename(os.path.normpath(args.dir))
            save_dir = os.path.join(save_dir, base_folder_name)
            save_dir_duplicate = os.path.join(save_dir_duplicate, base_folder_name)
        ensure_directory(save_dir)
        ensure_directory(save_dir_duplicate)
    
    if mem_cache == 'ON':
        for img_hash, img_path in hash_dict.items():
            cache.append((img_path, os.path.commonpath([img_path, args.dir])))
        for duplicate, original in duplicates:
            cache.append((duplicate, save_dir_duplicate))
    else:
        for img_hash, img_path in hash_dict.items():
            process_image_save(img_path, save_dir, args)
            saved_images_count += 1  # 成功した保存ごとにカウントアップ
        for duplicate, original in duplicates:
            process_duplicate_save(duplicate, original, save_dir_duplicate, args)

    if mem_cache == 'ON':
        for img_path, base_dir in cache:
            if img_path in dict(duplicates):
                process_duplicate_save(img_path, dict(duplicates)[img_path], save_dir_duplicate, args)
            else:
                process_image_save(img_path, save_dir, args)
                saved_images_count += 1

    print(f"Saved images: {saved_images_count}")
    print(f"Removed duplicates: {len(duplicates)}")

def process_image_save(img_path, save_dir, args):
    relative_path = os.path.relpath(img_path, start=os.path.commonpath([img_path, args.dir]))
    if args.preserve_structure or args.preserve_own_folder:
        dest_path = os.path.join(save_dir, relative_path)
    else:
        dest_path = os.path.join(save_dir, os.path.basename(img_path))
    ensure_directory(os.path.dirname(dest_path))
    shutil.copyfile(img_path, dest_path)

def process_duplicate_save(duplicate, original, save_dir_duplicate, args):
    relative_path = os.path.relpath(duplicate, start=os.path.commonpath([duplicate, save_dir_duplicate]))
    if args.preserve_structure or args.preserve_own_folder:
        dest_path = os.path.join(save_dir_duplicate, relative_path)
    else:
        dest_path = os.path.join(save_dir_duplicate, os.path.basename(duplicate))
    ensure_directory(os.path.dirname(dest_path))
    shutil.copyfile(duplicate, dest_path)

def main():
    args = parse_arguments()

    if args.gc_disable:
        gc.disable()

    extensions = args.extension.split()
    image_files = get_image_files(args.dir, extensions, args.recursive)

    if args.by_folder:
        folders = [f.path for f in os.scandir(args.dir) if f.is_dir()]
        for folder in folders:
            folder_files = get_image_files(folder, extensions, args.recursive)
            remove_duplicates(folder_files, args.threshold, args.save_dir, args.save_dir_duplicate, args.debug, args.mem_cache, args)
    else:
        remove_duplicates(image_files, args.threshold, args.save_dir, args.save_dir_duplicate, args.debug, args.mem_cache, args)

    if args.gc_disable:
        gc.enable()

if __name__ == '__main__':
    main()
