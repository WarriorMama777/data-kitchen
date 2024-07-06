import argparse
import os
import sys
import shutil
import tarfile
import zipfile
import signal
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import psutil

def parse_arguments():
    parser = argparse.ArgumentParser(description="File compression and decompression script")
    parser.add_argument("--dir", nargs="+", required=True, help="Target directory or file(s)")
    parser.add_argument("--dir_save", help="Output directory and filename")
    parser.add_argument("--by_folder", action="store_true", help="Process each folder separately when compressing")
    parser.add_argument("--by_pack", action="store_true", help="Process each archive file separately when decompressing")
    parser.add_argument("--smart_unpack", action="store_true", default=True, help="Smart unpacking")
    parser.add_argument("--format", choices=["zip", "tar", "tar.gz"], default="zip", help="Compression format")
    parser.add_argument("--separate_size", type=str, help="Split size for compression (e.g., '1000MB')")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    parser.add_argument("--threads", type=int, default=0, help="Number of threads (0 for auto)")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--pack", action="store_true", help="Compress files")
    group.add_argument("--unpack", action="store_true", help="Decompress files")
    
    return parser.parse_args()

def get_optimal_thread_count():
    return max(psutil.cpu_count(logical=False), 1)

def human_readable_size(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f}{unit}"
        size_bytes /= 1024.0

def compress_file(file_path, archive_path, archive_format, pbar):
    if archive_format == "zip":
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            arcname = os.path.basename(file_path)
            zipf.write(file_path, arcname)
            pbar.update(os.path.getsize(file_path))
    elif archive_format in ["tar", "tar.gz"]:
        mode = 'w:gz' if archive_format == "tar.gz" else 'w'
        with tarfile.open(archive_path, mode) as tarf:
            arcname = os.path.basename(file_path)
            tarf.add(file_path, arcname)
            pbar.update(os.path.getsize(file_path))

def decompress_file(archive_path, output_dir, smart_unpack, pbar):
    def get_extract_dir_name(archive_name):
        base_name = archive_name
        while True:
            new_base, ext = os.path.splitext(base_name)
            if new_base == base_name:
                break
            base_name = new_base
        return base_name

    try:
        archive_size = os.path.getsize(archive_path)
        extracted_size = 0

        if archive_path.endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zipf:
                if smart_unpack and len(zipf.namelist()) > 1:
                    extract_dir = os.path.join(output_dir, get_extract_dir_name(os.path.basename(archive_path)))
                    os.makedirs(extract_dir, exist_ok=True)
                else:
                    extract_dir = output_dir

                for file in zipf.namelist():
                    zipf.extract(file, extract_dir)
                    extracted_size += zipf.getinfo(file).file_size
                    pbar.update(zipf.getinfo(file).compress_size)

        elif archive_path.endswith(('.tar', '.tar.gz', '.tgz')):
            with tarfile.open(archive_path, 'r:*') as tarf:
                if smart_unpack and len(tarf.getnames()) > 1:
                    extract_dir = os.path.join(output_dir, get_extract_dir_name(os.path.basename(archive_path)))
                    os.makedirs(extract_dir, exist_ok=True)
                else:
                    extract_dir = output_dir

                for member in tarf.getmembers():
                    tarf.extract(member, extract_dir)
                    extracted_size += member.size
                    pbar.update(member.size)

        return f"Decompressed: {archive_path} -> {extract_dir}"
    except Exception as e:
        return f"Error decompressing {archive_path}: {str(e)}"

def process_item(item, args, output_dir, pbar):
    try:
        if os.path.isfile(item):
            output_file = os.path.join(output_dir, f"{os.path.basename(item)}.{args.format}")
            compress_file(item, output_file, args.format, pbar)
        elif os.path.isdir(item):
            output_file = os.path.join(output_dir, f"{os.path.basename(item)}.{args.format}")
            total_size = sum(os.path.getsize(os.path.join(dirpath,filename)) 
                             for dirpath, dirnames, filenames in os.walk(item) 
                             for filename in filenames)
            pbar.total = total_size
            if args.format == "zip":
                with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(item):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, item)
                            zipf.write(file_path, arcname)
                            pbar.update(os.path.getsize(file_path))
            elif args.format in ["tar", "tar.gz"]:
                mode = 'w:gz' if args.format == "tar.gz" else 'w'
                with tarfile.open(output_file, mode) as tarf:
                    for root, dirs, files in os.walk(item):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, item)
                            tarf.add(file_path, arcname)
                            pbar.update(os.path.getsize(file_path))
        return f"Processed: {item} -> {output_file}"
    except Exception as e:
        return f"Error processing {item}: {str(e)}"

def main():
    args = parse_arguments()

    if args.debug:
        print("Debug mode: No actual processing will be done.")
        print(f"Arguments: {args}")
        return

    if args.threads == 0:
        args.threads = get_optimal_thread_count()
    print(f"Using {args.threads} threads")

    if not args.dir_save and len(args.dir) > 1:
        print("Error: --dir_save must be specified when multiple directories are provided.")
        return

    output_dir = args.dir_save if args.dir_save else os.path.dirname(args.dir[0])
    os.makedirs(output_dir, exist_ok=True)

    items_to_process = []
    for path in args.dir:
        if os.path.isfile(path):
            items_to_process.append(path)
        elif os.path.isdir(path):
            if args.pack and args.by_folder:
                items_to_process.extend([os.path.join(path, item) for item in os.listdir(path) if os.path.isdir(os.path.join(path, item))])
            elif args.unpack and args.by_pack:
                items_to_process.extend([os.path.join(path, item) for item in os.listdir(path) if item.endswith(('.zip', '.tar', '.tar.gz', '.tgz'))])
            else:
                items_to_process.append(path)

    total_size = sum(os.path.getsize(item) if os.path.isfile(item) else
                     sum(os.path.getsize(os.path.join(dirpath, filename))
                         for dirpath, dirnames, filenames in os.walk(item)
                         for filename in filenames)
                     for item in items_to_process)

    with tqdm(total=total_size, unit='B', unit_scale=True, desc="Processing") as pbar:
        with ThreadPoolExecutor(max_workers=args.threads) as executor:
            if args.pack:
                futures = [executor.submit(process_item, item, args, output_dir, pbar) for item in items_to_process]
            elif args.unpack:
                futures = [executor.submit(decompress_file, item, output_dir, args.smart_unpack, pbar) for item in items_to_process]
            
            for future in as_completed(futures):
                result = future.result()
                print(result)

def signal_handler(signum, frame):
    print("\nInterrupt received. Cleaning up and exiting...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    main()