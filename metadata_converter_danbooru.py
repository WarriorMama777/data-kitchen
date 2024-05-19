import argparse
import json
import os
import signal
import sys
from pathlib import Path
from tqdm import tqdm
import time
from multiprocessing import Pool, cpu_count

def signal_handler(sig, frame):
    print('終了シグナルを受信しました。クリーンアップを行います。')
    sys.exit(0)

def process_file_wrapper(args):
    return process_file(*args)

def process_file(file_path, current_save_dir, metadata_order, save_extension='txt', insert_custom_texts=None, debug=False, mem_cache=True):
    if file_path.endswith('.txt') or file_path.endswith('.json'):
        if debug:
            print(f"[デバッグ] 処理するファイル: {file_path} -> 保存先: {current_save_dir}.{save_extension}")
        else:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    metadata = json.load(file)
            except json.JSONDecodeError:
                print(f"Warning: Skipping file due to JSONDecodeError: {file_path}")
                return None, None

            extracted_data = []
            for key in metadata_order:
                value = metadata.get(key, "")
                if value:
                    if key == 'rating':
                        value = f'rating_{value}'
                    else:
                        value = value.replace(' ', ',')
                extracted_data.append(value)

            if insert_custom_texts:
                insert_pairs = [(int(insert_custom_texts[i]), insert_custom_texts[i + 1]) for i in range(0, len(insert_custom_texts), 2)]
                for index, text in sorted(insert_pairs, key=lambda x: x[0], reverse=True):
                    extracted_data.insert(index, text)

            output_content = ','.join(filter(None, extracted_data))
            return (current_save_dir, os.path.splitext(os.path.basename(file_path))[0] + f'.{save_extension}', output_content)
    return None, None

def save_processed_data(save_dir, file_name, data):
    if data is not None:  # JSONDecodeErrorでスキップしたファイルを除外
        output_file_path = os.path.join(save_dir, file_name)
        with open(output_file_path, 'w', encoding='utf-8') as output_file:
            output_file.write(data)
        print(f"Processed: {output_file_path}")

def process_directory(directory_path, save_dir, metadata_order, save_extension='txt', insert_custom_texts=None, debug=False, mem_cache=True, threads=None):
    print(f"{directory_path} 内のファイルを処理中...")
    cache = []  # メモリキャッシュ用のリスト

    file_paths = []
    for root, dirs, files in os.walk(directory_path):
        relative_path = os.path.relpath(root, directory_path)
        current_save_dir = os.path.join(save_dir, relative_path)
        Path(current_save_dir).mkdir(parents=True, exist_ok=True)

        for file_name in files:
            file_path = os.path.join(root, file_name)
            file_paths.append((file_path, current_save_dir, metadata_order, save_extension, insert_custom_texts, debug, mem_cache))

    if threads is None:
        threads = cpu_count()

    with Pool(processes=threads) as pool:
        results = pool.map(process_file_wrapper, file_paths)

    for result in results:
        if result[0] is not None and result[1] is not None:
            if mem_cache:
                cache.append(result)
            else:
                save_processed_data(*result)

    if mem_cache:
        for save_dir, file_name, data in cache:
            save_processed_data(save_dir, file_name, data)
        print("全データをメモリから一括で保存しました。")

def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    parser = argparse.ArgumentParser(description='Convert Danbooru metadata files to plain text format.')
    parser.add_argument('--dir', type=str, help='Directory containing metadata files', required=True)
    parser.add_argument('--save', type=str, help='Directory to save converted files', required=True)
    parser.add_argument('--metadata_order', nargs='+', help='Order of metadata labels to extract. Format: --metadata_order "METADATA_LABEL" "METADATA_LABEL"', required=True)
    parser.add_argument('--insert_custom_text', nargs='*', help='Insert custom texts at specified indexes in the output. Format: --insert_custom_text INDEX "CUSTOM_TEXT" INDEX "CUSTOM_TEXT" ...', required=False)
    parser.add_argument('--debug', action='store_true', help='Enable debug mode to display processing logs without making actual changes.')
    parser.add_argument('--save_extension', type=str, default='txt', help='Extension of the output file. Default is "txt".', required=False)
    parser.add_argument('--mem_cache', type=str, choices=['ON', 'OFF'], default='ON', help='Enable or disable memory caching. Default is ON.')
    parser.add_argument('--threads', type=int, help='Number of threads to use. Default is the number of CPU cores.', required=False)

    args = parser.parse_args()

    Path(args.save).mkdir(parents=True, exist_ok=True)

    try:
        process_directory(args.dir, args.save, args.metadata_order, args.save_extension, args.insert_custom_text, args.debug, mem_cache=args.mem_cache == 'ON', threads=args.threads)
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")
    finally:
        print("プログラムを終了します。")

if __name__ == '__main__':
    main()
