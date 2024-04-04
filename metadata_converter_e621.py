import json
import os
import glob

# Input the directory path from the terminal
# ディレクトリの指定をターミナルから入力
directory_path = input('Enter the directory path: ')

# Process all txt files in the directory
# ディレクトリ内の全txtファイルに対して処理を行う
for filename in glob.glob(os.path.join(directory_path, '*.txt')):
    with open(filename, 'r') as f:
        data = json.load(f)

    # Extract the necessary elements
    # 必要な要素を抽出
    tags = data['tags']
    elements = ['general', 'artist', 'copyright', 'character', 'species', 'meta']
    selected_elements = []
    for element in elements:
        selected_elements.extend(tags[element])

    # Extract the value of "rating", format it into "rating_○○○", and add it to the list
    # "rating"の値を取得し、"rating_○○○"の形に整形してリストに追加
    rating = "rating_" + data['rating']
    selected_elements.append(rating)

    # Format into a single line of plain text
    # 1行の平文に整形
    formatted_text = ', '.join(selected_elements)

    # Overwrite and save to the same file
    # 同じファイルに上書き保存
    with open(filename, 'w') as f:
        f.write(formatted_text)
