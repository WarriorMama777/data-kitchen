import argparse
import os
import sys
import signal
import traceback
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import pydub
from pydub import AudioSegment
import logging
import io
import time

def setup_logging(debug_mode):
    logging.basicConfig(
        level=logging.DEBUG if debug_mode else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def parse_arguments():
    parser = argparse.ArgumentParser(description="Audio file converter")
    parser.add_argument("--dir", required=True, help="Directory or file to process")
    parser.add_argument("--extension", nargs="+", default=["mp3", "wav", "flac", "aac", "ogg"], 
                        help="File extensions to process")
    parser.add_argument("--recursive", action="store_true", default=True, 
                        help="Process subdirectories recursively")
    parser.add_argument("--dir_save", default="./output", help="Output directory")
    parser.add_argument("--preserve_own_folder", action="store_true", default=True, 
                        help="Preserve own folder structure")
    parser.add_argument("--preserve_structure", action="store_true", default=True, 
                        help="Preserve directory structure")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("-f", "--format", default="mp3", help="Output format")
    parser.add_argument("-b", "--bitrate", default="192k", help="Output bitrate")
    parser.add_argument("-c", "--channels", type=int, choices=[1, 2], default=2, 
                        help="Number of channels (1 for mono, 2 for stereo)")
    parser.add_argument("-r", "--rate", type=int, default=44100, help="Sampling rate")
    parser.add_argument("--threads", type=int, default=multiprocessing.cpu_count(), 
                        help="Number of threads to use")
    parser.add_argument("--mem_cache", action="store_true", default=True,
                        help="Use memory cache for converted files")
    parser.add_argument("--max_retries", type=int, default=3,
                        help="Maximum number of retries for failed conversions")
    return parser.parse_args()

def get_audio_files(directory, extensions, recursive):
    audio_files = []
    if os.path.isfile(directory):
        if any(directory.lower().endswith(ext.lower()) for ext in extensions):
            audio_files.append(directory)
    else:
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.lower().endswith(ext.lower()) for ext in extensions):
                    audio_files.append(os.path.join(root, file))
            if not recursive:
                break
    return audio_files

def create_output_directory(output_dir):
    os.makedirs(output_dir, exist_ok=True)

def get_output_path(input_path, args):
    rel_path = os.path.relpath(input_path, args.dir)
    if args.preserve_own_folder:
        rel_path = os.path.join(os.path.basename(args.dir), rel_path)
    if not args.preserve_structure:
        rel_path = os.path.basename(rel_path)
    output_path = os.path.join(args.dir_save, rel_path)
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)
    return os.path.splitext(output_path)[0] + '.' + args.format

def convert_audio(input_path, args):
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(args.channels)
    audio = audio.set_frame_rate(args.rate)
    buffer = io.BytesIO()
    audio.export(buffer, format=args.format, bitrate=args.bitrate)
    return buffer.getvalue()

def process_file(input_path, args):
    output_path = get_output_path(input_path, args)
    if args.debug:
        logging.debug(f"Would convert {input_path} to {output_path}")
        return output_path, None

    for attempt in range(args.max_retries):
        try:
            converted_data = convert_audio(input_path, args)
            return output_path, converted_data
        except Exception as e:
            if attempt < args.max_retries - 1:
                logging.warning(f"Attempt {attempt + 1} failed for {input_path}: {str(e)}. Retrying...")
                time.sleep(1)  # Wait for 1 second before retrying
            else:
                logging.error(f"Failed to convert {input_path} after {args.max_retries} attempts: {str(e)}")
                return output_path, None

def save_converted_files(converted_files):
    for output_path, data in converted_files:
        if data is not None:
            with open(output_path, 'wb') as f:
                f.write(data)
            logging.info(f"Saved converted file: {output_path}")
        else:
            logging.warning(f"Skipped saving file due to conversion failure: {output_path}")

def main():
    args = parse_arguments()
    setup_logging(args.debug)

    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))

    try:
        audio_files = get_audio_files(args.dir, args.extension, args.recursive)
        create_output_directory(args.dir_save)

        converted_files = []
        with ThreadPoolExecutor(max_workers=args.threads) as executor:
            futures = [executor.submit(process_file, file, args) for file in audio_files]
            
            with tqdm(total=len(audio_files), desc="Converting files") as pbar:
                for future in as_completed(futures):
                    pbar.update(1)
                    result = future.result()
                    if result[1] is not None or args.debug:
                        converted_files.append(result)
                    else:
                        logging.warning(f"Failed to convert a file")

        if not args.debug:
            if args.mem_cache:
                logging.info("Saving all converted files...")
                save_converted_files(converted_files)
            else:
                logging.info("Files have been saved during conversion")

        logging.info("Conversion completed successfully")
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        logging.debug(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()