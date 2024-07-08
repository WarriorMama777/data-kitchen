import os
import glob
import argparse
import signal
import time
from tqdm import tqdm
from huggingface_hub import HfApi, Repository, create_repo
import multiprocessing
import threading
import queue
import io
import sys

# グローバル変数for safe exit
exit_event = threading.Event()

def signal_handler(signum, frame):
    print("\nスクリプトを安全に停止しています...")
    exit_event.set()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def create_repository_if_not_exists(repo_id, repo_type, token, private):
    api = HfApi()
    try:
        api.repo_info(repo_id=repo_id, repo_type=repo_type, token=token)
    except Exception:
        print(f"リポジトリ {repo_id} が存在しません。新しく作成します。")
        create_repo(repo_id=repo_id, repo_type=repo_type, token=token, private=private)

def upload_file(file_path, repo_id, repo_type, token, revision, create_pr, preserve_structure, base_dir, preserve_own_folder):
    api = HfApi()
    max_retries = 3
    for attempt in range(max_retries):
        if exit_event.is_set():
            return False
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            buffer = io.BytesIO(content)
            
            if preserve_structure:
                rel_path = os.path.relpath(file_path, base_dir)
                if preserve_own_folder:
                    base_folder_name = os.path.basename(base_dir)
                    rel_path = os.path.join(base_folder_name, rel_path)
            else:
                rel_path = os.path.basename(file_path)
            
            api.upload_file(
                path_or_fileobj=buffer,
                path_in_repo=rel_path,
                repo_id=repo_id,
                repo_type=repo_type,
                token=token,
                revision=revision,
                create_pr=create_pr
            )
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"アップロード中にエラーが発生しました: {e}. 再試行中...")
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                print(f"ファイルのアップロードに失敗しました: {file_path}")
                return False

def download_file(file_path, local_dir, repo_id, repo_type, token, revision, preserve_structure, preserve_own_folder):
    api = HfApi()
    max_retries = 3
    for attempt in range(max_retries):
        if exit_event.is_set():
            return False
        try:
            if preserve_structure:
                if preserve_own_folder:
                    save_path = os.path.join(local_dir, repo_id.split('/')[-1], file_path)
                else:
                    save_path = os.path.join(local_dir, file_path)
            else:
                save_path = os.path.join(local_dir, os.path.basename(file_path))
            
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            api.hf_hub_download(
                repo_id=repo_id,
                filename=file_path,
                repo_type=repo_type,
                token=token,
                revision=revision,
                local_dir=os.path.dirname(save_path)
            )
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"ダウンロード中にエラーが発生しました: {e}. 再試行中...")
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                print(f"ファイルのダウンロードに失敗しました: {file_path}")
                return False

def worker(queue, args):
    while not exit_event.is_set():
        try:
            item = queue.get(timeout=1)
            if item is None:
                break
            if args.upload:
                upload_file(item, args.repo_id, args.repo_type, args.token, args.revision, args.create_pr, args.preserve_structure, args.dir[0], args.preserve_own_folder)
            elif args.download:
                download_file(item, args.dir_save, args.repo_id, args.repo_type, args.token, args.revision, args.preserve_structure, args.preserve_own_folder)
            queue.task_done()
        except queue.Empty:
            continue

