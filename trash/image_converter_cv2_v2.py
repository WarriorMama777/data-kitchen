import os
import cv2
import argparse
import numpy as np
from tqdm import tqdm
from pathlib import Path
import shutil
import signal
import sys
import gc

# Signal handler for graceful termination
def signal_handler(sig, frame):
    print('Process interrupted. Exiting gracefully...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def parse_args():
    parser = argparse.ArgumentParser(description="Image conversion and compression script.")
    parser.add_argument('--dir', required=True, help="Directory to process images from.")
    parser.add_argument('--save_dir', default="output/", help="Directory to save processed images.")
    parser.add_argument('--extension', nargs='+', default=['jpg', 'png', 'webp'], help="Extensions of files to process.")
    parser.add_argument('--background', default=None, help="Background color code for transparent images (e.g., ffffff).")
    parser.add_argument('--resize', type=int, default=None, help="Resize the images to have the longest side equal to this value.")
    parser.add_argument('--format', default=None, help="Convert images to this format (e.g., webp).")
    parser.add_argument('--quality', type=int, default=95, help="Quality of the saved images.")
    parser.add_argument('--recursive', action='store_true', help="Recursively process directories.")
    parser.add_argument('--debug', action='store_true', help="Run in debug mode without saving images.")
    parser.add_argument('--preserve_own_folder', action='store_true', help="Preserve the own folder name in save directory.")
    parser.add_argument('--preserve_structure', action='store_true', help="Preserve the directory structure in save directory.")
    parser.add_argument('--gc_disable', action='store_true', help="Disable garbage collection.")
    parser.add_argument('--by_folder', action='store_true', help="Process folders one by one.")
    parser.add_argument('--mem_cache', default='ON', help="Cache images in memory before saving.")
    return parser.parse_args()

def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)

def get_image_files(directory, extensions, recursive):
    if recursive:
        return [str(p) for ext in extensions for p in Path(directory).rglob(f'*.{ext}')]
    else:
        return [str(p) for ext in extensions for p in Path(directory).glob(f'*.{ext}')]

def process_image(file_path, args):
    try:
        image = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
        
        if image is None:
            raise ValueError(f"Image not loaded properly: {file_path}")

        # Handle transparent background
        if args.background and image.shape[2] == 4:
            background = np.full(image.shape, int(args.background, 16))
            alpha = image[:, :, 3] / 255.0
            image = alpha[..., None] * image[:, :, :3] + (1 - alpha[..., None]) * background[:, :, :3]

        # Resize image
        if args.resize:
            height, width = image.shape[:2]
            if width > height:
                new_width = args.resize
                new_height = int(height * (args.resize / width))
            else:
                new_height = args.resize
                new_width = int(width * (args.resize / height))
            image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)

        return image

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None

def save_image(image, save_path, args):
    try:
        if args.format:
            save_path = f"{os.path.splitext(save_path)[0]}.{args.format}"
        
        params = []
        if args.format == 'jpg' or args.format == 'jpeg':
            params = [cv2.IMWRITE_JPEG_QUALITY, args.quality]
        elif args.format == 'webp':
            params = [cv2.IMWRITE_WEBP_QUALITY, args.quality]

        create_directory(os.path.dirname(save_path))
        cv2.imwrite(save_path, image, params)
        
    except Exception as e:
        print(f"Error saving {save_path}: {e}")

def main():
    args = parse_args()

    if args.gc_disable:
        gc.disable()

    image_files = get_image_files(args.dir, args.extension, args.recursive)
    
    if args.debug:
        print(f"Found {len(image_files)} images to process.")
        for img_file in image_files:
            print(f"Would process: {img_file}")
        return

    if args.preserve_own_folder:
        save_dir = os.path.join(args.save_dir, os.path.basename(os.path.normpath(args.dir)))
    else:
        save_dir = args.save_dir

    if args.by_folder:
        folders = sorted(set(Path(f).parent for f in image_files))
        for folder in folders:
            folder_files = [f for f in image_files if f.startswith(str(folder))]
            with tqdm(total=len(folder_files), desc=f"Processing {folder}") as pbar:
                for img_file in folder_files:
                    image = process_image(img_file, args)
                    if image is not None:
                        save_path = os.path.join(save_dir, os.path.relpath(img_file, args.dir)) if args.preserve_structure else os.path.join(save_dir, os.path.basename(img_file))
                        save_image(image, save_path, args)
                    pbar.update(1)
    else:
        with tqdm(total=len(image_files), desc="Processing images") as pbar:
            for img_file in image_files:
                image = process_image(img_file, args)
                if image is not None:
                    save_path = os.path.join(save_dir, os.path.relpath(img_file, args.dir)) if args.preserve_structure else os.path.join(save_dir, os.path.basename(img_file))
                    save_image(image, save_path, args)
                pbar.update(1)

    if args.gc_disable:
        gc.enable()

if __name__ == "__main__":
    main()
