import os
import json
import re
import argparse
import signal
import threading
import concurrent.futures
from tqdm import tqdm
from pathlib import Path

# グローバル変数
stop_event = threading.Event()

# Signal handler
def signal_handler(sig, frame):
    print('停止信号を受信しました。処理を終了します...')
    stop_event.set()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def parse_args():
    parser = argparse.ArgumentParser(description="JSONファイルを編集するスクリプト")
    parser.add_argument('--dir', required=True, help="処理対象ディレクトリ")
    parser.add_argument('--dir_save', default='./output', help="出力ディレクトリ")
    parser.add_argument('--recursive', action='store_true', help="サブディレクトリも再帰的に処理")
    parser.add_argument('--debug', action='store_true', help="デバッグモード")
    parser.add_argument('--replace', nargs=2, metavar=('old_value', 'new_value'), help="文字列値を置換")
    parser.add_argument('--replace_key', nargs=2, metavar=('old_key', 'new_key'), help="キー名を置換")
    parser.add_argument('--replace_regex', nargs=2, metavar=('pattern', 'replacement'), help="正規表現による置換")
    parser.add_argument('--threads', type=int, help="使用するスレッド数を指定")
    return parser.parse_args()

def json_replace(data, old_value, new_value):
    if isinstance(data, dict):
        return {k: json_replace(v, old_value, new_value) for k, v in data.items()}
    elif isinstance(data, list):
        return [json_replace(item, old_value, new_value) for item in data]
    elif isinstance(data, str) and data == old_value:
        return new_value
    return data

def json_replace_key(data, old_key, new_key):
    if isinstance(data, dict):
        return {new_key if k == old_key else k: json_replace_key(v, old_key, new_key) for k, v in data.items()}
    elif isinstance(data, list):
        return [json_replace_key(item, old_key, new_key) for item in data]
    return data

def json_replace_regex(data, pattern, replacement):
    if isinstance(data, dict):
        return {k: json_replace_regex(v, pattern, replacement) for k, v in data.items()}
    elif isinstance(data, list):
        return [json_replace_regex(item, pattern, replacement) for item in data]
    elif isinstance(data, str):
        return re.sub(pattern, replacement, data)
    return data

def process_json_file(file_path, save_dir, args):
    if stop_event.is_set():
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"エラー: {file_path} を読み込めませんでした。{e}")
        return

    if args.replace:
        data = json_replace(data, args.replace[0], args.replace[1])
    if args.replace_key:
        data = json_replace_key(data, args.replace_key[0], args.replace_key[1])
    if args.replace_regex:
        data = json_replace_regex(data, args.replace_regex[0], args.replace_regex[1])

    if args.debug:
        print(f"デバッグ: {file_path} の処理内容: {data}")
    else:
        try:
            relative_path = os.path.relpath(file_path, args.dir)
            save_path = os.path.join(save_dir, relative_path)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"エラー: {file_path} を保存できませんでした。{e}")

def find_json_files(directory, recursive):
    if recursive:
        return [str(p) for p in Path(directory).rglob("*.json")]
    else:
        return [str(p) for p in Path(directory).glob("*.json")]

def main():
    args = parse_args()

    json_files = find_json_files(args.dir, args.recursive)

    if args.threads:
        num_threads = args.threads
    else:
        num_threads = os.cpu_count()

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        list(tqdm(executor.map(lambda f: process_json_file(f, args.dir_save, args), json_files), total=len(json_files)))

if __name__ == '__main__':
    main()
