import argparse
import os
import cv2
import numpy as np
from tqdm import tqdm
from collections import defaultdict
import shutil
import signal
import gc

def signal_handler(signal, frame):
    print("\nプログラムが中断されました。")
    exit(0)

signal.signal(signal.SIGINT, signal_handler)

def dhash(image, hashSize=8):
    # 画像をリサイズし、グレースケールに変換
    resized = cv2.resize(image, (hashSize + 1, hashSize))
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

    # 左から右に向かって、ピクセルを比較しハッシュを生成
    diff = gray[:, 1:] > gray[:, :-1]
    return sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])

def process_images(args):
    if args.gc_disable:
        gc.disable()

    # 引数で指定されたディレクトリの画像を取得
    extensions = args.extension.split()
    images = []
    for root, dirs, files in os.walk(args.dir, topdown=True):
        if not args.recursive:
            dirs.clear()
        for file in files:
            if any(file.lower().endswith(ext) for ext in extensions):
                path = os.path.join(root, file)
                images.append(path)
                if args.by_folder:
                    break

    # 画像のハッシュを計算して格納
    image_hashes = {}
    for image_path in tqdm(images, desc="画像のハッシュ計算"):
        image = cv2.imread(image_path)
        image_hash = dhash(image)
        if image_hash not in image_hashes:
            image_hashes[image_hash] = []
        image_hashes[image_hash].append(image_path)

    # 類似画像を削減
    processed_images = {}
    duplicate_images = defaultdict(list)
    for image_hash, paths in tqdm(image_hashes.items(), desc="類似画像の削減"):
        if len(paths) > 1:
            for path in paths[1:]:
                duplicate_images[paths[0]].append(path)
        processed_images[paths[0]] = None

    if not os.path.exists(args.save_dir):
        os.makedirs(args.save_dir)

    if args.save_dir_duplicate and not os.path.exists(args.save_dir_duplicate):
        os.makedirs(args.save_dir_duplicate)

    # 画像を保存
    for image_path in tqdm(processed_images.keys(), desc="画像の保存"):
        dest_path = os.path.join(args.save_dir, os.path.basename(image_path)) if not args.preserve_own_folder else os.path.join(args.save_dir, os.path.relpath(image_path, args.dir))
        shutil.copy2(image_path, dest_path)

    # 重複画像を別ディレクトリに保存
    for original, duplicates in tqdm(duplicate_images.items(), desc="重複画像の保存"):
        if args.save_dir_duplicate:
            for duplicate in duplicates:
                dest_path = os.path.join(args.save_dir_duplicate, os.path.basename(duplicate)) if not args.preserve_own_folder else os.path.join(args.save_dir_duplicate, os.path.relpath(duplicate, args.dir))
                shutil.copy2(duplicate, dest_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, help="処理対象ディレクトリ")
    parser.add_argument("--save_dir", default="output/", help="出力ディレクトリ")
    parser.add_argument("--extension", default="jpg png webp", help="処理対象となるファイル拡張子")
    parser.add_argument("--recursive", action="store_true", help="サブディレクトリも探索する")
    parser.add_argument("--debug", action="store_true", help="デバッグモード")
    parser.add_argument("--threshold", type=int, default=10, help="画像類似度の判定しきい値")
    parser.add_argument("--preserve_own_folder", action="store_true", help="元のフォルダ名で保存")
    parser.add_argument("--preserve_structure", action="store_true", help="ディレクトリ構造を保持して保存")
    parser.add_argument("--gc_disable", action="store_true", help="ガベージコレクションを無効にする")
    parser.add_argument("--by_folder", action="store_true", help="フォルダごとに処理")
    parser.add_argument("--batch_size", type=int, default=10, help="バッチサイズ")
    parser.add_argument("--save_dir_duplicate", help="重複判定された画像を保存するディレクトリ")
    parser.add_argument("--mem_cache", default="ON", help="メモリキャッシュを使用するかどうか")
    args = parser.parse_args()

    if args.debug:
        print("デバッグモードで実行します。")
    else:
        process_images(args)

