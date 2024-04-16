import argparse
import os
from pathlib import Path
import shutil
from tqdm import tqdm

def organize_files(src_dir, dest_dir, extensions, file_name, preserve_structure, action, debug_mode):
    if not Path(src_dir).exists():
        print(f"指定されたディレクトリが存在しません: {src_dir}")
        return

    if not Path(dest_dir).exists():
        print(f"保存先ディレクトリが存在しません。作成します: {dest_dir}")
        Path(dest_dir).mkdir(parents=True, exist_ok=True)

    files_to_process = []

    # ファイルを検索
    for root, _, files in os.walk(src_dir):
        for file in files:
            if extensions and not file.endswith(extensions):
                continue
            if file_name and file_name not in file:
                continue
            files_to_process.append((root, file))

    # 処理状況を表示
    for root, file in tqdm(files_to_process, desc="ファイルの整頓中"):
        src_path = Path(root) / file
        if preserve_structure:
            relative_path = src_path.relative_to(src_dir)
            dest_path = Path(dest_dir) / relative_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            dest_path = Path(dest_dir) / file

        if debug_mode:
            operation = "コピー" if action == "copy" else "切り取り"
            print(f"[デバッグ] {operation}: {src_path} -> {dest_path}")
        else:
            if action == "copy":
                shutil.copy2(src_path, dest_path)
            elif action == "cut":
                shutil.move(src_path, dest_path)

def main():
    parser = argparse.ArgumentParser(description="指定したディレクトリ下のファイルを整頓するスクリプト")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--copy", action="store_true", help="ファイルをコピーします")
    group.add_argument("--cut", action="store_true", help="ファイルを切り取ります")
    parser.add_argument("--dir", type=str, required=True, help="処理対象となるディレクトリ")
    parser.add_argument("--extensions", type=str, help="処理対象となるファイルの拡張子")
    parser.add_argument("--file_name", type=str, help="処理対象となるファイル名")
    parser.add_argument("--save", type=str, required=True, help="処理対象ファイルを保存するディレクトリ")
    parser.add_argument("--preserve_structure", action="store_true", help="ディレクトリの構造を保持してファイルを保存します")
    parser.add_argument("--debug", action="store_true", help="デバッグ情報を表示します")

    args = parser.parse_args()

    action = "copy" if args.copy else "cut"
    organize_files(args.dir, args.save, args.extensions, args.file_name, args.preserve_structure, action, args.debug)

if __name__ == "__main__":
    main()
