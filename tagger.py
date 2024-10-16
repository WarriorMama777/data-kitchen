import argparse
import csv
import os
import signal
import sys
from pathlib import Path
import threading
import queue
import multiprocessing

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

def signal_handler(signum, frame):
    logger.info("Interrupt received, stopping...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

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
                )
        for file in files:
            hf_hub_download(args.repo_id, file, cache_dir=model_location, force_download=True, force_filename=file)
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
        ort_sess = ort.InferenceSession(onnx_path, providers=providers)
        return ort_sess, input_name
    else:
        from tensorflow.keras.models import load_model
        return load_model(f"{model_location}"), None

def load_tags(model_location):
    with open(os.path.join(model_location, CSV_FILE), "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)[1:]  # ヘッダーをスキップ

    rating_tags = [row[1] for row in rows if row[2] == "9"]
    general_tags = [row[1] for row in rows if row[2] == "0"]
    character_tags = [row[1] for row in rows if row[2] == "4"]

    return rating_tags, general_tags, character_tags

def process_images(args, model, input_name, rating_tags, general_tags, character_tags):
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
    results = []

    def process_batch(batch):
        nonlocal tag_freq, results
        imgs = np.array([im for _, im in batch])

        if args.onnx:
            probs = model.run(None, {input_name: imgs})[0]
        else:
            probs = model(imgs, training=False).numpy()

        for (image_path, _), prob in zip(batch, probs):
            combined_tags = []
            
            for i, p in enumerate(prob[4:]):
                if i < len(general_tags) and p >= args.general_threshold:
                    tag_name = general_tags[i]
                    if tag_name not in args.undesired_tags:
                        tag_freq[tag_name] = tag_freq.get(tag_name, 0) + 1
                        combined_tags.append(tag_name)
                elif i >= len(general_tags) and p >= args.character_threshold:
                    tag_name = character_tags[i - len(general_tags)]
                    if tag_name not in args.undesired_tags:
                        tag_freq[tag_name] = tag_freq.get(tag_name, 0) + 1
                        combined_tags.insert(0, tag_name) if args.character_tags_first else combined_tags.append(tag_name)

            if args.use_rating_tags or args.use_rating_tags_as_last_tag:
                rating_index = prob[:4].argmax()
                found_rating = rating_tags[rating_index]
                if found_rating not in args.undesired_tags:
                    tag_freq[found_rating] = tag_freq.get(found_rating, 0) + 1
                    combined_tags.insert(0, found_rating) if args.use_rating_tags else combined_tags.append(found_rating)

            if args.always_first_tags:
                for tag in reversed(args.always_first_tags):
                    if tag in combined_tags:
                        combined_tags.remove(tag)
                        combined_tags.insert(0, tag)

            tag_text = args.caption_separator.join(combined_tags)
            results.append((image_path, tag_text))

    batch_size = args.batch_size
    for i in tqdm(range(0, len(image_paths), batch_size), desc="Processing images"):
        batch = [(path, preprocess_image(Image.open(path).convert("RGB"))) for path in image_paths[i:i+batch_size]]
        process_batch(batch)

    return results

def save_results(args, results):
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
    parser.add_argument("--threads", type=int, default=multiprocessing.cpu_count(), help="Number of threads to use")

    args = parser.parse_args()

    args.undesired_tags = set(args.undesired_tags.split(",")) if args.undesired_tags else set()
    args.always_first_tags = args.always_first_tags.split(",") if args.always_first_tags else []

    os.makedirs(args.dir_save, exist_ok=True)

    model, input_name = load_model(args)
    rating_tags, general_tags, character_tags = load_tags(os.path.join(args.model_dir, args.repo_id.replace("/", "_")))

    results = process_images(args, model, input_name, rating_tags, general_tags, character_tags)

    if args.mem_cache:
        save_results(args, results)
    else:
        for result in results:
            save_results(args, [result])

    logger.info("Processing completed.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
