import argparse
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# コマンドライン引数の設定
parser = argparse.ArgumentParser(description="特定のカテゴリのファイルをダウンロードするスクリプト")
parser.add_argument('--url', type=str, required=True, help='ページのURL')
parser.add_argument('--dir', type=str, required=True, help='保存先ディレクトリ')
parser.add_argument('--c', type=str, choices=['audio', 'image', 'video'], help='ダウンロードするファイルのカテゴリ')

# 引数の解析
args = parser.parse_args()

# 各カテゴリにおける一般的な拡張子のリスト
extensions = {
    'audio': ['mp3', 'wav', 'aac'],
    'image': ['jpg', 'jpeg', 'png', 'gif', 'webp', 'avif', 'bmp'],
    'video': ['mp4', 'avi', 'mov', 'avif']
}

def download_file(url, dir, category):
    # ページのコンテンツを取得
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')

    # ダウンロードするファイルの拡張子をチェック
    valid_extensions = extensions[category]
    
    # 保存先ディレクトリが存在しない場合は作成
    if not os.path.exists(dir):
        os.makedirs(dir)

    # ページ内の全リンクを検索
    for link in soup.find_all('a', href=True):
        href = link['href']
        if any(href.endswith(ext) for ext in valid_extensions):
            # 絶対URLを取得
            full_url = urljoin(url, href)
            # 保存先のファイルパスを指定
            save_path = os.path.join(dir, href.split('/')[-1])
            # ファイルをダウンロードして保存
            with requests.get(full_url, stream=True) as r:
                with open(save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192): 
                        f.write(chunk)
            print(f"ダウンロード完了: {save_path}")

if __name__ == '__main__':
    download_file(args.url, args.dir, args.c)
