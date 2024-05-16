import os
import argparse
from imutils import paths
import cv2
from typing import List, Dict
import numpy as np
from tqdm import tqdm
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from numba import njit

@njit
def dhash(image, hashSize=8):
    resized = cv2.resize(image, (hashSize + 1, hashSize))
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    diff = gray[:, 1:] > gray[:, :-1]
    return np.sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])

def hamming_distance(hash1, hash2):
    return bin(hash1 ^ hash2).count('1')

def process_image(image_path, hashes, args):
    image = cv2.imread(image_path)
    h = dhash(image)

    duplicate = False
    for stored_hash in hashes.keys():
        if hamming_distance(h, stored_hash) <= args.threshold:
            if args.verbose or args.debug:
                print(f"類似画像が検出されました: {image_path} は無視されます。")
            duplicate = True
            break
    if duplicate:
        return

    hashes[h] = image_path

    if not args.debug:
        relative_path = os.path.relpath(image_path, args.dir)
        save_path = os.path.join(args.save_dir, relative_path)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        cv2.imwrite(save_path, image)
        if args.verbose or args.debug:
            print(f"保存完了 {image_path} へ {save_path}。")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, help="処理するディレクトリ")
    parser.add_argument("--save_dir", default="output/", help="出力を保存するディレクトリ")
    parser.add_argument("--extension", default="jpg png webp", help="処理するファイル拡張子")
    parser.add_argument("--recursive", action='store_true', help="サブディレクトリを再帰的に検索")
    parser.add_argument("-v", "--verbose", action='store_true', help="冗長な情報を表示")
    parser.add_argument("--debug", action='store_true', help="デバッグモードを有効にします")
    parser.add_argument("--threshold", type=int, default=5, help="画像類似度の判定のしきい値")
    args = parser.parse_args()

    if not os.path.exists(args.save_dir):
        os.makedirs(args.save_dir)

    if args.recursive:
        image_paths = list(paths.list_images(args.dir))
    else:
        image_paths = [os.path.join(args.dir, f) for f in os.listdir(args.dir) if any(ext in f.lower() for ext in args.extension.split())]

    hashes = {}

    # 画像の事前読み込み
    print("画像を読み込み中...")
    images = [cv2.imread(path) for path in tqdm(image_paths)]

    # マルチスレッド処理
    print("画像を処理中...")
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_image, path, hashes, args) for path in image_paths]
        for future in tqdm(as_completed(futures), total=len(futures), leave=False):  # 修正
            pass

    # 最終的なメッセージを表示
    print(f"データセットは{len(hashes)}枚に削減されました。")

if __name__ == "__main__":
    main()