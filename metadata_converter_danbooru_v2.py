import argparse
import json
import os
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description='Convert Danbooru metadata files to plain text format.')
    parser.add_argument('--dir', type=str, help='Directory containing metadata files', required=True)
    parser.add_argument('--save', type=str, help='Directory to save converted files', required=True)
    parser.add_argument('--metadata_order', nargs='+', help='Order of metadata labels to extract', required=True)

    args = parser.parse_args()

    # ディレクトリが存在しない場合は作成
    Path(args.save).mkdir(parents=True, exist_ok=True)

    # 指定されたディレクトリ内の全ファイルを処理
    for file_name in os.listdir(args.dir):
        if file_name.endswith('.txt') or file_name.endswith('.json'):
            process_file(os.path.join(args.dir, file_name), args.save, args.metadata_order)

def process_file(file_path, save_dir, metadata_order):
    with open(file_path, 'r', encoding='utf-8') as file:
        try:
            metadata = json.load(file)
        except json.JSONDecodeError:
            # JSONとして読み込めない場合はスキップ
            print(f"Warning: Skipping file due to JSONDecodeError: {file_path}")
            return

    extracted_data = []
    for key in metadata_order:
        # 'rating'の場合は特別な整形を行う
        if key == 'rating':
            value = f'rating_{metadata.get(key, "")}'
        else:
            value = metadata.get(key, "").replace(' ', ',')
        extracted_data.append(value)

    output_content = ','.join(extracted_data)
    output_file_path = os.path.join(save_dir, os.path.basename(file_path))

    with open(output_file_path, 'w', encoding='utf-8') as output_file:
        output_file.write(output_content)

if __name__ == '__main__':
    main()
