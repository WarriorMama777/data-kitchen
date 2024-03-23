import os
import requests
from urllib.parse import quote
from bs4 import BeautifulSoup
import json

# タグまたは検索ワードを指定
keyword = input("対象とするタグまたは検索ワードを入力してください: ")

# ページ数を指定
pages = int(input("取得するページ数を入力してください: "))

# 保存先のディレクトリ名を取得
dir_name = input("画像を保存するディレクトリ名を入力してください: ")

# ディレクトリを作成
if not os.path.exists(dir_name):
    os.makedirs(dir_name)

# ヘッダーにユーザーエージェントを設定
headers = {
    'User-Agent': 'MyProject/1.0 (by username on e621)'
}

for page in range(1, pages+1):
    url = f"https://e621.net/posts.json?tags={quote(keyword)}&page={page}"
    response = requests.get(url, headers=headers)
    posts = response.json()["posts"]

    for post in posts:
        img_url = post["file"]["url"]
        if img_url is not None:  # 画像のURLが存在するかチェック
            img_name = os.path.join(dir_name, os.path.basename(img_url))
            img_response = requests.get(img_url, stream=True, headers=headers)
            with open(img_name, 'wb') as out_file:
                out_file.write(img_response.content)

            metadata_name = img_name.rsplit(".", 1)[0] + ".txt"
            with open(metadata_name, 'w') as out_file:
                json.dump(post, out_file, indent=4)

    print(f"Page {page} completed.")
    
print("All pages completed.")
