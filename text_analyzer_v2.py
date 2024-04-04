import argparse
import json
from pathlib import Path
from collections import defaultdict

def analyze_metadata(dir_path, save_path, metadata_label, append_labels=[]):
    results = defaultdict(lambda: {"count": 0, **{label: [] for label in append_labels}})
    total_files = 0
    
    for file_path in Path(dir_path).glob('**/*'):
        if file_path.suffix not in ['.txt', '.json']:
            continue

        print(f"Analyzing file: {file_path}")
        total_files += 1

        with open(file_path, 'r', encoding='utf-8') as file:
            try:
                metadata = json.load(file)
                label_values = metadata.get(metadata_label, [])
                for label_value in label_values:  # metadata_labelがリストであることを想定
                    results[label_value]["count"] += 1
                    for label in append_labels:
                        if metadata.get(label):
                            # append_labelsに該当するデータもリスト形式を想定
                            results[label_value][label].extend([str(item) for item in metadata[label] if item not in results[label_value][label]])
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON file: {file_path}")

    for result in results.values():
        for label in append_labels:
            result[label] = ", ".join(sorted(set(result[label])))  # 重複を排除し、ソート

    print(f"Analysis complete. Total files analyzed: {total_files}")

    Path(save_path).mkdir(parents=True, exist_ok=True)
    with open(Path(save_path) / "analysis_result.txt", 'w', encoding='utf-8') as file:
        json.dump(results, file, ensure_ascii=False, indent=4)
        print(f"Results saved to: {Path(save_path) / 'analysis_result.txt'}")

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
