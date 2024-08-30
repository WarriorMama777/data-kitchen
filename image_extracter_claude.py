import argparse
import os
import shutil
import signal
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
from tqdm import tqdm

def setup_argument_parser():
    parser = argparse.ArgumentParser(description='Image Extractor Script')
    parser.add_argument('--search_tag', help='Search word for tag matching')
    parser.add_argument('--dir_image', required=True, help='Directory containing image files')
    parser.add_argument('--dir_tag', help='Directory containing tag text files')
    parser.add_argument('--dir_save', default='.\\output', help='Output directory (default: .\\output)')
    parser.add_argument('--extension', nargs='+', default=['txt'], help='File extensions to search (default: txt)')
    parser.add_argument('--recursive', action='store_true', help='Search subdirectories recursively')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--cut', action='store_true', help='Cut files instead of copying')
    parser.add_argument('--copy', action='store_true', help='Copy files (default)')
    parser.add_argument('--preserve_own_folder', action='store_true', help='Preserve own folder structure')
    parser.add_argument('--preserve_structure', action='store_true', help='Preserve directory structure')
    parser.add_argument('--Images_with_text_only', action='store_true', help='Extract only images containing text')
    parser.add_argument('--threads', type=int, default=0, help='Number of threads to use (0 for auto)')
    parser.add_argument('--tesseract_path', help='Path to the Tesseract executable')
    # 前処理やtesseract周り
    parser.add_argument('--preprocess', action='store_true', help='Apply image preprocessing')
    parser.add_argument('--enhance_contrast', type=float, default=1.0, help='Contrast enhancement factor')
    parser.add_argument('--enhance_sharpness', type=float, default=1.0, help='Sharpness enhancement factor')
    parser.add_argument('--tesseract_lang', default='eng', help='Tesseract language model (`jpn`, `eng+jpn` etc...). Need to get the model from tessdata.')
    parser.add_argument('--tesseract_config', default='', help='Additional Tesseract configuration')
    parser.add_argument('--min_confidence', type=float, default=0, help='Minimum confidence score for text detection')
    return parser

def setup_signal_handler():
    def signal_handler(signum, frame):
        print("\nScript interrupted. Cleaning up...")
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)

def create_directory(path):
    os.makedirs(path, exist_ok=True)

def get_optimal_thread_count():
    return max(1, os.cpu_count() - 1)

def preprocess_image(image, args):
    if args.preprocess:
        # コントラスト調整
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(args.enhance_contrast)
        
        # シャープネス調整
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(args.enhance_sharpness)
        
        # ノイズ除去（オプション）
        image = image.filter(ImageFilter.MedianFilter())
        
        # グレースケール変換
        image = image.convert('L')
        
        # 二値化（オプション）
        # image = image.point(lambda x: 0 if x < 128 else 255, '1')
    
    return image

def has_text_in_image(image_path, args):
    try:
        with Image.open(image_path) as img:
            preprocessed_img = preprocess_image(img, args)
            
            # Tesseractの設定
            custom_config = f'-l {args.tesseract_lang} {args.tesseract_config}'
            
            # 文字認識と信頼度スコアの取得
            data = pytesseract.image_to_data(preprocessed_img, config=custom_config, output_type=pytesseract.Output.DICT)
            
            # 信頼度が閾値を超える文字がある場合にTrueを返す
            confidences = [float(conf) for conf in data['conf'] if conf != '-1']
            if args.debug:
                print(f"Processed {image_path}: confidences = {confidences}")
            return any(conf > args.min_confidence for conf in confidences)
    except Exception as e:
        print(f"Error processing image {image_path}: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return False

def process_file(args, root, file, tag_content=None):
    try:
        file_path = os.path.join(root, file)
        _, ext = os.path.splitext(file)

        if ext.lower() not in ['.jpg', '.jpeg', '.png', '.webp']:
            return None

        if args.Images_with_text_only and not has_text_in_image(file_path, args):
            return None

        if args.search_tag and tag_content and args.search_tag.lower() not in tag_content.lower():
            return None

        rel_path = os.path.relpath(root, args.dir_image)
        if args.preserve_own_folder:
            rel_path = os.path.join(os.path.basename(args.dir_image), rel_path)

        save_dir_image = os.path.join(args.dir_save, 'image', rel_path) if args.preserve_structure else os.path.join(args.dir_save, 'image')
        save_dir_tag = os.path.join(args.dir_save, 'tag', rel_path) if args.preserve_structure else os.path.join(args.dir_save, 'tag')

        create_directory(save_dir_image)
        create_directory(save_dir_tag)

        new_image_path = os.path.join(save_dir_image, file)
        new_tag_path = os.path.join(save_dir_tag, os.path.splitext(file)[0] + '.txt')

        if not args.debug:
            if args.cut:
                shutil.move(file_path, new_image_path)
                if tag_content:
                    with open(new_tag_path, 'w', encoding='utf-8') as f:
                        f.write(tag_content)
            else:
                shutil.copy2(file_path, new_image_path)
                if tag_content:
                    with open(new_tag_path, 'w', encoding='utf-8') as f:
                        f.write(tag_content)

        return file

    except Exception as e:
        print(f"Error processing file {file}: {e}")
        return None

def main():
    parser = setup_argument_parser()
    args = parser.parse_args()

    if args.tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = args.tesseract_path
    else:
        print("Tesseract path is not set. Using default path.")

    setup_signal_handler()

    if not args.cut and not args.copy:
        print("Error: Either --cut or --copy must be specified.")
        sys.exit(1)

    if args.threads == 0:
        args.threads = get_optimal_thread_count()

    print(f"Using {args.threads} threads")

    create_directory(args.dir_save)

    files_to_process = []
    for root, _, files in os.walk(args.dir_image):
        for file in files:
            _, ext = os.path.splitext(file)
            if ext.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                tag_content = None
                if args.dir_tag:
                    tag_file = os.path.join(args.dir_tag, os.path.relpath(root, args.dir_image), os.path.splitext(file)[0] + '.txt')
                    if os.path.exists(tag_file):
                        with open(tag_file, 'r', encoding='utf-8') as f:
                            tag_content = f.read()
                files_to_process.append((root, file, tag_content))

        if not args.recursive:
            break

    processed_files = []
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = [executor.submit(process_file, args, root, file, tag_content) for root, file, tag_content in files_to_process]
        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing files"):
            result = future.result()
            if result:
                processed_files.append(result)

    print(f"Processed {len(processed_files)} files")

if __name__ == "__main__":
    main()
