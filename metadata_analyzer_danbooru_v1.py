import argparse
import json
import glob
import os

def analyze_files(directory, metadata_label):
    # 集計結果を保持する辞書
    result = {}
    
    # 指定ディレクトリ内の全.txtと.jsonファイルを検索
    for file_path in glob.glob(os.path.join(directory, '*.txt')) + glob.glob(os.path.join(directory, '*.json')):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                # ファイルの内容を読み込む
                content = json.load(file)
                
                # 指定されたメタデータラベルが存在するか確認
                if metadata_label in content:
                    # ラベルの値を取得
                    label_value = content[metadata_label]
                    # 集計
                    if label_value in result:
                        result[label_value] += 1
                    else:
                        result[label_value] = 1
        except Exception as e:
            print(f"Error processing file {file_path}: {e}")
    
    return result

def save_results(results, output_file):
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(results, file, ensure_ascii=False, indent=4)

def main():
    parser = argparse.ArgumentParser(description='Analyze metadata from files and aggregate values.')
    parser.add_argument('--metadata_label', required=True, help='The metadata label to analyze.')
    parser.add_argument('--dir', required=True, help='Directory containing files to analyze.')
    args = parser.parse_args()
    
    # ファイルを解析
    results = analyze_files(args.dir, args.metadata_label)
    
    # 結果を保存
    save_results(results, os.path.join(args.dir, 'analysis_result.txt'))
    print("Analysis complete. Results saved to analysis_result.txt")

if __name__ == "__main__":
    main()
