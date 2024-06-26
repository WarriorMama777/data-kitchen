import os
import sys
import argparse
import signal
import threading
import concurrent.futures
from PIL import Image, ImageOps
from tqdm import tqdm
import gc

def parse_args():
    parser = argparse.ArgumentParser(description="Image processing script")
    parser.add_argument('--dir', required=True, help='Target directory')
    parser.add_argument('--save_dir', default='output/', help='Output directory')
    parser.add_argument('--extension', nargs='+', required=True, help='Target file extensions')
    parser.add_argument('--recursive', action='store_true', help='Process subdirectories')
    parser.add_argument('--background', help='Background color for transparent images')
    parser.add_argument('--resize', type=int, help='Resize images to have this max dimension')
    parser.add_argument('--format', help='Output image format')
    parser.add_argument('--quality', type=int, help='Output image quality')
    parser.add_argument('--comp', type=int, help='Compression level')
    parser.add_argument('--debug', action='store_true', help='Debug mode')
    parser.add_argument('--preserve_own_folder', action='store_true', help='Preserve original directory structure')
    parser.add_argument('--preserve_structure', action='store_true', help='Preserve directory structure')
    parser.add_argument('--gc_disable', action='store_true', help='Disable garbage collection')
    parser.add_argument('--by_folder', action='store_true', help='Process folders one by one')
    parser.add_argument('--mem_cache', default='ON', choices=['ON', 'OFF'], help='Use memory cache')
    parser.add_argument('--threads', type=int, help='Number of threads to use')
    parser.add_argument('--save_only_alphachannel', action='store_true', help='Save only alpha channel data')
    return parser.parse_args()

def signal_handler(sig, frame):
    print("Process interrupted. Exiting...")
    sys.exit(0)

def process_image(file_path, args, save_dir):
    try:
        with Image.open(file_path) as img:
            if args.save_only_alphachannel:
                if not img.mode in ('RGBA', 'LA'):
                    raise ValueError("Image does not have an alpha channel")
                alpha = img.split()[-1]
                
                if alpha.getextrema() == (255, 255):
                    return
                
                img = alpha.convert("L")
            
            if args.background and img.mode in ('RGBA', 'LA'):
                background = Image.new(img.mode[:-1], img.size, "#" + args.background)
                background.paste(img, img.split()[-1])
                img = background
            
            if args.resize:
                img.thumbnail((args.resize, args.resize), Image.Resampling.LANCZOS)
            
            # 保存パスの生成
            if args.preserve_structure:
                relative_path = os.path.relpath(file_path, args.dir)
                base, _ = os.path.splitext(relative_path)
                save_path = os.path.join(save_dir, base + '.' + (args.format or img.format.lower()))
                save_dir_structure = os.path.dirname(save_path)
                os.makedirs(save_dir_structure, exist_ok=True)
            else:
                save_path = os.path.join(save_dir, os.path.splitext(os.path.basename(file_path))[0] + '.' + (args.format or img.format.lower()))
            
            save_kwargs = {}
            if args.format:
                save_kwargs['format'] = args.format.upper()
            if args.quality:
                save_kwargs['quality'] = args.quality
            if args.comp:
                save_kwargs['compression'] = args.comp
            
            img.save(save_path, **save_kwargs)
            
            if args.debug:
                print(f"Processed: {file_path} -> {save_path}")
                
    except Exception as e:
        print(f"Failed to process {file_path}: {e}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error details: {str(e)}")

def get_file_list(root_dir, extensions, recursive):
    file_list = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            if any(file.lower().endswith(ext) for ext in extensions):
                file_list.append(os.path.join(root, file))
        if not recursive:
            break
    return file_list

def create_directory_structure(base_dir, target_dir, preserve_own_folder, preserve_structure):
    if preserve_structure:
        return base_dir  # preserve_structureが指定された場合はbase_dirをそのまま使用
    if preserve_own_folder:
        target_dir = os.path.join(base_dir, os.path.basename(target_dir))
    else:
        target_dir = base_dir  # preserve_own_folderおよびpreserve_structureが指定されていない場合もbase_dirを使用
    os.makedirs(target_dir, exist_ok=True)
    return target_dir

def main():
    args = parse_args()
    signal.signal(signal.SIGINT, signal_handler)
    
    if args.gc_disable:
        gc.disable()

    if args.save_only_alphachannel:
        if args.extension and any(ext.lower() not in ['png', 'webp'] for ext in args.extension):
            print("Error: --save_only_alphachannel is only supported for PNG and WebP formats.")
            sys.exit(1)
        if args.format and args.format.lower() not in ['png', 'webp']:
            print("Error: --save_only_alphachannel is only supported for PNG and WebP formats.")
            sys.exit(1)
        if args.background:
            print("Error: --save_only_alphachannel cannot be used with --background.")
            sys.exit(1)

    if args.by_folder:
        for subdir in os.listdir(args.dir):
            dir_path = os.path.join(args.dir, subdir)
            if os.path.isdir(dir_path):
                save_dir = create_directory_structure(args.save_dir, dir_path, args.
                preserve_own_folder, args.preserve_structure)
                os.makedirs(save_dir, exist_ok=True)
                file_list = get_file_list(dir_path, args.extension, args.recursive)
                if args.debug:
                    print(f"Processing {len(file_list)} images in {dir_path}")
                    continue
                with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads or (os.cpu_count() or 1)) as executor:
                    list(tqdm(executor.map(lambda file: process_image(file, args, save_dir), file_list), total=len(file_list)))
    else:
        save_dir = create_directory_structure(args.save_dir, args.dir, args.preserve_own_folder, args.preserve_structure)
        os.makedirs(save_dir, exist_ok=True)
        file_list = get_file_list(args.dir, args.extension, args.recursive)
        if args.debug:
            print(f"Processing {len(file_list)} images in {args.dir}")
            return
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads or (os.cpu_count() or 1)) as executor:
            list(tqdm(executor.map(lambda file: process_image(file, args, save_dir), file_list), total=len(file_list)))

if __name__ == '__main__':
    main()
