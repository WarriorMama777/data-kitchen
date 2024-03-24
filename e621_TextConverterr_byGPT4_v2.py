import json
import os
import glob

# ディレクトリの指定をターミナルから入力
directory_path = input('ディレクトリのパスを入力してください: ')

# ディレクトリ内の全txtファイルに対して処理を行う
for filename in glob.glob(os.path.join(directory_path, '*.txt')):
    with open(filename, 'r') as f:
        data = json.load(f)

    # 必要な要素を抽出
    tags = data['tags']
    elements = ['general', 'artist', 'copyright', 'character', 'species', 'meta']
    selected_elements = []
    for element in elements:
        selected_elements.extend(tags[element])

    # "rating"の値を取得し、"rating_○○○"の形に整形してリストに追加
    rating = "rating_" + data['rating']
    selected_elements.append(rating)

    # 1行の平文に整形
    formatted_text = ', '.join(selected_elements)

    # 同じファイルに上書き保存
    with open(filename, 'w') as f:
        f.write(formatted_text)
