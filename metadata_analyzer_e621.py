import argparse
import os
import json
from collections import defaultdict

def analyze_metadata(dir_path, save_path, metadata_label, count=False, metadata_append=[]):
    # 結果を格納する辞書
    results = defaultdict(lambda: defaultdict(list))
    # 指定ディレクトリを走査
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            if file.endswith('.txt') or file.endswith('.json'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)

                        # metadata_labelに基づいてデータを集計
                        label_values = []
                        if metadata_label in metadata:
                            # metadata_labelがトップレベルに存在する場合
                            if isinstance(metadata[metadata_label], list):
                                label_values.extend(metadata[metadata_label])
                            else:
                                label_values.append(metadata[metadata_label])
                        elif 'tags' in metadata and metadata_label in metadata['tags']:
                            # metadata_labelがtags内に存在する場合
                            label_values.extend(metadata['tags'][metadata_label])

                        for label_value in label_values:
                            results[label_value]['count'].append(1)
                            for append_label in metadata_append:
                                if append_label in metadata and metadata[append_label] is not None:
                                    results[label_value][append_label].append(metadata[append_label])
                                elif 'tags' in metadata and append_label in metadata['tags'] and metadata['tags'][append_label] is not None:
                                    results[label_value][append_label].extend(metadata['tags'][append_label])

                except Exception as e:
                    print(f"Error processing file {file_path}: {e}")

    # 結果の加工
    final_results = {}
    for artist, data in results.items():
        final_results[artist] = {}
        final_results[artist]['count'] = str(sum(data['count']))
        for key, values in data.items():
            if key != 'count':
                # リスト内の要素をフラットにするため、拡張されたリスト理解を使用
                flat_list = [item for sublist in values for item in (sublist if isinstance(sublist, list) else [sublist])]
                # ユニークな要素のみを保持
                unique_items = set(flat_list)
                # 最終的な文字列の生成
                final_results[artist][key] = ", ".join(map(str, unique_items))

    # 結果を保存
    save_file_path = os.path.join(save_path, 'analysis_result.txt')
    with open(save_file_path, 'w', encoding='utf-8') as f:
        json.dump(final_results, f, ensure_ascii=False, indent=4)

    print(f"Analysis completed. Results saved to {save_file_path}")

def main():
    parser = argparse.ArgumentParser(description="Analyze metadata files for specific labels.")
    parser.add_argument("--dir", type=str, required=True, help="Directory containing metadata files to analyze.")
    parser.add_argument("--save", type=str, required=True, help="Directory to save the analysis results.")
    parser.add_argument("--metadata_label", type=str, required=True, help="Main metadata label to analyze.")
    parser.add_argument("--count", action='store_true', help="Include count of items for each label.")
    parser.add_argument("--metadata_append", nargs='*', help="Additional metadata labels to append.")

    args = parser.parse_args()

    analyze_metadata(args.dir, args.save, args.metadata_label, args.count, args.metadata_append)

if __name__ == "__main__":
    main()
