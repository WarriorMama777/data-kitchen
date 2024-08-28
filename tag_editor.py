import argparse
import os
import re
import signal
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tqdm import tqdm

# Signal handler for graceful termination
def signal_handler(sig, frame):
    print("Script terminated gracefully")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Tag Editor Script for batch processing text files")
    parser.add_argument("--dir", required=True, help="Path to the directory or single file to process")
    parser.add_argument("--save_dir", default="output/", help="Path to the output directory for processed files")
    parser.add_argument("--extension", default="txt", help="File extension to process (e.g., 'txt' or 'json')")
    parser.add_argument("--recursive", action="store_true", help="Process subdirectories recursively")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode (no files will be modified)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging for detailed output")
    parser.add_argument("--del_first", type=int, help="Number of characters to delete from the beginning of each file")
    parser.add_argument("--del_last", type=int, help="Number of characters to delete from the end of each file")
    parser.add_argument("--add_first", help="Text to add at the beginning of each file")
    parser.add_argument("--add_last", help="Text to add at the end of each file")
    parser.add_argument("--add_number_first", action="store_true", help="Add a sequential number at the beginning of each file")
    parser.add_argument("--add_number_last", action="store_true", help="Add a sequential number at the end of each file")
    parser.add_argument("--replace", nargs=2, metavar=('OLD', 'NEW'), help="Replace all occurrences of OLD text with NEW text")
    parser.add_argument("--del_after", help="Delete all text after (and including) the specified text")
    parser.add_argument("--del_before", help="Delete all text before (and including) the specified text")
    parser.add_argument("--add_after", nargs=2, metavar=('TARGET', 'TEXT'), help="Add TEXT after the TARGET text")
    parser.add_argument("--add_before", nargs=2, metavar=('TARGET', 'TEXT'), help="Add TEXT before the TARGET text")
    parser.add_argument("--del_reg", help="Delete all text matching the specified regular expression")
    parser.add_argument("--del_reg_around", help="Keep only the text matching the specified regular expression")
    parser.add_argument("--mem_cache", default="ON", choices=["ON", "OFF"], help="Use memory cache for processing (OFF to disable)")
    parser.add_argument("--threads", type=int, default=os.cpu_count(), help="Number of threads to use for parallel processing")
    
    return parser.parse_args()

def ensure_dir_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)

def process_file(file_path, save_dir, args, file_number):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            if args.verbose:
                print(f"Debug: {file_path} の内容を読み込みました。")

        # content が None でないことを確認
        if content is None:
            print(f"Warning: {file_path} の内容が読み取れませんでした。スキップします。")
            return

        # Perform text manipulations based on arguments
        if args.del_first:
            content = content[args.del_first:]
        if args.del_last:
            content = content[:-args.del_last]
        if args.add_first:
            content = args.add_first + content
        if args.add_last:
            content = content + args.add_last
        if args.add_number_first:
            content = f"{file_number}_" + content
        if args.add_number_last:
            content = content + f"_{file_number}"
        if args.replace:
            content = content.replace(args.replace[0], args.replace[1])
        if args.del_after:
            content = content.split(args.del_after)[0] + args.del_after
        if args.del_before:
            content = args.del_before + content.split(args.del_before)[-1]
        if args.add_after:
            content = content.replace(args.add_after[0], args.add_after[0] + args.add_after[1])
        if args.add_before:
            content = content.replace(args.add_before[0], args.add_before[1] + args.add_before[0])
        if args.del_reg:
            content = re.sub(args.del_reg, '', content)
        if args.del_reg_around:
            match = re.search(args.del_reg_around, content)
            if match:
                content = match.group(0)
        
        save_path = os.path.join(save_dir, os.path.basename(file_path))
        ensure_dir_exists(os.path.dirname(save_path))
        with open(save_path, 'w', encoding='utf-8') as file:
            file.write(content)

    except Exception as e:
        print(f"Error processing file {file_path}: {e}")

def main():
    args = parse_arguments()
    
    target_files = []
    if os.path.isdir(args.dir):
        pattern = f"*.{args.extension}"
        if args.recursive:
            target_files = list(Path(args.dir).rglob(pattern))
        else:
            target_files = list(Path(args.dir).glob(pattern))
    elif os.path.isfile(args.dir) and args.dir.endswith(args.extension):
        target_files = [args.dir]
    else:
        print("Invalid directory or file specified")
        sys.exit(1)
    
    if args.debug:
        print("Debug mode enabled. No files will be modified.")
        for file_number, file_path in enumerate(target_files, start=1):
            print(f"Would process file: {file_path}")
        sys.exit(0)

    ensure_dir_exists(args.save_dir)
    
    if args.mem_cache == "OFF":
        with tqdm(total=len(target_files), desc="Processing files") as pbar:
            with ThreadPoolExecutor(max_workers=args.threads) as executor:
                futures = [executor.submit(process_file, file_path, args.save_dir, args, file_number) for file_number, file_path in enumerate(target_files, start=1)]
                for future in futures:
                    future.result()
                    pbar.update(1)
    else:
        cache = {}
        with tqdm(total=len(target_files), desc="Processing files") as pbar:
            with ThreadPoolExecutor(max_workers=args.threads) as executor:
                futures = {executor.submit(process_file, file_path, args.save_dir, args, file_number): file_path for file_number, file_path in enumerate(target_files, start=1)}
                for future in futures:
                    cache[futures[future]] = future.result()
                    pbar.update(1)
        for file_path, content in cache.items():
            save_path = os.path.join(args.save_dir, os.path.basename(file_path))
            with open(save_path, 'w', encoding='utf-8') as file:
                file.write(content)

if __name__ == "__main__":
    main()
