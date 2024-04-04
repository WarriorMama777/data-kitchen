import argparse
import json
from pathlib import Path
from collections import defaultdict

def analyze_metadata(dir_path, save_path, metadata_label, append_labels=[]):
    results = defaultdict(lambda: {"count": 0, "score": [], **{label: [] for label in append_labels}})
    
    for file_path in Path(dir_path).glob('**/*'):
        if file_path.suffix not in ['.txt', '.json']:
            continue

        with open(file_path, 'r', encoding='utf-8') as file:
            try:
                metadata = json.load(file)
                label_value = metadata.get(metadata_label, None)
                if label_value:
                    results[label_value]["count"] += 1
                    results[label_value]["score"].append(str(metadata.get("score", "")))
                    for label in append_labels:
                        if metadata.get(label):
                            results[label_value][label].append(metadata[label])
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON file: {file_path}")

    for result in results.values():
        result["score"] = ", ".join(map(str, result["score"]))
        for label in append_labels:
            result[label] = ", ".join(set(result[label]))

    with open(Path(save_path) / "analysis_result.txt", 'w', encoding='utf-8') as file:
        json.dump(results, file, ensure_ascii=False, indent=4)

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
