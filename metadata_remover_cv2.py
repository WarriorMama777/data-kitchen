import os
import argparse
import cv2
from concurrent.futures import ThreadPoolExecutor

def remove_exif(file_path, save_path=None):
    try:
        image = cv2.imread(file_path)
        if save_path is not None:
            cv2.imwrite(save_path, image)
        else:
            cv2.imwrite(file_path, image)

        print(f"EXIFデータを削除しました: {file_path}")
    except Exception as e:
        print(f"エラーが発生しました: {e}")

def process_image(args):
    file_path, save_dir = args
    save_path = None
    if save_dir is not None:
        save_path = os.path.join(save_dir, os.path.basename(file_path))
        os.makedirs(save_dir, exist_ok=True)
    remove_exif(file_path, save_path)

def process_directory(directory, remove, save_dir=None, cpu=None):
    if not remove:
        return

    # 画像ファイルのパスをリストアップ
    file_paths = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
                file_path = os.path.join(root, file)
                file_paths.append((file_path, save_dir))

    # マルチスレッディングで画像処理、スレッド数を指定
    with ThreadPoolExecutor(max_workers=cpu) as executor:
        executor.map(process_image, file_paths)

def main():
    parser = argparse.ArgumentParser(description="画像のEXIFメタデータを編集するスクリプト")
    parser.add_argument("--dir", type=str, required=True, help="対象とするディレクトリ")
    parser.add_argument("--remove", action="store_true", help="EXIFを削除")
    parser.add_argument("--save", type=str, help="保存するディレクトリ。指定しない場合、画像は上書きされる")
    parser.add_argument("--cpu", type=int, help="使用するスレッド数。指定しない場合、自動的に決定されます")

    args = parser.parse_args()

    process_directory(args.dir, args.remove, args.save, args.cpu)

if __name__ == "__main__":
    main()
