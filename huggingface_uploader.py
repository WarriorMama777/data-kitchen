import argparse
import os
import requests
import shutil
import tempfile
import threading
import signal
import time
from huggingface_hub import HfApi, HfFolder, Repository
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Signal handling for safe termination
def signal_handler(sig, frame):
    print("\nTerminating the process safely...")
    exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Function to upload files
def upload_file(api, repo_id, filepath, repo_type, token, preserve_structure, preserve_own_folder, base_dir, debug, pbar, retries=10, backoff_factor=2):
    relative_path = os.path.relpath(filepath, base_dir) if preserve_structure else os.path.basename(filepath)
    if preserve_own_folder:
        repo_path = os.path.join(os.path.basename(base_dir), relative_path)
    else:
        repo_path = relative_path
    if debug:
        print(f"Debug: Uploading {repo_path}")
    else:
        retry_strategy = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session = requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        with open(filepath, "rb") as f:
            for attempt in range(retries):
                try:
                    api.upload_file(
                        path_or_fileobj=f,
                        path_in_repo=repo_path.replace("\\", "/"),
                        repo_id=repo_id,
                        repo_type=repo_type,
                        token=token,
                        commit_message=f"Upload {repo_path}"
                    )
                    break
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code in [429, 504]:
                        wait_time = backoff_factor * (2 ** attempt)
                        print(f"Rate limit exceeded or timeout. Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        raise e
    pbar.update(1)

# Function to process directories
def process_directory(api, repo_id, base_dir, extensions, repo_type, token, recursive, preserve_structure, preserve_own_folder, by_file, debug, threads):
    file_paths = []
    for root, _, files in os.walk(base_dir):
        for file in files:
            if not extensions or any(file.endswith(ext) for ext in extensions):
                file_paths.append(os.path.join(root, file))
        if not recursive:
            break

    with tqdm(total=len(file_paths), desc="Uploading files") as pbar:
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = []
            for file_path in file_paths:
                futures.append(executor.submit(upload_file, api, repo_id, file_path, repo_type, token, preserve_structure, preserve_own_folder, base_dir, debug, pbar))

            for future in as_completed(futures):
                future.result()

# Function to create repository if not exists
def create_repo(api, repo_id, repo_type, token, private):
    try:
        api.create_repo(repo_id, repo_type=repo_type, token=token, private=private)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 409:
            print(f"Repository {repo_id} already exists.")
        else:
            raise e

# Main function to handle arguments and initiate processing
def main():
    parser = argparse.ArgumentParser(description="Upload files to Hugging Face repository.")
    parser.add_argument("--repo-id", required=True, help="Repository ID")
    parser.add_argument("--repo-type", choices=["model", "dataset", "space"], required=True, help="Repository type")
    parser.add_argument("--dir", nargs="+", required=True, help="Directories or files to upload")
    parser.add_argument("--extension", nargs="*", help="File extensions to include in the upload")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--recursive", type=bool, default=True, help="Recursively process directories")
    parser.add_argument("--preserve_structure", type=bool, default=True, help="Preserve directory structure")
    parser.add_argument("--preserve_own_folder", type=bool, default=False, help="Preserve own folder structure")
    parser.add_argument("--by_file", action="store_true", help="Upload files one by one")
    parser.add_argument("--private", action="store_true", help="Create private repository if not exists")
    parser.add_argument("--token", required=True, help="User access token")
    parser.add_argument("--threads", type=int, default=os.cpu_count(), help="Number of threads to use")

    args = parser.parse_args()

    api = HfApi()
    token = HfFolder.get_token() if args.token is None else args.token

    create_repo(api, args.repo_id, args.repo_type, token, args.private)

    for path in args.dir:
        if os.path.isdir(path):
            process_directory(api, args.repo_id, path, args.extension, args.repo_type, token, args.recursive, args.preserve_structure, args.preserve_own_folder, args.by_file, args.debug, args.threads)
        elif os.path.isfile(path):
            with tqdm(total=1, desc="Uploading file") as pbar:
                upload_file(api, args.repo_id, path, args.repo_type, token, args.preserve_structure, args.preserve_own_folder, os.path.dirname(path), args.debug, pbar)
        else:
            print(f"Path {path} does not exist.")

if __name__ == "__main__":
    main()
