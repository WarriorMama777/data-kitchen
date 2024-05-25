import argparse
import os
import signal
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from tqdm import tqdm
from wand.image import Image

# Ctrl+Cで安全に停止させるためのハンドラ設定
def signal_handler(sig, frame):
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# 引数の解析
parser = argparse.ArgumentParser(description="画像変換スクリプト")
parser.add_argument("--dir", required=True, help="処理対象ディレクトリ")
parser.add_argument("--save_dir", default="output/", help="出力ディレクトリ")
parser.add_argument("--extension", nargs="+", help="処理対象となるファイルの拡張子")
parser.add_argument("--recursive", action="store_true", help="サブディレクトリも含めて探索")
parser.add_argument("--background", help="透過画像の背景色 例：#ffffff")
parser.add_argument("--resize", type=int, help="リサイズする長辺のサイズ")
parser.add_argument("--format", help="変換後の画像形式")
parser.add_argument("--quality", type=int, help="画像品質")
parser.add_argument("--comp", type=int, help="画像圧縮の強度")
parser.add_argument("--debug", action="store_true", help="デバッグモード")
parser.add_argument("--preserve_own_folder", action="store_true", help="元のフォルダ名を保持")
parser.add_argument("--preserve_structure", action="store_true", help="ディレクトリ構造を保持")
parser.add_argument("--gc_disable", action="store_true", help="ガベージコレクションを無効化")
parser.add_argument("--by_folder", action="store_true", help="フォルダごとに処理")
parser.add_argument("--mem_cache", choices=["ON", "OFF"], default="ON", help="メモリキャッシュの使用")
parser.add_argument("--threads", type=int, default=4, help="使用するスレッド数")  # スレッド数のデフォルト値を設定
args = parser.parse_args()

# 出力ディレクトリの作成
Path(args.save_dir).mkdir(parents=True, exist_ok=True)

def process_image(image_path):
    try:
        with Image(filename=image_path) as img:
            # リサイズ処理
            if args.resize:
                img.transform(resize=f"{args.resize}x{args.resize}>")
            # 背景色設定
            if args.background:
                img.background_color = args.background
                img.alpha_channel = 'remove'
            # 画質設定
            if args.quality:
                img.compression_quality = args.quality
            # 形式変換
            if args.format:
                img.format = args.format

            # 出力ファイルパスの生成
            if args.preserve_own_folder:
                save_path = Path(args.save_dir) / Path(args.dir).name / image_path.relative_to(args.dir).with_suffix(f".{args.format}" if args.format else image_path.suffix)
            else:
                save_path = Path(args.save_dir) / image_path.relative_to(args.dir).with_suffix(f".{args.format}" if args.format else image_path.suffix)
            
            save_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(filename=save_path)
    except Exception as e:
        print(f"Error processing {image_path}: {e}")

def find_images(directory, extensions):
    if args.recursive:
        return [f for ext in extensions for f in Path(directory).rglob(f"*.{ext}")]
    else:
        return [f for ext in extensions for f in Path(directory).glob(f"*.{ext}")]

def main():
    if args.gc_disable:
        import gc
        gc.disable()
    
    images = find_images(args.dir, args.extension)
    
    if args.debug:
        print("デバッグモード：以下のファイルが処理されます")
        for img in images:
            print(img)
        return

    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = [executor.submit(process_image, img) for img in images]
        list(tqdm(as_completed(futures), total=len(images), desc="Processing Images"))

if __name__ == "__main__":
    main()
