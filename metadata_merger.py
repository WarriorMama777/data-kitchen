import argparse
import json
import logging
from pathlib import Path
import os

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def glob_images_pathlib(directory, recursive):
    if recursive:
        return list(directory.rglob('*.*'))
    else:
        return list(directory.glob('*.*'))

def choose_key():
    print("メタデータに保存しようとしているファイルを選択 / Select the file you want to save to metadata.:")
    print("1: tags")
    print("2: caption")
    choice = input("選択肢（1または2）を入力してEnterを押してください / Please enter your choice (1 or 2) and press Enter: ")
    if choice == '1':
        return 'tags'
    elif choice == '2':
        return 'caption'
    else:
        print("無効な入力です。'tags'をデフォルトとして使用します。 / Invalid input. Use 'tags' as default")
        return 'tags'

def main(args):
    assert not args.recursive or (args.recursive and args.full_path), "recursive requires full_path / recursiveはfull_pathと同時に指定してください"

    # ユーザーにキーを選択させる
    chosen_key = choose_key()

    train_data_dir_path = Path(args.train_data_dir)
    image_paths = glob_images_pathlib(train_data_dir_path, args.recursive)
    logger.info(f"found {len(image_paths)} images.")
    
    if args.in_json is None and Path(args.out_json).is_file():
        args.in_json = args.out_json
    
    if args.in_json is not None:
        logger.info(f"loading existing metadata: {args.in_json}")
        try:  # ここから追加
            with open(args.in_json, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except json.decoder.JSONDecodeError:
            logger.error("JSONファイルが空または不正なフォーマットです。新しいメタデータファイルが作成されます。")
            metadata = {}  # ここまで追加
        logger.warning("tags data for existing images will be overwritten / 既存の画像のタグは上書きされます")
    else:
        logger.info("new metadata will be created / 新しいメタデータファイルが作成されます")
        metadata = {}
    
    logger.info("merge tags to metadata json.")
    for image_path in image_paths:
        tags_path = image_path.with_suffix(args.caption_extension)
        if tags_path.exists():
            with open(tags_path, 'r', encoding='utf-8') as f:
                tags = f.read().strip()
            
            image_key = str(image_path) if args.full_path else image_path.stem
            if image_key not in metadata:
                metadata[image_key] = {}
            
            # ユーザーが選択したキーを使用してメタデータに追加
            metadata[image_key][chosen_key] = tags
            if args.debug:
                logger.info(f"{image_key} {tags}")
    
    # metadataを書き出して終わり
    logger.info(f"writing metadata: {args.out_json}")
    with open(args.out_json, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info("done!")

def setup_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("train_data_dir", type=str, help="directory for train images / 学習画像データのディレクトリ")
    parser.add_argument("out_json", type=str, help="metadata file to output / メタデータファイル書き出し先")
    parser.add_argument("--in_json", type=str, help="metadata file to input (if omitted and out_json exists, existing out_json is read) / 読み込むメタデータファイル（省略時、out_jsonが存在すればそれを読み込む）")
    parser.add_argument("--full_path", action="store_true", help="use full path as image-key in metadata (supports multiple directories) / メタデータで画像キーをフルパスにする（複数の学習画像ディレクトリに対応）")
    parser.add_argument("--recursive", action="store_true", help="recursively look for training tags in all child folders of train_data_dir / train_data_dirのすべての子フォルダにある学習タグを再帰的に探す")
    parser.add_argument("--caption_extension", type=str, default=".txt", help="extension of caption (tag) file / 読み込むキャプション（タグ）ファイルの拡張子")
    parser.add_argument("--debug", action="store_true", help="debug mode, print tags")
    return parser

if __name__ == '__main__':
    parser = setup_parser()
    args = parser.parse_args()
    main(args)
