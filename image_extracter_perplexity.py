import os
import shutil
import argparse
import concurrent.futures
import cv2
import pytesseract
from PIL import Image
from tqdm import tqdm
import signal
import sys
import multiprocessing

# Signal handler for graceful shutdown
def signal_handler(sig, frame):
    print('Graceful shutdown initiated. Exiting...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def parse_arguments():
    parser = argparse.ArgumentParser(description='Image Extractor Script')
    parser.add_argument('--search_tag', type=str, help='Search word for tag files')
    parser.add_argument('--dir_image', type=str, required=True, help='Directory containing image files')
    parser.add_argument('--dir_tag', type=str, required=True, help='Directory containing tag text files')
    parser.add_argument('--dir_save', type=str, default='./output', help='Directory to save the extracted files')
    parser.add_argument('--extension', type=str, default='txt', help='File extension for tag files')
    parser.add_argument('--recursive', action='store_true', help='Recursively search directories')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--cut', action='store_true', help='Cut files instead of copying')
    parser.add_argument('--copy', action='store_true', help='Copy files')
    parser.add_argument('--threshold', type=int, default=100, help='Threshold for text detection')
    parser.add_argument('--preserve_own_folder', action='store_true', help='Preserve own folder structure')
    parser.add_argument('--preserve_structure', action='store_true', help='Preserve directory structure')
    parser.add_argument('--Images_with_text_only', action='store_true', help='Extract images with text only')
    parser.add_argument('--threads', type=int, default=multiprocessing.cpu_count(), help='Number of threads to use')
    return parser.parse_args()

def ensure_directory_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)

def search_and_extract(search_word, dir_image, dir_tag, dir_save, extension, recursive, debug, cut, copy, preserve_own_folder, preserve_structure):
    # Ensure the output directories exist
    image_save_dir = os.path.join(dir_save, 'image')
    tag_save_dir = os.path.join(dir_save, 'tag')
    ensure_directory_exists(image_save_dir)
    ensure_directory_exists(tag_save_dir)

    # Walk through directories
    for root, _, files in os.walk(dir_tag):
        for file in files:
            if file.endswith(extension):
                tag_file_path = os.path.join(root, file)
                with open(tag_file_path, 'r', encoding='utf-8') as tag_file:
                    content = tag_file.read()
                    if search_word in content:
                        base_name = os.path.splitext(file)[0]
                        image_file_path = os.path.join(dir_image, base_name + '.jpg')
                        if os.path.exists(image_file_path):
                            if debug:
                                print(f"Found match: {tag_file_path} and {image_file_path}")
                            else:
                                # Determine the destination paths
                                if preserve_structure:
                                    relative_path = os.path.relpath(root, dir_tag)
                                    dest_image_dir = os.path.join(image_save_dir, relative_path)
                                    dest_tag_dir = os.path.join(tag_save_dir, relative_path)
                                    ensure_directory_exists(dest_image_dir)
                                    ensure_directory_exists(dest_tag_dir)
                                else:
                                    dest_image_dir = image_save_dir
                                    dest_tag_dir = tag_save_dir

                                dest_image_path = os.path.join(dest_image_dir, os.path.basename(image_file_path))
                                dest_tag_path = os.path.join(dest_tag_dir, os.path.basename(tag_file_path))

                                # Copy or move files
                                if copy:
                                    shutil.copy2(image_file_path, dest_image_path)
                                    shutil.copy2(tag_file_path, dest_tag_path)
                                elif cut:
                                    shutil.move(image_file_path, dest_image_path)
                                    shutil.move(tag_file_path, dest_tag_path)

def detect_text_in_image(image_path, threshold):
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray)
    return len(text) > threshold

def extract_images_with_text(dir_image, dir_save, threshold, debug):
    image_save_dir = os.path.join(dir_save, 'image_with_text')
    ensure_directory_exists(image_save_dir)

    for root, _, files in os.walk(dir_image):
        for file in files:
            if file.endswith('.jpg'):
                image_file_path = os.path.join(root, file)
                if detect_text_in_image(image_file_path, threshold):
                    if debug:
                        print(f"Text detected in: {image_file_path}")
                    else:
                        dest_image_path = os.path.join(image_save_dir, os.path.basename(image_file_path))
                        shutil.copy2(image_file_path, dest_image_path)

def main():
    args = parse_arguments()

    if not args.cut and not args.copy:
        print("Error: Either --cut or --copy must be specified.")
        sys.exit(1)

    if args.Images_with_text_only:
        extract_images_with_text(args.dir_image, args.dir_save, args.threshold, args.debug)
    elif args.search_tag:
        search_and_extract(args.search_tag, args.dir_image, args.dir_tag, args.dir_save, args.extension, args.recursive, args.debug, args.cut, args.copy, args.preserve_own_folder, args.preserve_structure)
    else:
        print("Error: Either --search_tag or --Images_with_text_only must be specified.")
        sys.exit(1)

if __name__ == "__main__":
    main()
