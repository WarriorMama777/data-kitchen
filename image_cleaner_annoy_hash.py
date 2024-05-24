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
    parser = argparse.ArgumentParser(description='画像の重複を削除するスクリプト')
    parser.add_argument('--dir', type=str, help='画像が格納されているディレクトリ')
    parser.add_argument('--extension', type=str, default='jpg jpeg png', help='対象とするファイルの拡張子')
    parser.add_argument('--recursive', action='store_true', help='サブディレクトリも含めて画像を検索')
    parser.add_argument('--by_folder', action='store_true', help='フォルダごとに分けて処理')
    parser.add_argument('--save_dir', type=str, help='重複していない画像を保存するディレクトリ')
    parser.add_argument('--save_dir_duplicate', type=str, help='重複している画像を保存するディレクトリ', default=None)
    parser.add_argument('--threshold', type=int, default=5, help='重複と判断する閾値')
    parser.add_argument('--debug', action='store_true', help='デバッグ情報を表示')
    parser.add_argument('--preserve_own_folder', action='store_true', help='元のフォルダ構造を保持')
    parser.add_argument('--preserve_structure', action='store_true', help='ファイルの保存時にディレクトリ構造を保持')
    parser.add_argument('--gc_disable', action='store_true', help='ガベージコレクションを無効にする')
    parser.add_argument('--batch_size', type=int, default=10, help='1回の処理で扱う画像の数')
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

def process_images(image_files, save_dir, save_dir_duplicate, threshold, debug, preserve_own_folder, preserve_structure, gc_disable, batch_size):
    if gc_disable:
        gc.disable()

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    if save_dir_duplicate and not os.path.exists(save_dir_duplicate):
        os.makedirs(save_dir_duplicate)
    
    hash_size = 64
    index = AnnoyIndex(hash_size, 'hamming')
    file_hashes = []

    for batch_start in tqdm(range(0, len(image_files), batch_size), desc="Processing batches"):
        batch_files = image_files[batch_start:batch_start+batch_size]
        for i, file in enumerate(batch_files):
            global_index = batch_start + i  # 全体のインデックス
            image_hash = hash_image(file)
            if image_hash is not None:
                binary_hash_array = image_hash_to_binary_array(image_hash)
                file_hashes.append((global_index, file, image_hash))
                index.add_item(global_index, binary_hash_array)

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
    for index in unique_images:
        _, file, _ = file_hashes[index]
        save_path = get_save_path(file, save_dir, args)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        shutil.copy2(file, save_path)

    for dup_index, orig_index in duplicates.items():
        _, dup_file, _ = file_hashes[dup_index]
        if save_dir_duplicate:
            save_path = get_save_path(dup_file, save_dir_duplicate, args)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            shutil.copy2(dup_file, save_path)
        else:
            _, orig_file, _ = file_hashes[orig_index]
            save_path = get_save_path(orig_file, save_dir, args)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            shutil.copy2(orig_file, save_path)

    # 処理結果の表示
    original_count = len(image_files)
    saved_count = sum(os.path.isfile(os.path.join(dp, f)) for dp, dn, filenames in os.walk(save_dir) for f in filenames)
    reduced_count = original_count - saved_count
    print(f"{reduced_count}枚削減されました。")

def get_save_path(file, base_dir, args):
    if args.preserve_structure:
        return os.path.join(base_dir, os.path.relpath(file, Path(args.dir).parent if args.preserve_own_folder else args.dir))
    else:
        if args.preserve_own_folder:
            base_dir_name = os.path.basename(os.path.normpath(args.dir))
            return os.path.join(base_dir, base_dir_name, os.path.basename(file))
        else:
            return os.path.join(base_dir, os.path.basename(file))

def image_hash_to_binary_array(image_hash):
    binary_string = bin(int(str(image_hash), 16))[2:].zfill(64)
    binary_array = np.array(list(binary_string), dtype=int)
    return binary_array

if __name__ == "__main__":
    args = parse_arguments()
    image_files = get_image_files(args.dir, args.extension, args.recursive, args.by_folder)
    process_images(image_files, args.save_dir, args.save_dir_duplicate, args.threshold, args.debug, args.preserve_own_folder, args.preserve_structure, args.gc_disable, args.batch_size)