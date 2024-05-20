import os
import cv2
import signal
import argparse
from tqdm import tqdm
from pathlib import Path
import numpy as np
from skimage.metrics import structural_similarity as ssim

def signal_handler(signal, frame):
    print("処理を中断します...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def parse_args():
    parser = argparse.ArgumentParser(description="指定したディレクトリに含まれる画像を解析し、類似した画像を除去します。")
    parser.add_argument("--dir", required=True, help="処理対象ディレクトリ")
    parser.add_argument("--save_dir", default="output/", help="出力ディレクトリを指定")
    parser.add_argument("--extension", nargs='+', default=["jpg", "png", "webp"], help="処理対象となるファイルの拡張子")
    parser.add_argument("--recursive", action="store_true", help="サブディレクトリを含めて画像を処理する")
    parser.add_argument("--debug", action="store_true", help="デバッグ情報を表示")
    parser.add_argument("--threshold", type=float, default=0.9, help="画像類似度の判定のしきい値")
    parser.add_argument("--mem_cache", default="ON", choices=["ON", "OFF"], help="メモリキャッシュを使用するかどうか")
    args = parser.parse_args()
    
    # --extensionで受け取った文字列を空白で分割してリスト化
    if isinstance(args.extension, list):
        # nargs='+'を使用しているため、単一の引数が複数として解釈されるかのチェック
        if len(args.extension) == 1:
            args.extension = args.extension[0].split()
    else:
        args.extension = args.extension.split()
    
    return args

def find_images(directory, extensions, recursive):
    if recursive:
        return [file for ext in extensions for file in Path(directory).rglob(f"*.{ext}")]
    else:
        return [file for ext in extensions for file in Path(directory).glob(f"*.{ext}")]

def image_similarity(imageA, imageB):
    grayA = cv2.cvtColor(imageA, cv2.COLOR_BGR2GRAY)
    grayB = cv2.cvtColor(imageB, cv2.COLOR_BGR2GRAY)
    score, _ = ssim(grayA, grayB, full=True)
    return score

def main():
    args = parse_args()
    all_images = find_images(args.dir, args.extension, args.recursive)
    if args.debug:
        print(f"処理対象画像数: {len(all_images)}")
    else:
        images_to_save = {}
        for img_path in tqdm(all_images, desc="画像を解析中"):
            try:
                img = cv2.imread(str(img_path))
                if img is None:
                    continue
                similar = False
                for saved_path, saved_img in images_to_save.items():
                    if image_similarity(img, saved_img) > args.threshold:
                        similar = True
                        break
                if not similar:
                    images_to_save[img_path] = img
            except Exception as e:
                print(f"エラー: {e}, ファイル: {img_path}")

        output_dir = Path(args.save_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        for img_path, img in tqdm(images_to_save.items(), desc="画像を保存中"):
            if args.mem_cache == "ON":
                relative_path = img_path.relative_to(Path(args.dir))
                save_path = output_dir / relative_path
                save_path.parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(save_path), img)
            elif args.mem_cache == "OFF":
                print(f"メモリキャッシュが無効に設定されています。処理をスキップします。")

if __name__ == "__main__":
    main()
