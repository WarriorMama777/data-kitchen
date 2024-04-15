# 必要なライブラリをインポート
import argparse
import json
import os
from pathlib import Path

def main():
    # コマンドライン引数を解析するためのパーサーを設定
    parser = argparse.ArgumentParser(description='Convert Danbooru metadata files to plain text format.')
    parser.add_argument('--dir', type=str, help='Directory containing metadata files', required=True)
    parser.add_argument('--save', type=str, help='Directory to save converted files', required=True)
    parser.add_argument('--metadata_order', nargs='+', help='Order of metadata labels to extract. Format: --metadata_order "METADATA_LABEL" "METADATA_LABEL"', required=True)
    parser.add_argument('--insert_custom_text', nargs='*', help='Insert custom texts at specified indexes in the output. Format: --insert_custom_text INDEX "CUSTOM_TEXT" INDEX "CUSTOM_TEXT" ...', required=False)


    args = parser.parse_args()

    # 出力ディレクトリを作成（既に存在していてもOK）
    Path(args.save).mkdir(parents=True, exist_ok=True)

    # 指定ディレクトリ内のファイルリストを取得
    files = os.listdir(args.dir)
    total_files = len(files)
    processed_files = 0

    # 各ファイルを処理
    for file_name in files:
        if file_name.endswith('.txt') or file_name.endswith('.json'):
            process_file(os.path.join(args.dir, file_name), args.save, args.metadata_order, args.insert_custom_text)
            processed_files += 1
            print(f"Processed {processed_files}/{total_files} files.")
        else:
            print(f"Skipped non-metadata file: {file_name}")

def process_file(file_path, save_dir, metadata_order, insert_custom_texts=None):
    # ファイルを開き、JSONとして読み込む
    with open(file_path, 'r', encoding='utf-8') as file:
        try:
            metadata = json.load(file)
        except json.JSONDecodeError:
            print(f"Warning: Skipping file due to JSONDecodeError: {file_path}")
            return

    extracted_data = []
    extracted_data = []
    # 指定されたメタデータ順にデータを抽出
    for key in metadata_order:
        if key in metadata and metadata[key]:
            if key == 'rating':
                value = f'rating_{metadata[key]}'
            else:
                value = metadata[key].replace(' ', ',')
        else:
            value = ""  # キーが存在しない場合や値が空の場合は空文字列を挿入
        extracted_data.append(value)

    # カスタムテキストがあれば指定位置に挿入
    if insert_custom_texts:
        # 引数のリストをインデックスとテキストのペアに変換
        insert_pairs = [(int(insert_custom_texts[i]), insert_custom_texts[i + 1]) for i in range(0, len(insert_custom_texts), 2)]
        for index, text in sorted(insert_pairs, key=lambda x: x[0], reverse=True):
            extracted_data.insert(index, text)

    # 抽出したデータをカンマ区切りで結合
    output_content = ','.join(filter(None, extracted_data))
    output_file_path = os.path.join(save_dir, os.path.basename(file_path))

    # 結果をファイルに書き込み
    with open(output_file_path, 'w', encoding='utf-8') as output_file:
        output_file.write(output_content)

if __name__ == '__main__':
    main()

