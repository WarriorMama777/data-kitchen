import argparse
import os
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
import torch
from PIL import Image

def parse_arguments():
    parser = argparse.ArgumentParser(description='Qwen2-VL-7B-Instruct-GPTQ-Int4を使用した画像キャプション生成')
    parser.add_argument('--dir_image', required=True, help='処理対象の画像ファイルパス')
    parser.add_argument('--prompt', default='Describe this image.', help='VLMモデルに対するプロンプト')
    parser.add_argument('--dir_save', default='./output', help='キャプションを保存するディレクトリパス')
    return parser.parse_args()

def save_caption(caption, image_path, save_dir):
    os.makedirs(save_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    save_path = os.path.join(save_dir, f"{base_name}.txt")
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write(caption)
    print(f"Caption saved to: {save_path}")

def main():
    args = parse_arguments()

    # モデルとプロセッサーのロード
    model = Qwen2VLForConditionalGeneration.from_pretrained(
        "Qwen/Qwen2-VL-7B-Instruct-GPTQ-Int4", torch_dtype="auto", device_map="auto"
    )
    processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-7B-Instruct-GPTQ-Int4")

    # 画像の読み込み
    if not os.path.exists(args.dir_image):
        print(f"Error: Image file not found at {args.dir_image}")
        return

    image = Image.open(args.dir_image)

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": args.prompt},
            ],
        }
    ]

    # 推論の準備
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

    # 推論：出力の生成
    generated_ids = model.generate(**inputs, max_new_tokens=128)
    generated_ids_trimmed = [
        out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    output_text = processor.batch_decode(
        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )
    
    caption = output_text[0]
    print("Generated caption:", caption)
    
    # キャプションの保存
    save_caption(caption, args.dir_image, args.dir_save)

if __name__ == "__main__":
    main()
