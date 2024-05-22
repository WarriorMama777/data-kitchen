import argparse
from pathlib import Path
import shutil
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed
import time

def try_operation(src_path, dest_path, action, retries=3, delay=1):
    for attempt in range(retries):
        try:
            if action == "copy":
                shutil.copy2(src_path, dest_path)
            elif action == "cut":
                shutil.move(src_path, dest_path)
            return True
        except Exception as e:
            print(f"エラー: {e} リトライします... ({attempt+1}/{retries})")
            time.sleep(delay)
    return False

def process_file(args):
    src_path, dest_path, action, debug_mode = args
    if debug_mode:
        operation = "コピー" if action == "copy" else "切り取り"
        print(f"[デバッグ] {operation}: {src_path} -> {dest_path}")
    else:
        return try_operation(src_path, dest_path, action)

def organize_files(src_dir, dest_dir, extensions, file_name, preserve_structure, preserve_own_folder, action, debug_mode, processes):
    src_dir_path = Path(src_dir)
    dest_dir_path = Path(dest_dir)

    if preserve_own_folder:
        dest_dir_path = dest_dir_path / src_dir_path.name
        if not dest_dir_path.exists():
            dest_dir_path.mkdir(parents=True, exist_ok=True)

    if not src_dir_path.exists():
        print(f"指定されたディレクトリが存在しません: {src_dir}")
        return

    if not dest_dir_path.exists():
        print(f"保存先ディレクトリが存在しません。作成します: {dest_dir}")
        dest_dir_path.mkdir(parents=True, exist_ok=True)

    files_to_process = []

    # ファイルを検索とディレクトリ構造の維持
    pattern = "**/*" if not extensions else f"**/*{extensions}"
    for src_path in src_dir_path.glob(pattern):
        if not src_path.is_file() or (file_name and file_name not in src_path.name):
            continue
        if preserve_structure:
            relative_path = src_path.relative_to(src_dir)
            dest_path = dest_dir_path / relative_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            dest_path = dest_dir_path / src_path.name
        files_to_process.append((src_path, dest_path, action, debug_mode))

    # マルチプロセッシングで処理
    with ProcessPoolExecutor(max_workers=processes) as executor:
        futures = [executor.submit(process_file, args) for args in files_to_process]
        for _ in tqdm(as_completed(futures), total=len(futures), desc="ファイルの整頓中"):
            pass

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
    parser.add_argument("--preserve_own_folder", action="store_true", help="`--dir`で指定されたディレクトリ自体のフォルダを`--save`の場所に作成します")
    parser.add_argument("--debug", action="store_true", help="デバッグ情報を表示します")
    parser.add_argument("--processes", type=int, default=4, help="使用するプロセス数")

    args = parser.parse_args()

    action = "copy" if args.copy else "cut"
    organize_files(args.dir, args.save, args.extensions, args.file_name, args.preserve_structure, args.preserve_own_folder, action, args.debug, args.processes)

if __name__ == "__main__":
    main()
