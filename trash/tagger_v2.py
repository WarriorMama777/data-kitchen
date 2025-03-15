import argparse
import csv
import os
import sys
import signal
import time
import multiprocessing
from pathlib import Path
import traceback
import logging

import cv2
import numpy as np
import torch
from huggingface_hub import hf_hub_download
from PIL import Image
from tqdm import tqdm

# 定数
IMAGE_SIZE = 448
DEFAULT_WD14_TAGGER_REPO = "SmilingWolf/wd-v1-4-convnext-tagger-v2"
FILES = ["keras_metadata.pb", "saved_model.pb", "selected_tags.csv"]
FILES_ONNX = ["model.onnx"]
SUB_DIR = "variables"
SUB_DIR_FILES = ["variables.data-00000-of-00001", "variables.index"]
CSV_FILE = FILES[-1]
SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
DEFAULT_THREADS = max(1, multiprocessing.cpu_count() - 1)

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def preprocess_image(image):
    """画像を前処理する"""
    image = np.array(image)
    image = image[:, :, ::-1]  # RGB->BGR

    # pad to square
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
    """画像読み込み・前処理用データセット"""
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
    """破損した例を削除するcollate関数"""
    batch = list(filter(lambda x: x is not None, batch))
    return batch


def ensure_dir(directory):
    """ディレクトリが存在することを確認し、存在しない場合は作成する"""
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    return directory


def get_files_recursively(directory, extensions=None):
    """ディレクトリから再帰的にファイルを取得する"""
    if not extensions:
        extensions = SUPPORTED_EXTENSIONS
    
    all_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.lower().endswith(ext) for ext in extensions):
                all_files.append(os.path.join(root, file))
    return all_files


def get_files_from_directory(directory, recursive=False, extensions=None):
    """ディレクトリからファイルを取得する"""
    if not extensions:
        extensions = SUPPORTED_EXTENSIONS
    
    if os.path.isfile(directory):
        if any(directory.lower().endswith(ext) for ext in extensions):
            return [directory]
        return []
    
    if recursive:
        return get_files_recursively(directory, extensions)
    
    all_files = []
    for item in os.listdir(directory):
        full_path = os.path.join(directory, item)
        if os.path.isfile(full_path) and any(full_path.lower().endswith(ext) for ext in extensions):
            all_files.append(full_path)
    
    return all_files


def get_output_path(input_path, args):
    """入力パスから出力パスを生成する"""
    if not args.dir_save:
        return input_path
    
    input_path = Path(input_path)
    dir_image = Path(args.dir_image)
    
    # 相対パスを求める
    try:
        relative_path = input_path.relative_to(dir_image)
    except ValueError:
        # dir_imageの親ディレクトリからの相対パスを試みる
        try:
            relative_path = input_path.relative_to(dir_image.parent)
            # この場合、dir_imageのフォルダ名を含める
            if args.preserve_own_folder:
                relative_path = Path(dir_image.name) / relative_path
        except ValueError:
            # どちらも失敗した場合は、ファイル名だけを使用
            relative_path = Path(input_path.name)
    
    # 出力パスを構築
    if args.preserve_structure:
        output_path = Path(args.dir_save) / relative_path
    else:
        output_path = Path(args.dir_save) / input_path.name
    
    # 出力ディレクトリが存在することを確認
    ensure_dir(output_path.parent)
    
    return str(output_path)


