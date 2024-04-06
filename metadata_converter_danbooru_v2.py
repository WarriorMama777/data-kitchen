import argparse
import json
import os
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description='Convert Danbooru metadata files to plain text format.')
    parser.add_argument('--dir', type=str, help='Directory containing metadata files', required=True)
    parser.add_argument('--save', type=str, help='Directory to save converted files', required=True)
    parser.add_argument('--metadata_order', nargs='+', help='Order of metadata labels to extract. Format: --metadata_order "METADATA_LABEL" "METADATA_LABEL"', required=True)
    parser.add_argument('--insert_custom_text', type=str, help='Insert custom text at a specified index in the output. Format: --insert_custom_text INDEX,CUSTOM_TEXT @Note: index counts from 0. ', required=False)

    args = parser.parse_args()

    # ディレクトリが存在しない場合は作成
    Path(args.save).mkdir(parents=True, exist_ok=True)

    files = os.listdir(args.dir)
    total_files = len(files)
    processed_files = 0

    # 指定されたディレクトリ内の全ファイルを処理
    for file_name in files:
        if file_name.endswith('.txt') or file_name.endswith('.json'):
            process_file(os.path.join(args.dir, file_name), args.save, args.metadata_order, args.insert_custom_text)
            processed_files += 1
            print(f"Processed {processed_files}/{total_files} files.")
        else:
            print(f"Skipped non-metadata file: {file_name}")

def process_file(file_path, save_dir, metadata_order, insert_custom_text=None):
    with open(file_path, 'r', encoding='utf-8') as file:
        try:
            metadata = json.load(file)
        except json.JSONDecodeError:
            # JSONとして読み込めない場合はスキップ
            print(f"Warning: Skipping file due to JSONDecodeError: {file_path}")
            return

    extracted_data = []
    for key in metadata_order:
        if key in metadata and metadata[key]:
            # 'rating'の場合は特別な整形を行う
            if key == 'rating':
                value = f'rating_{metadata[key]}'
            else:
                value = metadata[key].replace(' ', ',')
            extracted_data.append(value)

    if insert_custom_text:
        index, text = insert_custom_text.split(',', 1)
        extracted_data.insert(int(index), text)

    # 連続するカンマを取り除く
    output_content = ','.join(filter(None, extracted_data))
    output_file_path = os.path.join(save_dir, os.path.basename(file_path))

    with open(output_file_path, 'w', encoding='utf-8') as output_file:
        output_file.write(output_content)

if __name__ == '__main__':
    main()
