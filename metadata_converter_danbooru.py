import argparse
import json
import os
import signal
import sys
from pathlib import Path
from tqdm import tqdm
import time
from multiprocessing import Pool, cpu_count
import gc
import traceback

def signal_handler(sig, frame):
    print('終了シグナルを受信しました。クリーンアップを行います。')
    sys.exit(0)

def process_file_wrapper(args):
    return process_file(*args)

def process_file(file_path, current_save_dir, metadata_order, save_extension='txt', insert_custom_texts=None, debug=False, mem_cache=True):
    if file_path.endswith('.txt') or file_path.endswith('.json'):
        if debug:
            print(f"[デバッグ] 処理するファイル: {file_path} -> 保存先: {current_save_dir}.{save_extension}")
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                metadata = json.load(file)
            
            if debug:
                print(f"[デバッグ] メタデータの型: {type(metadata)}")
                print(f"[デバッグ] メタデータの内容: {metadata}")

            if isinstance(metadata, list):
                if debug:
                    print("[デバッグ] メタデータはリストです。最初の要素を使用します。")
                metadata = metadata[0] if metadata else {}

            extracted_data = []
            for key in metadata_order:
                value = metadata.get(key, "")
                if value:
                    if isinstance(value, list):
                        value = ','.join(str(item) for item in value)
                    elif isinstance(value, (dict, int, float)):
                        value = str(value)
                    elif isinstance(value, str):
                        value = value.replace(' ', ',')
                    
                    if key == 'rating' and not value.startswith('rating_'):
                        value = f'rating_{value}'
                
                extracted_data.append(value)

            if insert_custom_texts:
                insert_pairs = [(int(insert_custom_texts[i]), insert_custom_texts[i + 1]) for i in range(0, len(insert_custom_texts), 2)]
                for index, text in sorted(insert_pairs, key=lambda x: x[0], reverse=True):
                    extracted_data.insert(index, text)

            output_content = ','.join(filter(None, extracted_data))
            return (current_save_dir, os.path.splitext(os.path.basename(file_path))[0] + f'.{save_extension}', output_content)
        except Exception as e:
            print(f"Error processing file {file_path}: {str(e)}")
            print(traceback.format_exc())
            return None, None
    return None, None

def save_processed_data(save_dir, file_name, data):
    if data is not None:
        output_file_path = os.path.join(save_dir, file_name)
        with open(output_file_path, 'w', encoding='utf-8') as output_file:
            output_file.write(data)
        print(f"Processed: {output_file_path}")

def process_directory(directory_path, save_dir, metadata_order, save_extension='txt', insert_custom_texts=None, debug=False, mem_cache=True, threads=None, recursive=False, preserve_own_folder=False, preserve_structure=False, by_folder=False):
    print(f"{directory_path} 内のファイルを処理中...")
    cache = []  # メモリキャッシュ用のリスト

    if preserve_own_folder:
        base_folder_name = os.path.basename(os.path.normpath(directory_path))
        save_dir = os.path.join(save_dir, base_folder_name)
        Path(save_dir).mkdir(parents=True, exist_ok=True)

    if by_folder:
        subdirs = [os.path.join(directory_path, d) for d in os.listdir(directory_path) if os.path.isdir(os.path.join(directory_path, d))]
        for subdir in subdirs:
            process_directory(subdir, save_dir, metadata_order, save_extension, insert_custom_texts, debug, mem_cache, threads, recursive, preserve_own_folder, preserve_structure, by_folder=False)
        return

    file_paths = []
    for root, dirs, files in os.walk(directory_path):
        if not recursive and root != directory_path:
            continue
        relative_path = os.path.relpath(root, directory_path)
        current_save_dir = os.path.join(save_dir, relative_path) if preserve_structure else save_dir
        Path(current_save_dir).mkdir(parents=True, exist_ok=True)

        for file_name in files:
            file_path = os.path.join(root, file_name)
            file_paths.append((file_path, current_save_dir, metadata_order, save_extension, insert_custom_texts, debug, mem_cache))

    if threads is None:
        threads = cpu_count()

    try:
        with Pool(processes=threads) as pool:
            results = pool.map(process_file_wrapper, file_paths)
    except Exception as e:
        print(f"Error in multiprocessing: {str(e)}")
        print(traceback.format_exc())
        return

    for result in results:
        if result is not None and len(result) == 3:
            save_dir, file_name, data = result
            if mem_cache:
                cache.append((save_dir, file_name, data))
            else:
                save_processed_data(save_dir, file_name, data)

    if mem_cache:
        for save_dir, file_name, data in cache:
            save_processed_data(save_dir, file_name, data)
        print("全データをメモリから一括で保存しました。")

def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    parser = argparse.ArgumentParser(description='Convert Danbooru metadata files to plain text format.')
    parser.add_argument('--dir', type=str, help='Directory containing metadata files', required=True)
    parser.add_argument('--save_dir', type=str, help='Directory to save converted files', required=True)
    parser.add_argument('--metadata_order', nargs='+', help='Order of metadata labels to extract. Format: --metadata_order "METADATA_LABEL" "METADATA_LABEL"', required=True)
    parser.add_argument('--insert_custom_text', nargs='*', help='Insert custom texts at specified indexes in the output. Format: --insert_custom_text INDEX "CUSTOM_TEXT" INDEX "CUSTOM_TEXT" ...', required=False)
    parser.add_argument('--debug', action='store_true', help='Enable debug mode to display processing logs without making actual changes.')
    parser.add_argument('--save_extension', type=str, default='txt', help='Extension of the output file. Default is "txt".', required=False)
    parser.add_argument('--mem_cache', type=str, choices=['ON', 'OFF'], default='ON', help='Enable or disable memory caching. Default is ON.')
    parser.add_argument('--threads', type=int, help='Number of threads to use. Default is the number of CPU cores.', required=False)
    parser.add_argument('--recursive', action='store_true', help='Recursively process directories.')
    parser.add_argument('--preserve_own_folder', action='store_true', help='Preserve the own folder structure in the save directory.')
    parser.add_argument('--preserve_structure', action='store_true', help='Preserve the directory structure in the save directory.')
    parser.add_argument('--gc_disable', action='store_true', help='Disable garbage collection.')
    parser.add_argument('--by_folder', action='store_true', help='Process each folder one by one.')

    args = parser.parse_args()

    if args.gc_disable:
        gc.disable()

    Path(args.save_dir).mkdir(parents=True, exist_ok=True)

    try:
        process_directory(args.dir, args.save_dir, args.metadata_order, args.save_extension, args.insert_custom_text, args.debug, mem_cache=args.mem_cache == 'ON', threads=args.threads, recursive=args.recursive, preserve_own_folder=args.preserve_own_folder, preserve_structure=args.preserve_structure, by_folder=args.by_folder)
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")
    finally:
        print("プログラムを終了します。")

if __name__ == '__main__':
    main()