def main():
    parser = argparse.ArgumentParser(description="Hugging Face Upload/Download Utility")
    parser.add_argument("--upload", action="store_true", help="Upload mode")
    parser.add_argument("--download", action="store_true", help="Download mode")
    parser.add_argument("--repo-id", required=True, help="Repository ID")
    parser.add_argument("--repo-type", choices=["model", "dataset", "space"], default="dataset", help="Repository type")
    parser.add_argument("--dir", nargs="+", help="Directories or files to process")
    parser.add_argument("--dir_save", default="./output", help="Directory to save downloaded files")
    parser.add_argument("--extension", nargs="+", help="File extensions to process")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    parser.add_argument("--revision", default="main", help="Git revision to push to")
    parser.add_argument("--private", action="store_true", help="Create a private repository")
    parser.add_argument("--include", nargs="*", help="Glob patterns to include files")
    parser.add_argument("--exclude", nargs="*", help="Glob patterns to exclude files")
    parser.add_argument("--delete", nargs="*", help="Glob patterns for files to delete")
    parser.add_argument("--commit-message", default="Update files", help="Commit message")
    parser.add_argument("--commit-description", help="Commit description")
    parser.add_argument("--create-pr", action="store_true", help="Create a pull request")
    parser.add_argument("--every", type=int, help="Commit every N minutes")
    parser.add_argument("--token", required=True, help="Hugging Face user access token")
    parser.add_argument("--quiet", action="store_true", help="Quiet mode")
    parser.add_argument("--threads", type=int, default=multiprocessing.cpu_count(), help="Number of threads to use")
    parser.add_argument("--recursive", action="store_true", default=True, help="Process subdirectories recursively")
    parser.add_argument("--preserve_structure", action="store_true", default=True, help="Preserve directory structure")
    parser.add_argument("--preserve_own_folder", action="store_true", help="Preserve own folder name")
    
    args = parser.parse_args()

    if args.upload and args.download:
        raise ValueError("アップロードとダウンロードを同時に指定することはできません。")

    if not (args.upload or args.download):
        raise ValueError("アップロードまたはダウンロードのどちらかを指定してください。")

    if args.upload and not args.dir:
        raise ValueError("アップロードモードでは --dir オプションが必要です。")

    if args.download and not args.dir_save:
        raise ValueError("ダウンロードモードでは --dir_save オプションが必要です。")

    os.makedirs(args.dir_save, exist_ok=True)

    # リポジトリが存在しない場合は作成
    if args.upload:
        create_repository_if_not_exists(args.repo_id, args.repo_type, args.token, args.private)

    files_to_process = []
    if args.upload:
        for path in args.dir:
            if os.path.isfile(path):
                files_to_process.append(path)
            elif os.path.isdir(path):
                if args.recursive:
                    for root, _, files in os.walk(path):
                        for file in files:
                            if args.extension:
                                if any(file.endswith(ext) for ext in args.extension):
                                    files_to_process.append(os.path.join(root, file))
                            else:
                                files_to_process.append(os.path.join(root, file))
                else:
                    for file in os.listdir(path):
                        file_path = os.path.join(path, file)
                        if os.path.isfile(file_path):
                            if args.extension:
                                if any(file.endswith(ext) for ext in args.extension):
                                    files_to_process.append(file_path)
                            else:
                                files_to_process.append(file_path)
    elif args.download:
        api = HfApi()
        files_info = api.list_repo_files(args.repo_id, repo_type=args.repo_type, revision=args.revision)
        files_to_process = [file for file in files_info if not file.endswith('/')]

    if args.include:
        files_to_process = [f for f in files_to_process if any(glob.fnmatch.fnmatch(f, pattern) for pattern in args.include)]
    if args.exclude:
        files_to_process = [f for f in files_to_process if not any(glob.fnmatch.fnmatch(f, pattern) for pattern in args.exclude)]

    if args.debug:
        print("デバッグモード:")
        print(f"処理対象ファイル: {files_to_process}")
        return

    q = queue.Queue()
    threads = []
    for _ in range(min(args.threads, len(files_to_process))):
        t = threading.Thread(target=worker, args=(q, args))
        t.start()
        threads.append(t)

    with tqdm(total=len(files_to_process), unit="file", disable=args.quiet) as pbar:
        for file in files_to_process:
            q.put(file)
            pbar.update(1)

    q.join()

    for _ in range(args.threads):
        q.put(None)
    for t in threads:
        t.join()

    if exit_event.is_set():
        print("スクリプトは安全に停止されました。")
    else:
        print("処理が完了しました。")

if __name__ == "__main__":
    main()