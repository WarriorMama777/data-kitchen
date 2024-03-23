import json
import os
import glob

# ディレクトリの指定
directory_path = '/path/to/your/directory'

# ディレクトリ内の全txtファイルに対して処理を行う
for filename in glob.glob(os.path.join(directory_path, '*.txt')):
    with open(filename, 'r') as f:
        data = json.load(f)

    # 必要な要素を抽出
    tags = data['tags']
    elements = ['artist', 'copyright', 'character', 'species', 'meta']
    selected_elements = []
    for element in elements:
        selected_elements.extend(tags[element])

    # 1行の平文に整形
    formatted_text = ', '.join(selected_elements)

    # 同じファイルに上書き保存
    with open(filename, 'w') as f:
        f.write(formatted_text)
