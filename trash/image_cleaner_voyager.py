import os
import argparse
import signal
from tqdm import tqdm
from voyager import Voyager

def signal_handler(signal, frame):
    print("\nプログラムが強制終了されました。")
    exit(0)

signal.signal(signal.SIGINT, signal_handler)

def get_args():
    parser = argparse.ArgumentParser(description="画像の類似検索と重複除去")
    parser.add_argument("--dir", required=True, help="処理対象ディレクトリ")
    parser.add_argument("--save_dir", default="output/", help="出力ディレクトリ")
    parser.add_argument("--extension", nargs="+", default=["jpg", "png", "webp"], help="処理対象ファイル拡張子")
    parser.add_argument("--recursive", action="store_true", help="サブディレクトリも探索")
    parser.add_argument("--debug", action="store_true", help="デバッグモード")
    parser.add_argument("--threshold", type=float, default=0.8, help="類似度のしきい値")
    parser.add_argument("--mem_cache", choices=["ON", "OFF"], default="ON", help="メモリキャッシュの有効化")
    return parser.parse_args()

def main():
    args = get_args()
    input_dir = args.dir
    save_dir = args.save_dir
    extensions = args.extension
    recursive = args.recursive
    debug = args.debug
    threshold = args.threshold
    mem_cache = args.mem_cache == "ON"

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    voyager = Voyager()
    image_paths = []
    cached_images = []

    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.split(".")[-1].lower() in extensions:
                image_path = os.path.join(root, file)
                image_paths.append(image_path)

        if not recursive:
            break

    pbar = tqdm(image_paths, unit="image")
    for image_path in pbar:
        pbar.set_description(f"Processing {image_path}")
        try:
            image = voyager.encode(image_path)
            if not debug:
                similar_images = voyager.search(image, threshold=threshold)
                if not similar_images:
                    if mem_cache:
                        cached_images.append(image_path)
                    else:
                        save_path = os.path.join(save_dir, os.path.relpath(image_path, input_dir))
                        os.makedirs(os.path.dirname(save_path), exist_ok=True)
                        with open(save_path, "wb") as f:
                            with open(image_path, "rb") as src:
                                f.write(src.read())
        except Exception as e:
            print(f"Error processing {image_path}: {e}")

    if mem_cache:
        pbar = tqdm(cached_images, unit="image")
        for image_path in pbar:
            pbar.set_description(f"Saving {image_path}")
            save_path = os.path.join(save_dir, os.path.relpath(image_path, input_dir))
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "wb") as f:
                with open(image_path, "rb") as src:
                    f.write(src.read())

if __name__ == "__main__":
    main()
