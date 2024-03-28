import argparse
import json
import os

def format_metadata(directory_path):
    for filename in os.listdir(directory_path):
        if filename.endswith(".txt"):
            file_path = os.path.join(directory_path, filename)

            with open(file_path, 'r', encoding='utf-8') as file:
                try:
                    data = json.loads(file.read())
                except json.JSONDecodeError:
                    print(f"Skipping {filename}: not a valid JSON.")
                    continue

            # 各タグカテゴリのデータを抽出し、カンマ区切りの文字列に変換
            tag_string_copyright = data.get('tag_string_copyright', '').replace(' ', ',')
            tag_string_character = data.get('tag_string_character', '').replace(' ', ',')
            tag_string_general = data.get('tag_string_general', '').replace(' ', ',')
            tag_string_meta = data.get('tag_string_meta', '').replace(' ', ',')
            tag_string_artist = data.get('tag_string_artist', '').replace(' ', ',')

            # レーティングの整形
            rating = "rating_" + data.get('rating', '')

            # 全部を一つの文字列に結合する前に空の文字列を除外
            tags_and_rating = [tag_string for tag_string in [
                tag_string_copyright, tag_string_character, tag_string_general,
                tag_string_meta, rating, tag_string_artist
            ] if tag_string]

            # 空でない文字列をカンマで結合
            formatted_string = ",".join(tags_and_rating)

            # 先頭と末尾の不要なカンマを削除
            formatted_string = formatted_string.strip(',')

            # 結果を同じファイルに上書き保存
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(formatted_string)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Format metadata from .txt files within a directory and save them.")
    parser.add_argument("--directory", type=str, default="./", help="Path to the directory containing .txt files")

    args = parser.parse_args()

    format_metadata(args.directory)
