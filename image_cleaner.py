import os
import argparse
from imutils import paths
import cv2
from typing import List, Dict

def dhash(image, hashSize=8):
    # イメージをリサイズし、灰色に変換
    resized = cv2.resize(image, (hashSize + 1, hashSize))
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

    # 水平方向の勾配を計算
    diff = gray[:, 1:] > gray[:, :-1]

    # ハッシュ値を生成
    return sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])

def main():
    # 引数を解析
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, help="処理対象ディレクトリ")
    parser.add_argument("--save_dir", default="output/", help="出力ディレクトリ")
    parser.add_argument("--extension", default="jpg png webp", help="処理対象となるファイルの拡張子")
    parser.add_argument("--recursive", action='store_true', help="サブディレクトリも探索する")
    args = parser.parse_args()

    # 出力ディレクトリがなければ作成
    if not os.path.exists(args.save_dir):
        os.makedirs(args.save_dir)

    # 画像ファイルのパスを取得
    if args.recursive:
        imagePathList = list(paths.list_images(args.dir))
    else:
        imagePathList = [os.path.join(args.dir, f) for f in os.listdir(args.dir) if f.split('.')[-1] in args.extension.split()]

    # ハッシュ値を格納する辞書
    hashes: Dict[int, List[str]] = {}

    # 画像を解析
    for imagePath in imagePathList:
        # 画像を読み込む
        image = cv2.imread(imagePath)
        # ハッシュを計算
        h = dhash(image)

        # 既存のハッシュ値と比較
        if h in hashes:
            print(f"類似画像を検出: {imagePath} は削除されます。")
            continue
        else:
            hashes[h] = imagePath

            # ファイルを出力ディレクトリに保存（ディレクトリ構造を維持）
            relative_path = os.path.relpath(imagePath, args.dir)
            save_path = os.path.join(args.save_dir, relative_path)
            save_dir = os.path.dirname(save_path)
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            cv2.imwrite(save_path, image)
            print(f"{imagePath} を {save_path} に保存しました。")

if __name__ == "__main__":
    main()
