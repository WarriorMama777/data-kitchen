import os
import sys
import signal
from wand.image import Image
from argparse import ArgumentParser
import concurrent.futures
import multiprocessing
from tqdm import tqdm

# Ctrl+Cでの終了を処理
def signal_handler(sig, frame):
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# 引数を処理
parser = ArgumentParser(description="Image processing script.")
parser.add_argument("--dir", required=True, help="Directory of images to process.")
parser.add_argument("--save_dir", default="output/", help="Directory to save processed images.")
parser.add_argument("--extension", nargs="+", help="File extensions to process.")
parser.add_argument("--recursive", action="store_true", help="Process images in subdirectories.")
parser.add_argument("--background", help="Background color code.")
parser.add_argument("--resize", type=int, help="Resize images to this size on the longest side.")
parser.add_argument("--format", help="Format to convert images to.")
parser.add_argument("--quality", type=int, help="Quality of the output image.")
parser.add_argument("--debug", action="store_true", help="Run in debug mode without actual processing.")
parser.add_argument("--preserve_own_folder", action="store_true", help="Preserve the original directory's name.")
parser.add_argument("--preserve_structure", action="store_true", help="Preserve the directory structure.")
parser.add_argument("--gc_disable", action="store_true", help="Disable garbage collection.")
parser.add_argument("--by_folder", action="store_true", help="Process each folder separately.")
parser.add_argument("--mem_cache", default="ON", choices=["ON", "OFF"], help="Toggle memory caching.")
parser.add_argument("--threads", type=int, default=multiprocessing.cpu_count(), help="Number of threads to use.")

args = parser.parse_args()

if args.gc_disable:
    import gc
    gc.disable()

# ディレクトリが存在しない場合は作成
if not os.path.exists(args.save_dir):
    os.makedirs(args.save_dir)

# 処理するファイルのリストを取得
def get_files_to_process(directory, extensions, recursive):
    files_to_process = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                files_to_process.append(os.path.join(root, file))
        if not recursive:
            break
    return files_to_process

# 画像処理関数
def process_image(file_path):
    try:
        with Image(filename=file_path) as img:
            if args.background:
                img.background_color = args.background
            if args.resize:
                img.transform(resize=f"{args.resize}x{args.resize}>")
            if args.format:
                img.format = args.format
            if args.quality:
                img.compression_quality = args.quality

            # 出力パスの生成
            relative_path = os.path.relpath(file_path, args.dir)
            if args.preserve_structure or args.preserve_own_folder:
                output_path = os.path.join(args.save_dir, relative_path)
            else:
                output_path = os.path.join(args.save_dir, os.path.basename(file_path))

            if args.format:
                output_path = os.path.splitext(output_path)[0] + f".{args.format}"

            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            if not args.debug:
                img.save(filename=output_path)

            return file_path, True
    except Exception as e:
        return file_path, False

# メイン処理
def main():
    files_to_process = get_files_to_process(args.dir, args.extension, args.recursive)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
        tasks = [executor.submit(process_image, file) for file in files_to_process]

        for future in tqdm(concurrent.futures.as_completed(tasks), total=len(tasks), desc="Processing Images"):
            file, success = future.result()
            if args.debug:
                print(f"Processed {file}: {'Success' if success else 'Failed'}")

if __name__ == "__main__":
    main()
