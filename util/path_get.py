import argparse
import os
import signal
from pathlib import Path

def signal_handler(sig, frame):
    print('中断されました。安全に終了します。')
    exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def main():
    parser = argparse.ArgumentParser(description='指定されたディレクトリ内のフォルダの絶対パスを取得してテキストファイルに保存します。')
    parser.add_argument('--dir', required=True, help='処理対象ディレクトリ')
    parser.add_argument('--save_dir', default='output/', help='出力ディレクトリ')
    parser.add_argument('--recursive', action='store_true', help='サブディレクトリも探索する')
    parser.add_argument('--debug', action='store_true', help='デバッグモード')
    parser.add_argument('--mem_cache', default='ON', choices=['ON', 'OFF'], help='メモリキャッシュの使用')
    parser.add_argument('--quote', action='store_true', help='パスをダブルクオートで囲む')
    args = parser.parse_args()

    target_dir = Path(args.dir)
    save_dir = Path(args.save_dir)

    os.makedirs(save_dir, exist_ok=True)

    if args.mem_cache == 'ON':
        paths = []

    with save_dir.joinpath('paths.txt').open('w', encoding='utf-8') as f:
        def write_path(path):
            if args.quote:
                path = f'"{path}"'
            f.write(f'{path}\n')
            if args.debug:
                print(f'ディレクトリを発見: {path}')

        if args.recursive:
            for root, dirs, files in os.walk(target_dir):
                for dir in dirs:
                    path = Path(root) / dir
                    if args.mem_cache == 'ON':
                        paths.append(str(path))
                    else:
                        write_path(path)
        else:
            for dir in target_dir.iterdir():
                if dir.is_dir():
                    if args.mem_cache == 'ON':
                        paths.append(str(dir))
                    else:
                        write_path(dir)
        
        if args.mem_cache == 'ON':
            for path in paths:
                write_path(path)

    print('処理が完了しました。')

if __name__ == '__main__':
    main()
