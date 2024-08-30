import os
import shutil
import argparse
import concurrent.futures
import re
from tqdm import tqdm
from PIL import Image
import pytesseract
import signal
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Signal handler for safe exit
def signal_handler(sig, frame):
    print('Script interrupted!')
    exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Function to create directories if they don't exist
def create_directories(dir_path):
    Path(dir_path).mkdir(parents=True, exist_ok=True)

# Function to find files with specific extension
def find_files_with_extension(directory, extensions, recursive):
    extensions = tuple(extensions)
    if recursive:
        return [f for f in Path(directory).rglob('*') if f.suffix[1:] in extensions]
    else:
        return [f for f in Path(directory).glob('*') if f.suffix[1:] in extensions]

# Function to check if image contains text based on threshold
def image_contains_text(image_path, threshold):
    try:
        text = pytesseract.image_to_string(Image.open(image_path))
        return len(text.strip()) >= threshold
    except Exception as e:
        logging.error(f"Error processing image {image_path}: {e}")
        return False

# Function to copy or cut files preserving structure
def copy_or_cut(src, dst, action):
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if action == 'copy':
            shutil.copy2(src, dst)
        elif action == 'cut':
            shutil.move(src, dst)
    except Exception as e:
        logging.error(f"Error {action} file {src} to {dst}: {e}")

# Main function to handle Images_with_text_only functionality
def images_with_text_only(dir_image, dir_tag, dir_save, action, debug, threshold, preserve_own_folder, preserve_structure):
    if preserve_own_folder:
        dir_save = Path(dir_save) / Path(dir_image).name
    create_directories(dir_save)

    image_save_dir = Path(dir_save) / 'image'
    tag_save_dir = Path(dir_save) / 'tag'
    create_directories(image_save_dir)
    create_directories(tag_save_dir)

    image_files = find_files_with_extension(dir_image, ['jpg', 'jpeg', 'png', 'webp'], True)
    matched_files = []

    for image_file in tqdm(image_files, desc="Checking images for text"):
        if image_contains_text(image_file, threshold):
            matched_files.append(image_file)
            if debug:
                logging.debug(f"Image with text: {image_file}")

    for image_file in tqdm(matched_files, desc="Copying images and tags"):
        if preserve_structure:
            relative_path = image_file.relative_to(dir_image)
            image_dst = image_save_dir / relative_path
            copy_or_cut(image_file, image_dst, action)
            
            if dir_tag:
                tag_file = Path(dir_tag) / relative_path.with_suffix('.txt')
                if tag_file.exists():
                    tag_dst = tag_save_dir / relative_path.with_suffix('.txt')
                    copy_or_cut(tag_file, tag_dst, action)
        else:
            copy_or_cut(image_file, image_save_dir / image_file.name, action)
            
            if dir_tag:
                tag_file = Path(dir_tag) / image_file.with_suffix('.txt').name
                if tag_file.exists():
                    copy_or_cut(tag_file, tag_save_dir / tag_file.name, action)

def main():
    parser = argparse.ArgumentParser(description="Image Extractor Tool")
    parser.add_argument('--search_tag', type=str, help='Search word for tags')
    parser.add_argument('--dir_image', type=str, required=True, help='Directory for image files')
    parser.add_argument('--dir_tag', type=str, help='Directory for tag text files')
    parser.add_argument('--dir_save', type=str, default="./output", help='Directory to save output files')
    parser.add_argument('--extension', type=str, nargs='+', default=['txt'], help='Extensions for tag files')
    parser.add_argument('--recursive', action='store_true', default=True, help='Recursively search directories')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--cut', action='store_true', help='Cut files instead of copy')
    parser.add_argument('--copy', action='store_true', help='Copy files instead of cut')
    parser.add_argument('--Images_with_text_only', action='store_true', help='Extract images with text only')
    parser.add_argument('--threads', type=int, default=os.cpu_count(), help='Number of threads to use')
    parser.add_argument('--threshold', type=int, default=1, help='Text detection threshold')
    parser.add_argument('--preserve_own_folder', action='store_true', help='Preserve the own folder name in the save directory')
    parser.add_argument('--preserve_structure', action='store_true', help='Preserve the directory structure')
    parser.add_argument('--tesseract_path', type=str, help='Path to Tesseract executable')

    args = parser.parse_args()

    if args.tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = args.tesseract_path

    action = 'copy' if args.copy else 'cut' if args.cut else None
    if not action:
        parser.error('Either --cut or --copy must be specified.')

    if args.Images_with_text_only:
        images_with_text_only(args.dir_image, args.dir_tag, args.dir_save, action, args.debug, args.threshold, args.preserve_own_folder, args.preserve_structure)
    elif args.search_tag:
        search_tag(args.search_tag, args.dir_image, args.dir_tag, args.dir_save, args.extension, args.recursive, action, args.debug, args.preserve_own_folder, args.preserve_structure)
    else:
        parser.error('Either --search_tag or --Images_with_text_only must be specified.')

if __name__ == "__main__":
    main()