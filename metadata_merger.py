import argparse
import json
import logging
from pathlib import Path

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def glob_images_pathlib(directory, recursive):
    """指定されたディレクトリから画像のパスを取得する"""
    if recursive:
        return list(directory.rglob('*.*'))
    else:
        return list(directory.glob('*.*'))

def main(args):
    base_dir_path = Path(args.dir_base)
    assert base_dir_path.is_dir(), f"{args.dir_base} does not exist or is not a directory."

    append_data_dir_path = Path(args.dir_append_data)
    assert append_data_dir_path.is_dir(), f"{args.dir_append_data} does not exist or is not a directory."

    if args.dir_json and Path(args.dir_json).is_file():
        with open(args.dir_json, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
    else:
        metadata = {}

    image_paths = glob_images_pathlib(base_dir_path, args.recursive)
    logger.info(f"Found {len(image_paths)} images in base directory.")

    for image_path in image_paths:
        image_key = str(image_path) if args.save_full_path else image_path.name

        # メタデータにキーを追加
        if image_key not in metadata:
            metadata[image_key] = {}

        append_data_path = append_data_dir_path / (image_path.stem + '.txt')
        if append_data_path.exists():
            with open(append_data_path, 'r', encoding='utf-8') as f:
                append_data = f.read().strip()
            metadata[image_key][args.append_data_key] = append_data

    # メタデータをJSONファイルに保存
    dir_save_json_path = Path(args.dir_save_json)
    with open(dir_save_json_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Metadata saved to {args.dir_save_json}")

def setup_parser():
    """コマンドライン引数のパーサーを設定する"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir_base", type=str, required=True, help="Base directory path for root metadata files.")
    parser.add_argument("--dir_append_data", type=str, required=True, help="Directory path for files to be appended to JSON.")
    parser.add_argument("--dir_json", type=str, help="Path to the existing metadata JSON file.")
    parser.add_argument("--dir_save_json", type=str, required=True, help="Path to save the output metadata JSON file.")
    parser.add_argument("--save_full_path", action="store_true", help="Use full path for image keys in the metadata.")
    parser.add_argument("--recursive", action="store_true", help="Recursively search directories for images.")
    parser.add_argument("--debug", action="store_true", help="Debug mode to output tag information.")
    parser.add_argument("--append_data_key", type=str, required=True, help="Key name for data to be appended in the metadata JSON.")
    return parser

if __name__ == '__main__':
    parser = setup_parser()
    args = parser.parse_args()
    main(args)