def process_image_batch(model, batch_images, args, tag_data, file_cache):
    """画像バッチを処理する"""
    rating_tags, general_tags, character_tags = tag_data
    undesired_tags = set(tag.strip() for tag in args.undesired_tags.split(args.caption_separator.strip()) if tag.strip())
    always_first_tags = args.always_first_tags.split(args.caption_separator.strip()) if args.always_first_tags else None

    imgs = np.array([im for _, im in batch_images])

    if args.onnx:
        probs = args.ort_sess.run(None, {args.input_name: imgs})[0]
        probs = probs[:len(batch_images)]
    else:
        probs = model(imgs, training=False)
        probs = probs.numpy()

    tag_freq = {}
    for (image_path, _), prob in zip(batch_images, probs):
        combined_tags = []
        rating_tag_text = ""
        character_tag_text = ""
        general_tag_text = ""

        # 一般タグとキャラクタータグの処理
        for i, p in enumerate(prob[4:]):
            if i < len(general_tags) and p >= args.general_threshold:
                tag_name = general_tags[i]
                if tag_name not in undesired_tags:
                    tag_freq[tag_name] = tag_freq.get(tag_name, 0) + 1
                    general_tag_text += args.caption_separator + tag_name
                    combined_tags.append(tag_name)
            elif i >= len(general_tags) and p >= args.character_threshold:
                tag_name = character_tags[i - len(general_tags)]
                if tag_name not in undesired_tags:
                    tag_freq[tag_name] = tag_freq.get(tag_name, 0) + 1
                    character_tag_text += args.caption_separator + tag_name
                    if args.character_tags_first:
                        combined_tags.insert(0, tag_name)
                    else:
                        combined_tags.append(tag_name)

        # レーティングタグの処理
        if args.use_rating_tags or args.use_rating_tags_as_last_tag:
            ratings_probs = prob[:4]
            rating_index = ratings_probs.argmax()
            found_rating = rating_tags[rating_index]
            
            if args.use_rating_tags:
                # rating_general, rating_sensitive という形式に変換
                rating_prefix = "rating_"
                if not found_rating.startswith(rating_prefix):
                    found_rating = rating_prefix + found_rating

            if found_rating not in undesired_tags:
                tag_freq[found_rating] = tag_freq.get(found_rating, 0) + 1
                rating_tag_text = found_rating
                if args.use_rating_tags:
                    combined_tags.insert(0, found_rating)
                elif args.use_rating_tags_as_last_tag:
                    combined_tags.append(found_rating)

        # 一番最初に置くタグの処理
        if always_first_tags is not None:
            for tag in always_first_tags:
                if tag in combined_tags:
                    combined_tags.remove(tag)
                    combined_tags.insert(0, tag)

        # 追加タグの処理
        if args.add_tag:
            additional_tags = [tag.strip() for tag in args.add_tag.split(args.caption_separator.strip()) if tag.strip()]
            
            # 追加タグの位置に基づいて処理
            if args.add_tag_position == "first":
                # 先頭に追加（リストの先頭から順に挿入するため、逆順で処理）
                for tag in reversed(additional_tags):
                    if tag not in combined_tags:  # 重複を避ける
                        combined_tags.insert(0, tag)
            else:  # "last"
                # 末尾に追加
                for tag in additional_tags:
                    if tag not in combined_tags:  # 重複を避ける
                        combined_tags.append(tag)

        # 先頭のセパレータを取る
        if len(general_tag_text) > 0:
            general_tag_text = general_tag_text[len(args.caption_separator):]
        if len(character_tag_text) > 0:
            character_tag_text = character_tag_text[len(args.caption_separator):]

        # 出力パスを決定
        output_path = get_output_path(image_path, args)
        caption_file = os.path.splitext(output_path)[0] + args.caption_extension

        tag_text = args.caption_separator.join(combined_tags)

        # 既存のタグに追記する場合
        if args.append_tags and os.path.exists(caption_file):
            try:
                with open(caption_file, "rt", encoding="utf-8") as f:
                    existing_content = f.read().strip("\n")
                
                existing_tags = [tag.strip() for tag in existing_content.split(args.caption_separator.strip()) if tag.strip()]
                new_tags = [tag for tag in combined_tags if tag not in existing_tags]
                tag_text = args.caption_separator.join(existing_tags + new_tags)
            except Exception as e:
                logger.error(f"Error reading existing caption file {caption_file}: {e}")

        # メモリキャッシュに保存
        if args.mem_cache:
            file_cache[caption_file] = tag_text + "\n"
        else:
            # 直接ファイルに書き込み
            try:
                os.makedirs(os.path.dirname(caption_file), exist_ok=True)
                with open(caption_file, "wt", encoding="utf-8") as f:
                    f.write(tag_text + "\n")
            except Exception as e:
                logger.error(f"Error writing to caption file {caption_file}: {e}")
                if args.debug:
                    logger.error(traceback.format_exc())

        if args.debug:
            logger.info("")
            logger.info(f"{image_path}:")
            logger.info(f"\tOutput path: {output_path}")
            if args.add_tag:
                logger.info(f"\tAdditional tags: {args.add_tag} (position: {args.add_tag_position})")
            logger.info(f"\tRating tags: {rating_tag_text}")
            logger.info(f"\tCharacter tags: {character_tag_text}")
            logger.info(f"\tGeneral tags: {general_tag_text}")
            logger.info(f"\tFull tag text: {tag_text}")

    return tag_freq


