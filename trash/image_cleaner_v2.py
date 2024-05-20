import os
import argparse
from imutils import paths
import cv2
from typing import List, Dict, Tuple
import numpy as np
from tqdm import tqdm
import concurrent.futures

def dhash(image, hashSize=8) -> int:
    resized = cv2.resize(image, (hashSize + 1, hashSize))
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    diff = gray[:, 1:] > gray[:, :-1]
    return sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])

def hamming_distance(hash1, hash2) -> int:
    return bin(hash1 ^ hash2).count('1')

def process_image(imagePath: str, args) -> Tuple[int, str, bool]:
    image = cv2.imread(imagePath)
    h = dhash(image)
    return (h, imagePath, False)

def save_image(data: Tuple[int, str, bool], args, hashes: Dict[int, str]):
    h, imagePath, duplicate = data
    if not duplicate:
        hashes[h] = imagePath
        if not args.debug:  # `--debug`が有効でない場合にのみ保存
            relative_path = os.path.relpath(imagePath, args.dir)
            save_path = os.path.join(args.save_dir, relative_path)
            save_dir = os.path.dirname(save_path)
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            cv2.imwrite(save_path, cv2.imread(imagePath))
            if args.verbose or args.debug:
                print(f"保存完了 {imagePath} へ {save_path}。 / Saved {imagePath} to {save_path}.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, help="処理するディレクトリ / Directory to process")
    parser.add_argument("--save_dir", default="output/", help="出力を保存するディレクトリ / Directory to save the output")
    parser.add_argument("--extension", default="jpg png webp", help="処理するファイル拡張子 / File extensions to process")
    parser.add_argument("--recursive", action='store_true', help="サブディレクトリを再帰的に検索 / Search subdirectories recursively")
    parser.add_argument("-v", "--verbose", action='store_true', help="冗長な情報を表示 / Display verbose information")
    parser.add_argument("--debug", action='store_true', help="デバッグモードを有効にします / Enable debug mode")
    parser.add_argument("--threshold", type=int, default=5, help="画像類似度の判定のしきい値。この値を増やすとより削減されるようになります。 / Threshold for image similarity judgement")
    parser.add_argument("--processes", type=int, default=4, help="使用するプロセス数 / Number of processes to use")
    parser.add_argument("--multi_processing", action='store_true', help="マルチプロセス処理を有効にする / Enable multi-processing")
    args = parser.parse_args()

    if not os.path.exists(args.save_dir):
        os.makedirs(args.save_dir)

    if args.recursive:
        imagePathList = list(paths.list_images(args.dir))
    else:
        imagePathList = [os.path.join(args.dir, f) for f in os.listdir(args.dir) if f.split('.')[-1] in args.extension.split()]

    hashes: Dict[int, str] = {}

    Executor = concurrent.futures.ProcessPoolExecutor if args.multi_processing else concurrent.futures.ThreadPoolExecutor
    with Executor(max_workers=args.processes) as executor:
        # 画像処理
        future_to_image = {executor.submit(process_image, imagePath, args): imagePath for imagePath in imagePathList}
        # tqdmを用いて進捗状況を表示
        for future in tqdm(concurrent.futures.as_completed(future_to_image), total=len(imagePathList), desc="Processing images"):
            imagePath = future_to_image[future]
            try:
                data = future.result()
            except Exception as exc:
                print(f"{imagePath} の処理中に例外が発生しました: {exc}")
            else:
                save_image(data, args, hashes)

    # 最終的なメッセージを表示
    print(f"データセットは{len(hashes)}枚に削減されました。/ Datasets was reduced to {len(hashes)} images.")

if __name__ == "__main__":
    main()
