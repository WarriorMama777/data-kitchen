import argparse
import os
import re
import signal
from pathlib import Path

def signal_handler(sig, frame):
    print('中断されました。安全に終了します。')
    exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def natural_sort_key(s, _nsre=re.compile('([0-9]+)')):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(_nsre, str(s))]

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

def sort_paths(paths, order, reverse):
    if order == 'name':
        return sorted(paths, key=natural_sort_key, reverse=reverse)
    elif order == 'size':
        return sorted(paths, key=lambda p: p.stat().st_size, reverse=reverse)
    elif order == 'mtime':
        return sorted(paths, key=lambda p: p.stat().st_mtime, reverse=reverse)
    elif order == 'ctime':
        return sorted(paths, key=lambda p: p.stat().st_ctime, reverse=reverse)
    else:
        return paths

def get_next_output_file(save_dir):
    counter = 1
    while True:
        output_file = save_dir / f'paths_{counter}.txt'
        if not output_file.exists():
            return output_file
        counter += 1

def main():
    parser = argparse.ArgumentParser(description='指定されたディレクトリ内のフォルダまたはファイルの絶対パスを取得してテキストファイルに保存します。')
    parser.add_argument('--dir', required=True, help='処理対象ディレクトリ')
    parser.add_argument('--save_dir', default='output/', help='出力ディレクトリ')
    parser.add_argument('--recursive', action='store_true', help='サブディレクトリも探索する')
    parser.add_argument('--debug', action='store_true', help='デバッグモード')
    parser.add_argument('--mem_cache', default='ON', choices=['ON', 'OFF'], help='メモリキャッシュの使用')
    parser.add_argument('--quote', action='store_true', help='パスをダブルクオートで囲む')
    parser.add_argument('--target', default='folder', choices=['folder', 'file'], help='取得するパスの対象')
    parser.add_argument('--order', default='name', choices=['name', 'size', 'mtime', 'ctime'], help='パスの並び順')
    parser.add_argument('--reverse', action='store_true', help='降順に並べ替える')
    args = parser.parse_args()

    target_dir = Path(args.dir)
    save_dir = Path(args.save_dir)

    os.makedirs(save_dir, exist_ok=True)

    output_file = get_next_output_file(save_dir)

    with output_file.open('w', encoding='utf-8') as f:
        if args.mem_cache == 'ON':
            paths = process_paths(target_dir, args.recursive, args.target, args.quote, args.debug)
            paths = sort_paths(paths, args.order, args.reverse)
            for path in paths:
                write_path(f, path, args.quote)
                if args.debug:
                    print(f'{args.target.capitalize()}を発見: {path}')
        else:
            paths = process_paths(target_dir, args.recursive, args.target, args.quote, args.debug)
            paths = sort_paths(paths, args.order, args.reverse)
            for path in paths:
                write_path(f, path, args.quote)
                if args.debug:
                    print(f'{args.target.capitalize()}を発見: {path}')

    print(f'処理が完了しました。出力ファイル: {output_file}')

if __name__ == '__main__':
    main()