def load_and_prepare_model(args):
    """モデルの読み込みと準備"""
    model_location = os.path.join(args.model_dir, args.repo_id.replace("/", "_"))

    # モデルのダウンロード（必要な場合）
    if not os.path.exists(model_location) or args.force_download:
        os.makedirs(args.model_dir, exist_ok=True)
        logger.info(f"Downloading wd14 tagger model from hf_hub. id: {args.repo_id}")
        
        files = FILES
        if args.onnx:
            files = ["selected_tags.csv"]
            files += FILES_ONNX
        else:
            for file in SUB_DIR_FILES:
                max_retries = 3
                retry_count = 0
                while retry_count < max_retries:
                    try:
                        hf_hub_download(
                            args.repo_id,
                            file,
                            subfolder=SUB_DIR,
                            cache_dir=os.path.join(model_location, SUB_DIR),
                            force_download=True,
                            force_filename=file,
                        )
                        break
                    except Exception as e:
                        retry_count += 1
                        if retry_count == max_retries:
                            logger.error(f"Failed to download {file} after {max_retries} attempts: {e}")
                            raise
                        logger.warning(f"Download attempt {retry_count} for {file} failed: {e}. Retrying...")
                        time.sleep(1)
        
        for file in files:
            max_retries = 3
            retry_count = 0
            while retry_count < max_retries:
                try:
                    hf_hub_download(
                        args.repo_id, 
                        file, 
                        cache_dir=model_location, 
                        force_download=True, 
                        force_filename=file
                    )
                    break
                except Exception as e:
                    retry_count += 1
                    if retry_count == max_retries:
                        logger.error(f"Failed to download {file} after {max_retries} attempts: {e}")
                        raise
                    logger.warning(f"Download attempt {retry_count} for {file} failed: {e}. Retrying...")
                    time.sleep(1)
    else:
        logger.info("Using existing wd14 tagger model")

    # タグデータの読み込み
    tag_data = load_tag_data(model_location, args)

    # モデルの読み込み
    model = None
    if args.onnx:
        import onnx
        import onnxruntime as ort

        onnx_path = f"{model_location}/model.onnx"
        logger.info("Running wd14 tagger with ONNX")
        logger.info(f"Loading ONNX model: {onnx_path}")

        if not os.path.exists(onnx_path):
            raise Exception(
                f"ONNX model not found: {onnx_path}, please redownload the model with --force_download"
            )

        model_data = onnx.load(onnx_path)
        args.input_name = model_data.graph.input[0].name
        try:
            batch_size = model_data.graph.input[0].type.tensor_type.shape.dim[0].dim_value
        except Exception:
            batch_size = model_data.graph.input[0].type.tensor_type.shape.dim[0].dim_param

        if args.batch_size != batch_size and not isinstance(batch_size, str) and batch_size > 0:
            logger.warning(
                f"Batch size {args.batch_size} doesn't match ONNX model batch size {batch_size}, using model batch size {batch_size}"
            )
            args.batch_size = batch_size

        del model_data

        # ONNX RuntimeセッションをGPUまたはCPUに設定
        if "OpenVINOExecutionProvider" in ort.get_available_providers():
            args.ort_sess = ort.InferenceSession(
                onnx_path,
                providers=(["OpenVINOExecutionProvider"]),
                provider_options=[{'device_type': "GPU_FP32"}],
            )
        else:
            args.ort_sess = ort.InferenceSession(
                onnx_path,
                providers=(
                    ["CUDAExecutionProvider"] if "CUDAExecutionProvider" in ort.get_available_providers() else
                    ["ROCMExecutionProvider"] if "ROCMExecutionProvider" in ort.get_available_providers() else
                    ["CPUExecutionProvider"]
                ),
            )
    else:
        from tensorflow.keras.models import load_model as tf_load_model
        model = tf_load_model(f"{model_location}")

    return model, tag_data


