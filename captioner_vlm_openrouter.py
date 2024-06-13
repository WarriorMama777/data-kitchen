import os
import argparse
import requests
from pathlib import Path
from tqdm import tqdm
import signal
import sys
from PIL import Image

# OpenRouter APIの設定
API_URL = "https://api.openrouter.ai/v1/requests"
API_KEY = "your_openrouter_api_key_here"

# SIGINT (Ctrl+C) ハンドリング
def signal_handler(sig, frame):
    print("\nProcess interrupted. Exiting gracefully...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# 画像キャプション生成関数
def generate_caption(image_path):
    with open(image_path, 'rb') as img_file:
        files = {'file': img_file}
        headers = {
            'Authorization': f'Bearer {API_KEY}',
            'User-Agent': 'Mozilla/5.0'
        }
        data = {
            'model': 'liuhaotian/llava-13b',
            'task': 'captioning'
        }
        
        try:
            response = requests.post(API_URL, headers=headers, files=files, data=data)
            response.raise_for_status()
            result = response.json()
            return result['caption']
        except requests.exceptions.RequestException as e:
            print(f"Error occurred: {e}")
            return None

# メイン処理関数
def main(args):
    image_extensions = args.extension.split()
    if not args.save_dir:
        args.save_dir = "output/"
    save_path = Path(args.save_dir)
    save_path.mkdir(parents=True, exist_ok=True)
    
    if os.path.isfile(args.dir):
        image_paths = [args.dir]
    else:
        if args.recursive:
            image_paths = list(Path(args.dir).rglob('*'))
        else:
            image_paths = list(Path(args.dir).glob('*'))

    image_paths = [p for p in image_paths if p.suffix.lower().strip('.') in image_extensions]

    if args.debug:
        print("Debug mode enabled. The following files will be processed:")
        for image_path in image_paths:
            print(image_path)
        sys.exit(0)

    for image_path in tqdm(image_paths, desc="Processing images"):
        try:
            caption = None
            retries = 3
            while retries > 0 and not caption:
                caption = generate_caption(image_path)
                retries -= 1
            if caption:
                save_file = save_path / (image_path.stem + ".txt")
                with open(save_file, 'w', encoding='utf-8') as f:
                    f.write(caption)
            else:
                print(f"Failed to generate caption for {image_path}")
        except Exception as e:
            print(f"Error processing {image_path}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate captions for images using liuhaotian/llava-13b model via OpenRouter API.")
    parser.add_argument('--dir', required=True, help='Directory or single file to process.')
    parser.add_argument('--save_dir', default="output/", help='Directory to save the generated captions.')
    parser.add_argument('--extension', default="jpg png webp", help='File extensions to process (default: jpg png webp).')
    parser.add_argument('--recursive', action='store_true', help='Recursively process subdirectories.')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode.')

    args = parser.parse_args()
    main(args)
