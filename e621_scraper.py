import requests
from bs4 import BeautifulSoup

# 検索ワード
search_query = "palworld"

# URL
base_url = "https://e621.net/post/index.json"
params = {
    "tags": search_query,
    "limit": 100,
}

# リクエスト
response = requests.get(base_url, params=params)
text_data = response.text
# 正規表現や文字列操作で必要な情報を抽出


# 画像とメタデータの保存
for post in data["posts"]:
    # 画像URL
    image_url = post["file_url"]

    # メタデータ
    metadata = {
        "id": post["id"],
        "tags": post["tags"],
        "artist": post["artist"],
        "created_at": post["created_at"],
        "score": post["score"],
        "width": post["width"],
        "height": post["height"],
    }

    # 画像の保存
    with open(f"image_{post['id']}.jpg", "wb") as f:
        f.write(requests.get(image_url).content)

    # メタデータの保存
    with open(f"metadata_{post['id']}.txt", "w") as f:
        for key, value in metadata.items():
            f.write(f"{key}: {value}\n")
