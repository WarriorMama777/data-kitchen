import argparse
import json
from pathlib import Path
from collections import defaultdict

def analyze_metadata(dir_path, save_path, metadata_label, count=False, metadata_append=[]):
    results = defaultdict(lambda: {"count": 0, **{label: [] for label in metadata_append}})
    total_files = 0
    
    for file_path in Path(dir_path).rglob('*'):
        if file_path.suffix not in ['.txt', '.json']:
            continue

        print(f"Analyzing file: {file_path}")
        total_files += 1

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                metadata = json.load(file)
                if metadata_label in metadata or (metadata_label in metadata.get('tags', {})):
                    label_values = metadata.get(metadata_label) or metadata.get('tags', {}).get(metadata_label)
                    if not isinstance(label_values, list):
                        label_values = [label_values]
                    for label_value in label_values:
                        results[label_value]["count"] += 1
                        for label in metadata_append:
                            if label in metadata:
                                results[label_value][label].append(metadata[label])
                            elif label in metadata.get('tags', {}):
                                results[label_value][label].extend(metadata['tags'][label])
        except json.JSONDecodeError:
            print(f"Skipping invalid JSON file: {file_path}")

    for result in results.values():
        result["count"] = sum(result["count"]) if count else str(result["count"])
        for label in metadata_append:
            result[label] = ", ".join(set(str(item) for sublist in result[label] for item in (sublist if isinstance(sublist, list) else [sublist])))

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
    parser.add_argument("--count", action='store_true', help="Include count of items for each label.")
    parser.add_argument("--metadata_append", nargs='+', help="Additional metadata labels to include in the analysis.", default=[])

    args = parser.parse_args()

    analyze_metadata(args.dir, args.save, args.metadata_label, args.count, args.metadata_append)

if __name__ == "__main__":
    main()