def load_tag_data(model_location, args):
    """タグデータの読み込みと前処理"""
    with open(os.path.join(model_location, CSV_FILE), "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        lines = [row for row in reader]
        header = lines[0]  # tag_id,name,category,count
        rows = lines[1:]
    
    assert header[0] == "tag_id" and header[1] == "name" and header[2] == "category", f"Unexpected CSV format: {header}"

    # タグの抽出
    rating_tags = [row[1] for row in rows if row[2] == "9"]
    general_tags = [row[1] for row in rows if row[2] == "0"]
    character_tags = [row[1] for row in rows if row[2] == "4"]

    # キャラクタータグの展開
    if args.character_tag_expand:
        for i, tag in enumerate(character_tags):
            if tag.endswith(")"):
                tags = tag.split("(")
                character_tag = "(".join(tags[:-1])
                if character_tag.endswith("_"):
                    character_tag = character_tag[:-1]
                series_tag = tags[-1].replace(")", "")
                character_tags[i] = character_tag + args.caption_separator + series_tag

    # アンダースコアの置換
    if args.remove_underscore:
        rating_tags = [tag.replace("_", " ") if len(tag) > 3 else tag for tag in rating_tags]
        general_tags = [tag.replace("_", " ") if len(tag) > 3 else tag for tag in general_tags]
        character_tags = [tag.replace("_", " ") if len(tag) > 3 else tag for tag in character_tags]

    # タグの置換
    if args.tag_replacement:
        escaped_tag_replacements = args.tag_replacement.replace("\\,", "@@@@").replace("\\;", "####")
        tag_replacements = escaped_tag_replacements.split(";")
        for tag_replacement in tag_replacements:
            tags = tag_replacement.split(",")  # source, target
            assert len(tags) == 2, f"Tag replacement must be in the format of `source,target`: {args.tag_replacement}"

            source, target = [tag.replace("@@@@", ",").replace("####", ";") for tag in tags]
            logger.info(f"Replacing tag: {source} -> {target}")

            if source in general_tags:
                general_tags[general_tags.index(source)] = target
            elif source in character_tags:
                character_tags[character_tags.index(source)] = target
            elif source in rating_tags:
                rating_tags[rating_tags.index(source)] = target

    return rating_tags, general_tags, character_tags


def write_cached_files(file_cache):
    """キャッシュされたタグをファイルに書き込む"""
    logger.info(f"Writing {len(file_cache)} cached files to disk...")
    for file_path, content in tqdm(file_cache.items(), desc="Writing files"):
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wt", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            logger.error(f"Error writing to file {file_path}: {e}")


def process_directory(directory, model, args, tag_data):
    """ディレクトリ内の画像を処理する"""
    image_paths = get_files_from_directory(directory, args.recursive)
    if not image_paths:
        logger.warning(f"No supported images found in {directory}")
        return None
    
    logger.info(f"Found {len(image_paths)} images in {directory}")
    
    return process_images(image_paths, model, args, tag_data)


def process_images(image_paths, model, args, tag_data):
    """画像のリストを処理する"""
    file_cache = {}
    tag_freq = {}
    
    # DataLoaderを使用するかどうか
    if args.max_data_loader_n_workers is not None and args.max_data_loader_n_workers > 0:
        dataset = ImageLoadingPrepDataset(image_paths)
        data_loader = torch.utils.data.DataLoader(
            dataset,
            batch_size=args.batch_size,
            shuffle=False,
            num_workers=args.max_data_loader_n_workers,
            collate_fn=collate_fn_remove_corrupted,
            drop_last=False,
        )
        
        b_imgs = []
        for data_entry in tqdm(data_loader, desc="Processing images", smoothing=0.0):
            for data in data_entry:
                if data is None:
                    continue
                
                image, image_path = data
                b_imgs.append((image_path, image))
                
                if len(b_imgs) >= args.batch_size:
                    batch_tag_freq = process_image_batch(model, b_imgs, args, tag_data, file_cache)
                    for tag, freq in batch_tag_freq.items():
                        tag_freq[tag] = tag_freq.get(tag, 0) + freq
                    b_imgs = []
        
        # 残りの画像を処理
        if b_imgs:
            batch_tag_freq = process_image_batch(model, b_imgs, args, tag_data, file_cache)
            for tag, freq in batch_tag_freq.items():
                tag_freq[tag] = tag_freq.get(tag, 0) + freq
    else:
        # スレッドを使用してマルチスレッド処理
        from concurrent.futures import ThreadPoolExecutor
        
        def process_image(image_path):
            try:
                image = Image.open(image_path).convert("RGB")
                processed = preprocess_image(image)
                return (image_path, processed)
            except Exception as e:
                logger.error(f"Could not load image path: {image_path}, error: {e}")
                if args.debug:
                    logger.error(traceback.format_exc())
                return None
        
        b_imgs = []
        with ThreadPoolExecutor(max_workers=args.threads) as executor:
            futures = [executor.submit(process_image, img_path) for img_path in image_paths]
            
            for future in tqdm(futures, desc="Processing images", smoothing=0.0):
                try:
                    result = future.result()
                    if result is None:
                        continue
                    
                    b_imgs.append(result)
                    
                    if len(b_imgs) >= args.batch_size:
                        batch_tag_freq = process_image_batch(model, b_imgs, args, tag_data, file_cache)
                        for tag, freq in batch_tag_freq.items():
                            tag_freq[tag] = tag_freq.get(tag, 0) + freq
                        b_imgs = []
                except Exception as e:
                    logger.error(f"Error processing image: {e}")
                    if args.debug:
                        logger.error(traceback.format_exc())
        
        # 残りの画像を処理
        if b_imgs:
            batch_tag_freq = process_image_batch(model, b_imgs, args, tag_data, file_cache)
            for tag, freq in batch_tag_freq.items():
                tag_freq[tag] = tag_freq.get(tag, 0) + freq
    
    # キャッシュしたファイルを書き込む
    if args.mem_cache and file_cache:
        write_cached_files(file_cache)
    
    return tag_freq


def main():
    """メイン関数"""
    parser = setup_parser()
    args = parser.parse_args()
    
    # 引数の後処理
    if args.general_threshold is None:
        args.general_threshold = args.thresh
    if args.character_threshold is None:
        args.character_threshold = args.thresh
    
    # デバッグモードの場合、情報を表示
    if args.debug:
        logger.info("Running in debug mode")
        logger.info(f"Arguments: {args}")
    
    # 出力ディレクトリの作成
    if args.dir_save:
        ensure_dir(args.dir_save)
    
    # モデルの読み込み
    if args.debug:
        logger.info("Loading model...")
    
    try:
        model, tag_data = load_and_prepare_model(args)
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        if args.debug:
            logger.error(traceback.format_exc())
        return 1
    
    # 処理の開始
    start_time = time.time()
    
    # SIGINTハンドラ（Ctrl+C）の設定
    def signal_handler(sig, frame):
        logger.info("\nInterrupted by user. Cleaning up...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # 入力ディレクトリ/ファイルの処理
    tag_freq = {}
    
    try:
        if args.by_folder and os.path.isdir(args.dir_image):
            # フォルダごとに処理
            folders = [f for f in os.listdir(args.dir_image) if os.path.isdir(os.path.join(args.dir_image, f))]
            logger.info(f"Found {len(folders)} folders to process")
            
            for item in folders:
                item_path = os.path.join(args.dir_image, item)
                logger.info(f"Processing folder: {item_path}")
                folder_tag_freq = process_directory(item_path, model, args, tag_data)
                if folder_tag_freq:
                    for tag, freq in folder_tag_freq.items():
                        tag_freq[tag] = tag_freq.get(tag, 0) + freq
        else:
            # 入力パスを直接処理
            if args.debug:
                logger.info(f"Processing input path: {args.dir_image}")
            folder_tag_freq = process_directory(args.dir_image, model, args, tag_data)
            if folder_tag_freq:
                tag_freq = folder_tag_freq
    except Exception as e:
        logger.error(f"Error during processing: {e}")
        if args.debug:
            logger.error(traceback.format_exc())
        return 1
    
    # タグの頻度表示
    if args.frequency_tags and tag_freq:
        sorted_tags = sorted(tag_freq.items(), key=lambda x: x[1], reverse=True)
        logger.info("Tag frequencies:")
        for tag, freq in sorted_tags:
            logger.info(f"{tag}: {freq}")
    
    elapsed_time = time.time() - start_time
    logger.info(f"Done! Total time: {elapsed_time:.2f} seconds")
    
    return 0


def setup_parser():
    """引数パーサーのセットアップ"""
    parser = argparse.ArgumentParser(description="WD14 tagger for images")
    
    # 入力/出力関連
    parser.add_argument(
        "--dir_image", type=str, required=True,
        help="Directory or file to process / 処理対象のディレクトリまたはファイル"
    )
    parser.add_argument(
        "--recursive", action="store_true", default=True,
        help="Search for images in subdirectories recursively / サブディレクトリを再帰的に検索する"
    )
    parser.add_argument(
        "--dir_save", type=str, default="./output",
        help="Output directory / 出力ディレクトリ"
    )
    parser.add_argument(
        "--preserve_own_folder", action="store_true", default=True,
        help="Preserve the original folder name in the output directory / 元のフォルダ名を出力ディレクトリに保持する"
    )
    parser.add_argument(
        "--preserve_structure", action="store_true", default=True,
        help="Preserve the directory structure in the output directory / ディレクトリ構造を出力ディレクトリに保持する"
    )
    parser.add_argument(
        "--by_folder", action="store_true", default=False,
        help="Process each folder separately / フォルダごとに個別に処理する"
    )
    
    # デバッグ関連
    parser.add_argument(
        "--debug", action="store_true",
        help="Debug mode / デバッグモード"
    )
    
    # タガー関連
    parser.add_argument(
        "--repo_id", type=str, default=DEFAULT_WD14_TAGGER_REPO,
        help="Repository ID for wd14 tagger on Hugging Face / Hugging Faceのwd14 taggerのリポジトリID"
    )
    parser.add_argument(
        "--model_dir", type=str, default="wd14_tagger_model",
        help="Directory to store wd14 tagger model / wd14 taggerのモデルを格納するディレクトリ"
    )
    parser.add_argument(
        "--force_download", action="store_true",
        help="Force downloading wd14 tagger models / wd14 taggerのモデルを再ダウンロードする"
    )
    parser.add_argument(
        "--batch_size", type=int, default=1,
        help="Batch size in inference / 推論時のバッチサイズ"
    )
    parser.add_argument(
        "--caption_extension", type=str, default=".txt",
        help="Extension of caption file / 出力されるキャプションファイルの拡張子"
    )
    parser.add_argument(
        "--thresh", type=float, default=0.35,
        help="Threshold of confidence to add a tag / タグを追加するか判定する閾値"
    )
    parser.add_argument(
        "--general_threshold", type=float, default=None,
        help="Threshold for general category tags / generalカテゴリのタグのしきい値"
    )
    parser.add_argument(
        "--character_threshold", type=float, default=None,
        help="Threshold for character category tags / characterカテゴリのタグのしきい値"
    )
    parser.add_argument(
        "--remove_underscore", action="store_true",
        help="Replace underscores with spaces in the output tags / タグのアンダースコアをスペースに置換"
    )
    parser.add_argument(
        "--undesired_tags", type=str, default="",
        help="Comma-separated list of undesired tags to remove / 除外したいタグのリスト"
    )
    parser.add_argument(
        "--frequency_tags", action="store_true",
        help="Show frequency of tags for images / タグの出現頻度を表示"
    )
    parser.add_argument(
        "--onnx", action="store_true",
        help="Use ONNX model for inference / ONNXモデルを使用"
    )
    parser.add_argument(
        "--append_tags", action="store_true",
        help="Append captions instead of overwriting / 既存のキャプションに追記"
    )
    parser.add_argument(
        "--use_rating_tags", action="store_true",
        help="Add rating tags with 'rating_' prefix / 'rating_'プレフィックス付きでレーティングタグを追加"
    )
    parser.add_argument(
        "--use_rating_tags_as_last_tag", action="store_true",
        help="Add rating tags as the last tag / レーティングタグを最後に追加"
    )
    parser.add_argument(
        "--character_tags_first", action="store_true",
        help="Insert character tags before general tags / キャラクタータグを一般タグの前に挿入"
    )
    parser.add_argument(
        "--always_first_tags", type=str, default=None,
        help="Tags to always put first, e.g. '1girl,1boy' / 常に先頭に配置するタグ"
    )
    parser.add_argument(
        "--caption_separator", type=str, default=", ",
        help="Separator for captions / キャプションの区切り文字"
    )
    parser.add_argument(
        "--tag_replacement", type=str, default=None,
        help="Tag replacements in format 'source1,target1;source2,target2' / タグ置換設定"
    )
    parser.add_argument(
        "--character_tag_expand", action="store_true",
        help="Expand character tag parentheses to separate tags / キャラクタータグの括弧部分を別タグに展開"
    )
    parser.add_argument(
        "--max_data_loader_n_workers", type=int, default=None,
        help="Number of workers for DataLoader / DataLoaderのワーカー数"
    )
    # 引数パーサーに新しいオプションを追加
    parser.add_argument(
        "--add_tag", type=str, default=None,
        help="Additional tags to add to all images, e.g. 'ghibli style, anime screencap' / すべての画像に追加するタグ"
    )
    parser.add_argument(
        "--add_tag_position", type=str, default="first", choices=["first", "last"],
        help="Position to add the additional tags: 'first' or 'last' / 追加タグを配置する位置"
    )

    # メモリキャッシュ関連
    parser.add_argument(
        "--mem_cache", type=bool, default=True,
        help="Use memory cache for processed files / 処理済みファイルをメモリにキャッシュ"
    )
    
    # マルチスレッド関連
    parser.add_argument(
        "--threads", type=int, default=DEFAULT_THREADS,
        help=f"Number of threads (default: {DEFAULT_THREADS}) / スレッド数"
    )
    
    return parser


if __name__ == "__main__":
    sys.exit(main())