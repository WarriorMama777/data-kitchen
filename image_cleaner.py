import os
import argparse
import cv2
from typing import List, Dict
import numpy as np
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import signal
import sys
import functools

def dhash(image, hashSize=8):
    resized = cv2.resize(image, (hashSize + 1, hashSize))
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    diff = gray[:, 1:] > gray[:, :-1]
    return sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])

def hamming_distance(hash1, hash2):
    return bin(hash1 ^ hash2).count('1')

def load_images_from_directory(directory: str, extensions: List[str], recursive: bool = False) -> List[str]:
    image_paths = []
    if recursive:
        for root, _, files in os.walk(directory):
            for file in files:
                if file.split('.')[-1].lower() in extensions:
                    image_paths.append(os.path.join(root, file))
    else:
        for file in os.listdir(directory):
            if file.split('.')[-1].lower() in extensions:
                image_paths.append(os.path.join(directory, file))
    return image_paths

def process_image(imagePath, args, hashes):
    image = cv2.imread(imagePath)
    if image is None:
        if args.verbose or args.debug:
            print(f"エラー: 画像を読み込めませんでした {imagePath} / Failed to load image {imagePath}")
        return None, None

    h = dhash(image)
    if args.verbose or args.debug:
        print(f"Debug: 計算されたハッシュ {h} for {imagePath}")

    duplicate = False
    for stored_hash in hashes.keys():
        if hamming_distance(h, stored_hash) <= args.threshold:
            if args.verbose or args.debug:
                print(f"類似画像が検出されました: {imagePath} は無視されます。")
            duplicate = True
            break
    if duplicate:
        return None, None

    return h, imagePath

def signal_handler(sig, frame):
    print('強制終了が要求されました。クリーンアップしています...')
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, help="処理するディレクトリ / Directory to process")
    parser.add_argument("--save_dir", default="output/", help="出力を保存するディレクトリ / Directory to save the output")
    parser.add_argument("--extension", default="jpg png webp", help="処理するファイル拡張子 / File extensions to process")
    parser.add_argument("--recursive", action='store_true', help="サブディレクトリを再帰的に検索 / Search subdirectories recursively")
    parser.add_argument("-v", "--verbose", action='store_true', help="冗長な情報を表示 / Display verbose information")
    parser.add_argument("--debug", action='store_true', help="デバッグモードを有効にします / Enable debug mode")
    parser.add_argument("--threshold", type=int, default=5, help="画像類似度の判定のしきい値。この値を増やすとより削減されるようになります。 / Threshold for image similarity judgement")
    parser.add_argument("--threads", type=int, default=multiprocessing.cpu_count(), help="使用するスレッド数 / Number of threads to use")
    parser.add_argument("--batch_size", type=int, default=32, help="バッチ処理のサイズ / Batch size for processing")
    args = parser.parse_args()

    if not os.path.exists(args.save_dir):
        os.makedirs(args.save_dir)

    allowed_extensions = [ext.lower() for ext in args.extension.split()]
    imagePathList = load_images_from_directory(args.dir, allowed_extensions, args.recursive)

    if args.verbose or args.debug:
        print(f"Debug: 処理する画像のリスト {imagePathList}")

    hashes: Dict[int, List[str]] = {}

    try:
        with ProcessPoolExecutor(max_workers=args.threads) as executor:
            futures = []
            for i in range(0, len(imagePathList), args.batch_size):
                batch = imagePathList[i:i + args.batch_size]
                for imagePath in batch:
                    futures.append(executor.submit(process_image, imagePath, args, hashes))

            for future in tqdm(as_completed(futures), total=len(futures), desc="画像解析中 / Analyzing images"):
                h, imagePath = future.result()
                if h is not None and imagePath is not None:
                    hashes[h] = imagePath
                    if not args.debug:
                        relative_path = os.path.relpath(imagePath, args.dir)
                        save_path = os.path.join(args.save_dir, relative_path)
                        save_dir = os.path.dirname(save_path)
                        if not os.path.exists(save_dir):
                            os.makedirs(save_dir)
                        cv2.imwrite(save_path, cv2.imread(imagePath))
                        if args.verbose or args.debug:
                            print(f"保存完了 {imagePath} へ {save_path}。 / Saved {imagePath} to {save_path}.")

        if args.debug:
            print(f"データセットは{len(hashes)}枚に削減されます。 / Datasets reduced to {len(hashes)} images.")
        elif args.verbose:
            print(f"データセットは{len(hashes)}枚に削減されました。 / Datasets was reduced to {len(hashes)} images.")
        else:
            print(f"データセットは{len(hashes)}枚に削減されました。/ Datasets was reduced to {len(hashes)} images.")
    except KeyboardInterrupt:
        print("強制終了されました。クリーンアップしています...")
        sys.exit(0)

if __name__ == "__main__":
    main()
