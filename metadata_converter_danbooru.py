import argparse
import json
import os
from pathlib import Path
from tqdm import tqdm
import time  # デバッグ用の時間計測やリトライ間隔に使用

def process_directory(directory_path, save_dir, metadata_order, insert_custom_texts=None, debug=False):
    print(f"{directory_path} 内のファイルを処理中...")
    for root, dirs, files in tqdm(os.walk(directory_path)):
        relative_path = os.path.relpath(root, directory_path)
        current_save_dir = os.path.join(save_dir, relative_path)
        Path(current_save_dir).mkdir(parents=True, exist_ok=True)

        for file_name in tqdm(files):
            if file_name.endswith('.txt') or file_name.endswith('.json'):
                file_path = os.path.join(root, file_name)
                if debug:
                    print(f"[デバッグ] 処理するファイル: {file_path} -> 保存先: {current_save_dir}")
                else:
                    process_file(file_path, current_save_dir, metadata_order, insert_custom_texts)

def process_file(file_path, save_dir, metadata_order, insert_custom_texts=None):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            metadata = json.load(file)
    except json.JSONDecodeError:
        print(f"Warning: Skipping file due to JSONDecodeError: {file_path}")
        return

    extracted_data = []
    for key in metadata_order:
        value = metadata.get(key, "")
        if value:
            if key == 'rating':
                value = f'rating_{value}'
            else:
                value = value.replace(' ', ',')
        extracted_data.append(value)

    if insert_custom_texts:
        insert_pairs = [(int(insert_custom_texts[i]), insert_custom_texts[i + 1]) for i in range(0, len(insert_custom_texts), 2)]
        for index, text in sorted(insert_pairs, key=lambda x: x[0], reverse=True):
            extracted_data.insert(index, text)

    output_content = ','.join(filter(None, extracted_data))
    output_file_path = os.path.join(save_dir, os.path.basename(file_path))

    with open(output_file_path, 'w', encoding='utf-8') as output_file:
        output_file.write(output_content)
    print(f"Processed: {file_path} -> {output_file_path}")

def main():
    parser = argparse.ArgumentParser(description='Convert Danbooru metadata files to plain text format.')
    parser.add_argument('--dir', type=str, help='Directory containing metadata files', required=True)
    parser.add_argument('--save', type=str, help='Directory to save converted files', required=True)
    parser.add_argument('--metadata_order', nargs='+', help='Order of metadata labels to extract. Format: --metadata_order "METADATA_LABEL" "METADATA_LABEL"', required=True)
    parser.add_argument('--insert_custom_text', nargs='*', help='Insert custom texts at specified indexes in the output. Format: --insert_custom_text INDEX "CUSTOM_TEXT" INDEX "CUSTOM_TEXT" ...', required=False)
    parser.add_argument('--debug', action='store_true', help='Enable debug mode to display processing logs without making actual changes.')

    args = parser.parse_args()

    Path(args.save).mkdir(parents=True, exist_ok=True)

    process_directory(args.dir, args.save, args.metadata_order, args.insert_custom_text, args.debug)

if __name__ == '__main__':
    main()
