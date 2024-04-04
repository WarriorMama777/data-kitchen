import argparse
import json
from pathlib import Path
from collections import defaultdict

def analyze_metadata(dir_path, save_path, metadata_label, append_labels=[]):
    # "score"をデフォルトのキーから削除し、append_labelsに基づいてキーを追加
    results = defaultdict(lambda: {"count": 0, **{label: [] for label in append_labels}})
    total_files = 0  # 解析されたファイルの総数をカウントするための変数を追加
    
    for file_path in Path(dir_path).glob('**/*'):
        if file_path.suffix not in ['.txt', '.json']:
            continue

        print(f"Analyzing file: {file_path}")  # 解析中のファイル名を表示
        total_files += 1  # 解析されたファイルの数をインクリメント

        with open(file_path, 'r', encoding='utf-8') as file:
            try:
                metadata = json.load(file)
                label_value = metadata.get(metadata_label, None)
                if label_value:
                    results[label_value]["count"] += 1
                    for label in append_labels:
                        if metadata.get(label):
                            results[label_value][label].append(metadata[label])
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON file: {file_path}")

    for result in results.values():
        for label in append_labels:
            if label == "score":
                result[label] = ", ".join(map(str, result[label]))
            else:
                result[label] = ", ".join(set(str(item) for item in result[label]))

    print(f"Analysis complete. Total files analyzed: {total_files}")  # 解析完了と総ファイル数を表示

    # save_path に対応するディレクトリを確認し、存在しなければ作成
    Path(save_path).mkdir(parents=True, exist_ok=True)

    with open(Path(save_path) / "analysis_result.txt", 'w', encoding='utf-8') as file:
        json.dump(results, file, ensure_ascii=False, indent=4)
        print(f"Results saved to: {Path(save_path) / 'analysis_result.txt'}")  # 結果が保存された場所を表示

def main():
    parser = argparse.ArgumentParser(description="Analyze metadata files.")
    parser.add_argument("--dir", required=True, help="Directory containing metadata files.")
    parser.add_argument("--save", required=True, help="Directory to save analysis results.")
    parser.add_argument("--metadata_label", required=True, help="Main metadata label for analysis.")
    parser.add_argument("--metadata_append", nargs='+', help="Additional metadata labels to include in the analysis.", default=[])
    
    args = parser.parse_args()
    
    analyze_metadata(args.dir, args.save, args.metadata_label, args.metadata_append)

if __name__ == "__main__":
    main()
