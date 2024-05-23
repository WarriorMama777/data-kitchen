import argparse
import os
import signal
from pathlib import Path

def signal_handler(sig, frame):
    print('中断されました。安全に終了します。')
    exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def write_path(file, path, quote):
    if quote:
        path = f'"{path}"'
    file.write(f'{path}\n')

def process_paths(target_dir, recursive, target, quote, debug):
    paths = []
    if recursive:
        for root, dirs, files in os.walk(target_dir):
            items = dirs if target == 'folder' else files
            for item in items:
                path = Path(root) / item
                paths.append(path)
    else:
        items = target_dir.iterdir()
        for item in items:
            if (target == 'folder' and item.is_dir()) or (target == 'file' and item.is_file()):
                paths.append(item)
    
    return paths

def main():
    parser = argparse.ArgumentParser(description='指定されたディレクトリ内のフォルダまたはファイルの絶対パスを取得してテキストファイルに保存します。')
    parser.add_argument('--dir', required=True, help='処理対象ディレクトリ')
    parser.add_argument('--save_dir', default='output/', help='出力ディレクトリ')
    parser.add_argument('--recursive', action='store_true', help='サブディレクトリも探索する')
    parser.add_argument('--debug', action='store_true', help='デバッグモード')
    parser.add_argument('--mem_cache', default='ON', choices=['ON', 'OFF'], help='メモリキャッシュの使用')
    parser.add_argument('--quote', action='store_true', help='パスをダブルクオートで囲む')
    parser.add_argument('--target', default='folder', choices=['folder', 'file'], help='取得するパスの対象')
    args = parser.parse_args()

    target_dir = Path(args.dir)
    save_dir = Path(args.save_dir)

    os.makedirs(save_dir, exist_ok=True)

    with save_dir.joinpath('paths.txt').open('w', encoding='utf-8') as f:
        if args.mem_cache == 'ON':
            paths = process_paths(target_dir, args.recursive, args.target, args.quote, args.debug)
            for path in paths:
                write_path(f, path, args.quote)
                if args.debug:
                    print(f'{args.target.capitalize()}を発見: {path}')
        else:
            paths = process_paths(target_dir, args.recursive, args.target, args.quote, args.debug)
            for path in paths:
                write_path(f, path, args.quote)
                if args.debug:
                    print(f'{args.target.capitalize()}を発見: {path}')

    print('処理が完了しました。')

if __name__ == '__main__':
    main()
