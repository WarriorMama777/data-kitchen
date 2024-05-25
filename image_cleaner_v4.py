import argparse
import os
import cv2
import numpy as np
from tqdm import tqdm
import shutil
from collections import defaultdict

def dhash(image, hash_size=8):
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Resize, adding one column for gradients
    resized = cv2.resize(gray, (hash_size + 1, hash_size))
    # Compute gradients
    diff = resized[:, 1:] > resized[:, :-1]
    # Convert to hash
    return sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])

def hamming_distance(hash1, hash2):
    return bin(hash1 ^ hash2).count("1")

def find_duplicates(images, threshold):
    hashes = {}
    duplicates = defaultdict(list)
    for img_path in tqdm(images, desc="Analyzing"):
        image = cv2.imread(img_path)
        img_hash = dhash(image)
        for h, paths in hashes.items():
            if hamming_distance(img_hash, h) <= threshold:
                duplicates[paths[0]].append(img_path)
                break
        else:
            hashes[img_hash] = [img_path]
    return duplicates

def process_images(args):
    if args.gc_disable:
        import gc
        gc.disable()

    img_extensions = tuple(args.extension.split())
    if args.recursive:
        images = [os.path.join(dp, f) for dp, dn, filenames in os.walk(args.dir) for f in filenames if f.endswith(img_extensions)]
    else:
        images = [os.path.join(args.dir, f) for f in os.listdir(args.dir) if f.endswith(img_extensions)]

    duplicates = find_duplicates(images, args.threshold)

    if not args.debug:
        for original, dupes in tqdm(duplicates.items(), desc="Processing"):
            if not args.mem_cache == 'OFF':
                # Save original
                save_path = os.path.join(args.save_dir, os.path.relpath(original, args.dir))
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                shutil.copy2(original, save_path)
                # Save duplicates if specified
                if args.save_dir_duplicate:
                    for dupe in dupes:
                        dupe_save_path = os.path.join(args.save_dir_duplicate, os.path.relpath(dupe, args.dir))
                        os.makedirs(os.path.dirname(dupe_save_path), exist_ok=True)
                        shutil.copy2(dupe, dupe_save_path)
            else:
                print(f"Would process {original} and its {len(dupes)} duplicates.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reduce dataset size by removing duplicate images.")
    parser.add_argument("--dir", required=True, help="Directory containing images.")
    parser.add_argument("--save_dir", default="output/", help="Directory to save unique images.")
    parser.add_argument("--extension", default="jpg png webp", help="File extensions to process.")
    parser.add_argument("--recursive", action="store_true", help="Search directories recursively.")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode without processing images.")
    parser.add_argument("--threshold", type=int, default=5, help="Threshold for image similarity.")
    parser.add_argument("--preserve_own_folder", action="store_true", help="Preserve original folder name in save directory.")
    parser.add_argument("--preserve_structure", action="store_true", help="Preserve directory structure in save directory.")
    parser.add_argument("--gc_disable", action="store_true", help="Disable garbage collection.")
    parser.add_argument("--by_folder", action="store_true", help="Process each folder separately.")
    parser.add_argument("--batch_size", type=int, default=10, help="Batch size for processing images.")
    parser.add_argument("--save_dir_duplicate", help="Directory to save duplicate images.")
    parser.add_argument("--mem_cache", default="ON", help="Use memory cache before saving to disk.")
    args = parser.parse_args()

    if not os.path.exists(args.save_dir):
        os.makedirs(args.save_dir)
    if args.save_dir_duplicate and not os.path.exists(args.save_dir_duplicate):
        os.makedirs(args.save_dir_duplicate)

    process_images(args)
