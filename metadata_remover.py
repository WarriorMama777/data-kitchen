import os
import argparse
from PIL import Image

def remove_exif(file_path, save_path=None):
    try:
        image = Image.open(file_path)
        data = list(image.getdata())
        image_without_exif = Image.new(image.mode, image.size)
        image_without_exif.putdata(data)

        if save_path is not None:
            image_without_exif.save(save_path)
        else:
            image_without_exif.save(file_path)

        print(f"EXIFデータを削除しました: {file_path}")
    except Exception as e:
        print(f"エラーが発生しました: {e}")

def process_directory(directory, remove, save_dir=None):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
                file_path = os.path.join(root, file)
                save_path = None
                if save_dir is not None:
                    save_path = os.path.join(save_dir, file)
                    os.makedirs(save_dir, exist_ok=True)
                if remove:
                    remove_exif(file_path, save_path)

def main():
    parser = argparse.ArgumentParser(description="画像のEXIFメタデータを編集するスクリプト")
    parser.add_argument("--dir", type=str, required=True, help="対象とするディレクトリ")
    parser.add_argument("--remove", action="store_true", help="EXIFを削除")
    parser.add_argument("--save", type=str, help="保存するディレクトリ。指定しない場合、画像は上書きされる")

    args = parser.parse_args()

    process_directory(args.dir, args.remove, args.save)

if __name__ == "__main__":
    main()
