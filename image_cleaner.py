import os
import argparse
from imutils import paths
import cv2
from typing import List, Dict
import numpy as np
from tqdm import tqdm

def dhash(image, hashSize=8):
    # 画像をリサイズし、グレースケールに変換します / Resize the image and convert it to grayscale
    resized = cv2.resize(image, (hashSize + 1, hashSize))
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

    # 水平方向のグラデーションを計算します / Compute the horizontal gradient
    diff = gray[:, 1:] > gray[:, :-1]

    # ハッシュ値を生成します / Generate the hash value
    return sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])

def hamming_distance(hash1, hash2):
    # ハミング距離（2つのハッシュ間の差異）を計算します / Calculate the Hamming distance (difference between two hashes)
    return bin(hash1 ^ hash2).count('1')

def main():
    # 引数を解析します / Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, help="処理するディレクトリ / Directory to process")
    parser.add_argument("--save_dir", default="output/", help="出力を保存するディレクトリ / Directory to save the output")
    parser.add_argument("--extension", default="jpg png webp", help="処理するファイル拡張子 / File extensions to process")
    parser.add_argument("--recursive", action='store_true', help="サブディレクトリを再帰的に検索 / Search subdirectories recursively")
    parser.add_argument("--debug", action='store_true', help="実際の画像処理なしでデバッグモードを有効にします / Enable debug mode without actual image processing")
    parser.add_argument("--threshold", type=int, default=5, help="画像類似度の判定のしきい値 / Threshold for image similarity judgement")
    args = parser.parse_args()

    # 出力ディレクトリが存在しない場合は作成します / Create the output directory if it does not exist
    if not os.path.exists(args.save_dir):
        os.makedirs(args.save_dir)

    # 画像ファイルのパスを取得します / Get the paths of the image files
    if args.recursive:
        imagePathList = list(paths.list_images(args.dir))
    else:
        imagePathList = [os.path.join(args.dir, f) for f in os.listdir(args.dir) if f.split('.')[-1] in args.extension.split()]

    # ハッシュ値を格納する辞書 / Dictionary to store hash values
    hashes: Dict[int, List[str]] = {}

    # 画像を処理します / Process images
    for imagePath in tqdm(imagePathList, desc="画像の解析を行っています"):
        # デバッグモードでは、意図したアクションのみを表示します / In debug mode, only display the intended actions
        if args.debug:
            print(f"Debug: 画像を処理する予定です {imagePath}")
            continue

        image = cv2.imread(imagePath)
        h = dhash(image)

        duplicate = False
        for stored_hash in hashes.keys():
            if hamming_distance(h, stored_hash) <= args.threshold:
                print(f"類似画像が検出されました: {imagePath} は無視されます。")
                duplicate = True
                break
        if duplicate:
            continue

        hashes[h] = imagePath

        # 出力ディレクトリにファイルを保存します、ディレクトリ構造を維持します / Save the file in the output directory, maintaining directory structure
        relative_path = os.path.relpath(imagePath, args.dir)
        save_path = os.path.join(args.save_dir, relative_path)
        save_dir = os.path.dirname(save_path)
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        cv2.imwrite(save_path, image)
        print(f"保存完了 {imagePath} へ {save_path}。 / Saved {imagePath} to {save_path}.")
        # デバッグモード時の追加情報表示 / Additional information display in debug mode
        if args.debug:
            print(f"Step2: 類似画像が{len(hashes)}枚見つかりました。")

if __name__ == "__main__":
    main()
