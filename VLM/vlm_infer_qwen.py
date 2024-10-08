import os
import argparse
import glob
import signal
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import torch
from transformers import Qwen2VLForConditionalGeneration, AutoTokenizer, AutoProcessor
from qwen_vl_utils import process_vision_info
import psutil
import gc

def signal_handler(sig, frame):
    print('\nプログラムを終了します。')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def get_optimal_thread_count():
    return psutil.cpu_count(logical=False)

def process_image(image_path, model, processor, prompt, max_new_tokens, remove_newlines):
    try:
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image_path},
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        text = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
        inputs = inputs.to(model.device)

        with torch.no_grad():
            generated_ids = model.generate(**inputs, max_new_tokens=max_new_tokens)
        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0]

        if remove_newlines:
            output_text = output_text.replace('\n', ' ')

        return image_path, output_text.strip()
    except Exception as e:
        print(f"エラーが発生しました: {image_path}")
        print(traceback.format_exc())
        return image_path, None

def process_batch(batch, model, processor, prompt, args):
    results = {}
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = []
        for image_path in batch:
            future = executor.submit(process_image, image_path, model, processor, prompt, args.max_new_tokens, args.remove_newlines)
            futures.append(future)

        for future in as_completed(futures):
            image_path, caption = future.result()
            if caption:
                results[image_path] = caption

    return results

def main(args):
    if args.prompt.endswith('.txt'):
        with open(args.prompt, 'r', encoding='utf-8') as f:
            prompt = f.read().strip()
    else:
        prompt = args.prompt

    model = Qwen2VLForConditionalGeneration.from_pretrained(
        args.model, torch_dtype="auto", device_map="auto"
    )
    processor = AutoProcessor.from_pretrained(args.model)

    supported_extensions = tuple(f'.{ext.lower()}' for ext in args.extension)
    if os.path.isfile(args.dir_image):
        image_files = [args.dir_image]
    else:
        pattern = os.path.join(args.dir_image, '**' if args.recursive else '', '*')
        image_files = glob.glob(pattern, recursive=args.recursive)
        image_files = [f for f in image_files if f.lower().endswith(supported_extensions)]

    batch_size = args.batch_size
    results = {}

    with tqdm(total=len(image_files), desc="画像処理中") as pbar:
        for i in range(0, len(image_files), batch_size):
            batch = image_files[i:i+batch_size]
            try:
                batch_results = process_batch(batch, model, processor, prompt, args)
                results.update(batch_results)
                pbar.update(len(batch))
            except torch.cuda.OutOfMemoryError:
                print(f"メモリ不足エラーが発生しました。バッチサイズを{batch_size//2}に縮小します。")
                batch_size = max(1, batch_size // 2)
                i -= len(batch)  # この失敗したバッチを再処理
            
            # GPUメモリの解放
            torch.cuda.empty_cache()
            gc.collect()

    save_results(results, args)

def save_results(results, args):
    for image_path, caption in results.items():
        if os.path.isfile(args.dir_image):
            # 入力が単一ファイルの場合
            parent_dir = os.path.basename(os.path.dirname(args.dir_image))
            rel_path = os.path.basename(image_path)
        else:
            # 入力がディレクトリの場合
            parent_dir = os.path.basename(args.dir_image)
            rel_path = os.path.relpath(image_path, args.dir_image)

        if args.preserve_own_folder:
            save_path = os.path.join(args.dir_save, parent_dir, rel_path)
        else:
            save_path = os.path.join(args.dir_save, rel_path)

        if args.preserve_structure:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
        else:
            save_path = os.path.join(args.dir_save, parent_dir, os.path.basename(image_path))

        txt_path = os.path.splitext(save_path)[0] + '.txt'
        os.makedirs(os.path.dirname(txt_path), exist_ok=True)
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(caption)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QwenVLを使用した画像キャプション生成")
    parser.add_argument("--dir_image", required=True, help="処理対象ディレクトリまたはファイル")
    parser.add_argument("--recursive", type=bool, default=True, help="サブディレクトリも探索するか")
    parser.add_argument("--dir_save", default="./output", help="出力ディレクトリ")
    parser.add_argument("--preserve_own_folder", action="store_true", help="処理対象ディレクトリ名またはファイルの親ディレクトリ名を保持するか")
    parser.add_argument("--preserve_structure", action="store_true", help="ディレクトリ構造を保持するか")
    parser.add_argument("--extension", nargs='+', default=['jpg', 'jpeg', 'png', 'webp', 'bmp'], help="処理対象の拡張子")
    parser.add_argument("--prompt", default="Describe this image.", help="VLMモデルに対するプロンプト")
    parser.add_argument("--model", default="Qwen2-VL-7B-Instruct-GPTQ-Int4", help="モデル名またはパス")
    parser.add_argument("--max_new_tokens", type=int, default=50, help="生成するキャプションの最大トークン数")
    parser.add_argument("--threads", type=int, default=get_optimal_thread_count(), help="使用するスレッド数")
    parser.add_argument("--remove_newlines", action="store_true", help="出力テキストの改行を削除するか")
    parser.add_argument("--batch_size", type=int, default=1, help="一度に処理する画像の数")

    args = parser.parse_args()
    main(args)