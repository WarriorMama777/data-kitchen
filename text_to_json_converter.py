import os
import json
import argparse
from pathlib import Path
import concurrent.futures
from tqdm import tqdm
import signal
import sys
import traceback
import multiprocessing

def setup_argument_parser():
    parser = argparse.ArgumentParser(description="Convert text files to JSON format.")
    parser.add_argument("--dir", type=str, required=True, help="Directory to process or a single file path")
    parser.add_argument("--dir_save", type=str, help="Output directory. Default is next to the processed text file")
    parser.add_argument("--extension", nargs='+', default=['txt'], help="File extensions to process (default: txt)")
    parser.add_argument("--recursive", action="store_true", help="Process subdirectories recursively")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--threads", type=int, default=0, help="Number of threads to use. 0 for auto-detection")
    return parser

def signal_handler(signum, frame):
    print("\nInterrupt received. Cleaning up and exiting...")
    sys.exit(0)

def get_optimal_thread_count():
    return max(1, multiprocessing.cpu_count() - 1)

def process_file(file_path, save_dir, debug=False):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()

        json_content = {"caption": content}

        if debug:
            print(f"Debug: Would process file {file_path}")
            print(f"Debug: JSON content would be: {json_content}")
            return True

        output_path = Path(save_dir) / f"{file_path.stem}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_content, f, ensure_ascii=False, indent=4)

        return True
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        traceback.print_exc()
        return False

def find_files(directory, extensions, recursive):
    if Path(directory).is_file():
        return [Path(directory)] if Path(directory).suffix[1:] in extensions else []

    if recursive:
        return [f for ext in extensions for f in Path(directory).rglob(f"*.{ext}")]
    else:
        return [f for ext in extensions for f in Path(directory).glob(f"*.{ext}")]

def main():
    parser = setup_argument_parser()
    args = parser.parse_args()

    signal.signal(signal.SIGINT, signal_handler)

    if args.threads == 0:
        args.threads = get_optimal_thread_count()

    files = find_files(args.dir, args.extension, args.recursive)

    if args.debug:
        print(f"Debug: Found {len(files)} files to process")
        for file in files:
            print(f"Debug: Would process {file}")
        return

    processed_files = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = []
        for file in files:
            save_dir = args.dir_save if args.dir_save else file.parent
            future = executor.submit(process_file, file, save_dir, args.debug)
            futures.append(future)

        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Processing files"):
            if future.result():
                processed_files.append(future.result())

    print(f"Processed {len(processed_files)} files successfully.")

if __name__ == "__main__":
    main()