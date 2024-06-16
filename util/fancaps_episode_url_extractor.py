import os
import argparse
import signal
from tqdm import tqdm

# Signal handler for graceful exit
def signal_handler(sig, frame):
    print("\nプロセスが中断されました。終了します...")
    exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Function to extract necessary URLs
def extract_urls(content, add_middle_url=False):
    urls = content.split('\n')
    url_dict = {}
    for url in urls:
        if url:
            anime_name = url.split('/')[4].split('?')[1].split('-')[1]
            if anime_name not in url_dict:
                url_dict[anime_name] = [url]
            else:
                url_dict[anime_name].append(url)
    
    result_urls = []
    for key in url_dict:
        episodes = url_dict[key]
        result_urls.append(episodes[0])  # 最初のエピソード
        if add_middle_url and len(episodes) > 2:
            middle_index = len(episodes) // 2
            result_urls.append(episodes[middle_index])  # 中央のエピソード
        result_urls.append(episodes[-1])  # 最後のエピソード
    
    return result_urls

# Main function to process files
def process_files(input_path, output_dir, debug, add_middle_url):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"出力ディレクトリを作成しました: {output_dir}")
    
    if os.path.isdir(input_path):
        files = [os.path.join(input_path, f) for f in os.listdir(input_path) if os.path.isfile(os.path.join(input_path, f))]
    else:
        files = [input_path]
    
    for file_path in tqdm(files, desc="ファイル処理中"):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                extracted_urls = extract_urls(content, add_middle_url)
                
                if debug:
                    print(f"デバッグモード: {file_path} の処理結果")
                    for url in extracted_urls:
                        print(url)
                else:
                    output_file = os.path.join(output_dir, os.path.basename(file_path))
                    with open(output_file, 'w', encoding='utf-8') as out_file:
                        for url in extracted_urls:
                            out_file.write(url + '\n')
                    print(f"ファイルが正常に保存されました: {output_file}")
        except Exception as e:
            print(f"エラー: {file_path} の処理中に問題が発生しました。詳細: {e}")

# Argument parser setup
def main():
    parser = argparse.ArgumentParser(description='FancapエピソードURLに対するURL抽出スクリプト。Episode_1から最後のEpisodeだけを残してテキストファイルを出力するだけ')
    parser.add_argument('--dir', required=True, help='処理対象ディレクトリまたはファイル')
    parser.add_argument('--save_dir', default='./output', help='出力ディレクトリのパス')
    parser.add_argument('--debug', action='store_true', help='デバッグモードを有効にする')
    parser.add_argument('--add_middle_url', action='store_true', help='最初と最後のエピソードに加え、中央値のエピソードも含める')
    args = parser.parse_args()

    process_files(args.dir, args.save_dir, args.debug, args.add_middle_url)

if __name__ == "__main__":
    main()
