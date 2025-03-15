import argparse
import csv
import os
import signal
import sys
from pathlib import Path
import threading
import queue
import multiprocessing
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
import torch
from huggingface_hub import hf_hub_download
from PIL import Image
from tqdm import tqdm

import logging
import traceback
import time
import shutil
import psutil
import random

# ロギングの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 画像サイズの定義
IMAGE_SIZE = 448

# デフォルトのwd14 taggerリポジトリ
DEFAULT_WD14_TAGGER_REPO = "SmilingWolf/wd-v1-4-convnext-tagger-v2"
FILES = ["keras_metadata.pb", "saved_model.pb", "selected_tags.csv"]
FILES_ONNX = ["model.onnx"]
SUB_DIR = "variables"
SUB_DIR_FILES = ["variables.data-00000-of-00001", "variables.index"]
CSV_FILE = FILES[-1]

# 停止フラグ（スレッド間で共有）
stop_processing = False

def signal_handler(signum, frame):
    global stop_processing
    logger.info("Interrupt received, stopping gracefully...")
    stop_processing = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def retry_on_error(max_retries=3, delay=1):
    """
    処理失敗時に自動的にリトライする装飾子
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"Failed after {max_retries} retries: {e}")
                        raise
                    logger.warning(f"Error occurred: {e}. Retrying ({retries}/{max_retries})...")
                    # バックオフ遅延（ランダム要素を含む）
                    sleep_time = delay * (1 + random.random())
                    time.sleep(sleep_time)
        return wrapper
    return decorator

def get_optimal_thread_count():
    """
    システムに最適なスレッド数を計算する
    """
    cpu_count = psutil.cpu_count(logical=True)
    # 物理コア数とハイパースレッディングを考慮
    physical_cores = psutil.cpu_count(logical=False)
    if physical_cores is None:
        physical_cores = cpu_count // 2 or 1
    
    # メモリ使用量も考慮
    memory = psutil.virtual_memory()
    memory_factor = min(1.0, memory.available / (4 * 1024 * 1024 * 1024))  # 4GB以上のメモリがあるほど多くのスレッドを使用
    
    # 最適なスレッド数を計算（CPUを完全に使い切らないようにする）
    optimal_threads = max(1, min(cpu_count, int(physical_cores * 1.5 * memory_factor)))
    
    logger.info(f"System has {cpu_count} logical cores, {physical_cores} physical cores")
    logger.info(f"Determined optimal thread count: {optimal_threads}")
    
    return optimal_threads

@retry_on_error(max_retries=3, delay=1)
def preprocess_image(image):
    image = np.array(image)
    image = image[:, :, ::-1]  # RGB->BGR

    # パディングを正方形に
    size = max(image.shape[0:2])
    pad_x = size - image.shape[1]
    pad_y = size - image.shape[0]
    pad_l = pad_x // 2
    pad_t = pad_y // 2
    image = np.pad(image, ((pad_t, pad_y - pad_t), (pad_l, pad_x - pad_l), (0, 0)), mode="constant", constant_values=255)

    interp = cv2.INTER_AREA if size > IMAGE_SIZE else cv2.INTER_LANCZOS4
    image = cv2.resize(image, (IMAGE_SIZE, IMAGE_SIZE), interpolation=interp)

    image = image.astype(np.float32)
    return image

class ImageLoadingPrepDataset(torch.utils.data.Dataset):
    def __init__(self, image_paths):
        self.images = image_paths

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        img_path = str(self.images[idx])

        try:
            image = Image.open(img_path).convert("RGB")
            image = preprocess_image(image)
        except Exception as e:
            logger.error(f"Could not load image path: {img_path}, error: {e}")
            return None

        return (image, img_path)

def collate_fn_remove_corrupted(batch):
    batch = list(filter(lambda x: x is not None, batch))
    return batch

@retry_on_error(max_retries=3, delay=2)
def load_model(args):
    model_location = os.path.join(args.model_dir, args.repo_id.replace("/", "_"))

    if not os.path.exists(model_location) or args.force_download:
        os.makedirs(args.model_dir, exist_ok=True)
        logger.info(f"Downloading wd14 tagger model from hf_hub. id: {args.repo_id}")
        files = FILES
        if args.onnx:
            files = ["selected_tags.csv"] + FILES_ONNX
        else:
            for file in SUB_DIR_FILES:
                hf_hub_download(
                    args.repo_id,
                    file,
                    subfolder=SUB_DIR,
                    cache_dir=os.path.join(model_location, SUB_DIR),
                    force_download=True,
                    force_filename=file,
                    user_agent="tagger.py/1.0"
                )
        for file in files:
            hf_hub_download(
                args.repo_id, 
                file, 
                cache_dir=model_location, 
                force_download=True, 
                force_filename=file,
                user_agent="tagger.py/1.0"
            )
    else:
        logger.info("Using existing wd14 tagger model")

    if args.onnx:
        import onnx
        import onnxruntime as ort

        onnx_path = f"{model_location}/model.onnx"
        logger.info(f"Loading ONNX model: {onnx_path}")

        if not os.path.exists(onnx_path):
            raise Exception(f"ONNX model not found: {onnx_path}")

        model = onnx.load(onnx_path)
        input_name = model.graph.input[0].name
        
        providers = (
            ["CUDAExecutionProvider"] if "CUDAExecutionProvider" in ort.get_available_providers() else
            ["ROCMExecutionProvider"] if "ROCMExecutionProvider" in ort.get_available_providers() else
            ["CPUExecutionProvider"]
        )
        logger.info(f"Using ONNX providers: {providers}")
        ort_sess = ort.InferenceSession(onnx_path, providers=providers)
        return ort_sess, input_name
    else:
        from tensorflow.keras.models import load_model
        return load_model(f"{model_location}"), None

@retry_on_error(max_retries=3, delay=1)
def load_tags(model_location):
    with open(os.path.join(model_location, CSV_FILE), "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)[1:]  # ヘッダーをスキップ

    rating_tags = [row[1] for row in rows if row[2] == "9"]
    general_tags = [row[1] for row in rows if row[2] == "0"]
    character_tags = [row[1] for row in rows if row[2] == "4"]

    return rating_tags, general_tags, character_tags

def process_images(args, model, input_name, rating_tags, general_tags, character_tags):
    global stop_processing
    
    image_paths = []
    if os.path.isfile(args.dir_image):
        image_paths = [args.dir_image]
    else:
        for root, _, files in os.walk(args.dir_image):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp')):
                    image_paths.append(os.path.join(root, file))
            if not args.recursive:
                break

    logger.info(f"Found {len(image_paths)} images.")

    tag_freq = {}
    results_queue = queue.Queue()
    
    def process_image(image_path):
        if stop_processing:
            return None
        
        try:
            image = Image.open(image_path).convert("RGB")
            processed_image = preprocess_image(image)
            
            if args.onnx:
                probs = model.run(None, {input_name: np.array([processed_image])})[0][0]
            else:
                probs = model(np.array([processed_image]), training=False).numpy()[0]
            
            combined_tags = []
            local_tag_freq = {}
            
            for i, p in enumerate(probs[4:]):
                if i < len(general_tags) and p >= args.general_threshold:
                    tag_name = general_tags[i]
                    if tag_name not in args.undesired_tags:
                        local_tag_freq[tag_name] = local_tag_freq.get(tag_name, 0) + 1
                        combined_tags.append(tag_name)
                elif i >= len(general_tags) and p >= args.character_threshold:
                    tag_name = character_tags[i - len(general_tags)]
                    if tag_name not in args.undesired_tags:
                        local_tag_freq[tag_name] = local_tag_freq.get(tag_name, 0) + 1
                        combined_tags.insert(0, tag_name) if args.character_tags_first else combined_tags.append(tag_name)

            if args.use_rating_tags or args.use_rating_tags_as_last_tag:
                rating_index = probs[:4].argmax()
                found_rating = rating_tags[rating_index]
                if found_rating not in args.undesired_tags:
                    # プレフィックスを追加
                    prefixed_rating = f"rating_{found_rating}"
                    local_tag_freq[prefixed_rating] = local_tag_freq.get(prefixed_rating, 0) + 1
                    combined_tags.insert(0, prefixed_rating) if args.use_rating_tags else combined_tags.append(prefixed_rating)

            if args.always_first_tags:
                for tag in reversed(args.always_first_tags):
                    if tag in combined_tags:
                        combined_tags.remove(tag)
                        combined_tags.insert(0, tag)
            
            # 追加タグの処理
            if args.add_tag:
                add_tags = args.add_tag.split(",")
                # 位置に応じて追加
                if args.add_tag_position == "last":
                    combined_tags.extend(add_tags)
                else:  # "first" または未指定の場合
                    for tag in reversed(add_tags):
                        combined_tags.insert(0, tag)
            
            tag_text = args.caption_separator.join(combined_tags)
            
            return (image_path, tag_text, local_tag_freq)
        
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            if args.debug:
                logger.error(traceback.format_exc())
            return None
    
    # スレッドプールで処理を実行
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = [executor.submit(process_image, path) for path in image_paths]
        
        results = []
        for future in tqdm(futures, desc="Processing images", total=len(image_paths)):
            if stop_processing:
                break
                
            try:
                result = future.result()
                if result is not None:
                    image_path, tag_text, local_tag_freq = result
                    results.append((image_path, tag_text))
                    
                    # タグ頻度をメインのディクショナリに集約
                    for tag, count in local_tag_freq.items():
                        tag_freq[tag] = tag_freq.get(tag, 0) + count
            except Exception as e:
                logger.error(f"Error getting result: {e}")
                if args.debug:
                    logger.error(traceback.format_exc())
    
    if stop_processing:
        logger.info("Processing was interrupted by user.")
    else:
        logger.info(f"Processed {len(results)} images successfully.")
        
    return results

@retry_on_error(max_retries=3, delay=1)
def save_results(args, results):
    if stop_processing:
        return
        
    with tqdm(total=len(results), desc="Saving results") as pbar:
        for image_path, tag_text in results:
            # 入力が単一のファイルかディレクトリかを判断
            if os.path.isfile(args.dir_image):
                relative_path = os.path.basename(image_path)
            else:
                relative_path = os.path.relpath(image_path, args.dir_image)

            # preserve_own_folder処理
            if args.preserve_own_folder:
                own_folder = os.path.basename(os.path.dirname(args.dir_image))
                output_path = os.path.join(args.dir_save, own_folder, relative_path)
            else:
                output_path = os.path.join(args.dir_save, relative_path)

            # preserve_structure処理
            if args.preserve_structure:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
            else:
                output_path = os.path.join(args.dir_save, os.path.basename(relative_path))

            caption_file = os.path.splitext(output_path)[0] + args.caption_extension
            
            if args.append_tags and os.path.exists(caption_file):
                with open(caption_file, "r", encoding="utf-8") as f:
                    existing_content = f.read().strip()
                existing_tags = set(existing_content.split(args.caption_separator))
                new_tags = set(tag_text.split(args.caption_separator))
                combined_tags = existing_tags.union(new_tags)
                tag_text = args.caption_separator.join(sorted(combined_tags))

            os.makedirs(os.path.dirname(caption_file), exist_ok=True)
            with open(caption_file, "w", encoding="utf-8") as f:
                f.write(tag_text + "\n")

            if args.debug:
                logger.info(f"Processed: {image_path}")
                logger.info(f"Tags: {tag_text}")
                
            pbar.update(1)
            
            if stop_processing:
                logger.info("Saving interrupted by user.")
                break

def main():
    parser = argparse.ArgumentParser(description="Image Tagger")
    parser.add_argument("--dir_image", type=str, required=True, help="Directory containing images or a single image file")
    parser.add_argument("--recursive", type=bool, default=True, help="Process subdirectories recursively")
    parser.add_argument("--dir_save", type=str, default="./output", help="Directory to save processed files")
    parser.add_argument("--preserve_own_folder", type=bool, default=True, help="Preserve the original folder structure")
    parser.add_argument("--preserve_structure", type=bool, default=True, help="Preserve the directory structure")
    parser.add_argument("--by_folder", action="store_true", help="Process each folder separately")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--repo_id", type=str, default=DEFAULT_WD14_TAGGER_REPO, help="Hugging Face repository ID for wd14 tagger")
    parser.add_argument("--model_dir", type=str, default="./models", help="Directory to store wd14 tagger model")
    parser.add_argument("--force_download", action="store_true", help="Force download of the model")
    parser.add_argument("--general_threshold", type=float, default=0.35, help="Threshold for general tags")
    parser.add_argument("--character_threshold", type=float, default=0.35, help="Threshold for character tags")
    parser.add_argument("--caption_extension", type=str, default=".txt", help="Extension for caption files")
    parser.add_argument("--use_rating_tags", action="store_true", help="Use rating tags")
    parser.add_argument("--use_rating_tags_as_last_tag", action="store_true", help="Use rating tags as last tag")
    parser.add_argument("--character_tags_first", action="store_true", help="Put character tags first")
    parser.add_argument("--caption_separator", type=str, default=", ", help="Separator for caption tags")
    parser.add_argument("--undesired_tags", type=str, default="", help="Comma-separated list of undesired tags")
    parser.add_argument("--always_first_tags", type=str, help="Comma-separated list of tags to always put first")
    parser.add_argument("--append_tags", action="store_true", help="Append new tags to existing caption files")
    parser.add_argument("--onnx", type=bool, default=True, help="Use ONNX runtime")
    parser.add_argument("--batch_size", type=int, default=1, help="Batch size for processing")
    parser.add_argument("--mem_cache", type=bool, default=True, help="Use memory cache")
    # 新しい引数の追加
    parser.add_argument("--add_tag", type=str, help="Additional tags to add to all images (comma-separated)")
    parser.add_argument("--add_tag_position", type=str, default="first", choices=["first", "last"], 
                        help="Position to add the additional tags: 'first' (at the beginning) or 'last' (at the end)")
    parser.add_argument("--threads", type=int, help="Number of threads to use for processing (default: auto-detected)")

    args = parser.parse_args()

    # スレッド数自動設定
    if args.threads is None or args.threads <= 0:
        args.threads = get_optimal_thread_count()
    else:
        logger.info(f"Using user-specified thread count: {args.threads}")

    args.undesired_tags = set(args.undesired_tags.split(",")) if args.undesired_tags else set()
    args.always_first_tags = args.always_first_tags.split(",") if args.always_first_tags else []

    try:
        os.makedirs(args.dir_save, exist_ok=True)

        logger.info(f"Loading model: {args.repo_id}")
        model, input_name = load_model(args)
        
        logger.info("Loading tags...")
        rating_tags, general_tags, character_tags = load_tags(os.path.join(args.model_dir, args.repo_id.replace("/", "_")))
        
        logger.info("Starting image processing...")
        results = process_images(args, model, input_name, rating_tags, general_tags, character_tags)

        if not stop_processing:
            if args.mem_cache:
                save_results(args, results)
            else:
                for result in results:
                    if stop_processing:
                        break
                    save_results(args, [result])

        logger.info("Processing completed." if not stop_processing else "Processing was interrupted.")
        
    except KeyboardInterrupt:
        logger.info("Processing manually interrupted.")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)