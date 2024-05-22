import argparse
import os
import signal
from pathlib import Path
import shutil
from tqdm import tqdm

# KeyboardInterrupt時の処理
def signal_handler(sig, frame):
    print('中断されました。安全に終了します。')
    exit(0)

# シグナルハンドラの設定
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def main():
    parser = argparse.ArgumentParser(description='指定されたディレクトリ内のフォルダの絶対パスを取得してテキストファイルに保存します。')
    parser.add_argument('--dir', required=True, help='処理対象ディレクトリ')
    parser.add_argument('--save_dir', default='output/', help='出力ディレクトリ')
    parser.add_argument('--recursive', action='store_true', help='サブディレクトリも探索する')
    parser.add_argument('--debug', action='store_true', help='デバッグモード')
    parser.add_argument('--mem_cache', default='ON', choices=['ON', 'OFF'], help='メモリキャッシュの使用')
    args = parser.parse_args()

    target_dir = Path(args.dir)
    save_dir = Path(args.save_dir)

    # 出力ディレクトリの確認と作成
    if not save_dir.exists():
        os.makedirs(save_dir)

    paths = []
    if args.recursive:
        for root, dirs, files in os.walk(target_dir):
            for dir in dirs:
                path = Path(root) / dir
                paths.append(f'"{path}"')
                if args.debug:
                    print(f'ディレクトリを発見: {path}')
    else:
        if target_dir.is_dir():
            for dir in target_dir.iterdir():
                if dir.is_dir():
                    paths.append(f'"{dir}"')
                    if args.debug:
                        print(f'ディレクトリを発見: {dir}')
        else:
            paths.append(f'"{target_dir}"')

    # メモリキャッシュがONの場合、最後に一括でファイルに書き込む
    if args.mem_cache == 'ON':
        with save_dir.joinpath('paths.txt').open('w', encoding='utf-8') as f:
            for path in tqdm(paths, desc='ファイル書き込み'):
                f.write(path + '\n')
    else:  # メモリキャッシュがOFFの場合、発見次第ファイルに書き込む
        with save_dir.joinpath('paths.txt').open('w', encoding='utf-8') as f:
            for path in tqdm(paths, desc='ファイル書き込み'):
                f.write(path + '\n')

    print('処理が完了しました。')

if __name__ == '__main__':
    main()
