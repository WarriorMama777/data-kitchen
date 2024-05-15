import requests
from bs4 import BeautifulSoup
import os
import argparse
from tqdm import tqdm

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}

def fetch_anime_urls(base_url, start_letter, end_letter):
    urls = []
    # '0'のページを最初に追加
    special_page_url = f"{base_url}?0"
    response = requests.get(special_page_url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if href and href.startswith("/anime/showimages.php?"):
                full_url = f"https://fancaps.net{href}"
                urls.append(full_url)
    else:
        print(f"Error fetching {special_page_url}: Status code {response.status_code}")

    # 以前の処理を続ける
    for letter in tqdm(range(ord(start_letter), ord(end_letter) + 1), desc="アルファベット"):
        page_url = f"{base_url}?{chr(letter)}"
        response = requests.get(page_url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href and href.startswith("/anime/showimages.php?"):
                    full_url = f"https://fancaps.net{href}"
                    urls.append(full_url)
        else:
            print(f"Error fetching {page_url}: Status code {response.status_code}")
    return urls


def save_urls_to_file(urls, save_dir, file_name):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    file_path = os.path.join(save_dir, file_name)
    with open(file_path, 'w', encoding='utf-8') as file:  # ここでエンコーディングを指定
        for url in tqdm(urls, desc="URLを保存"):
            file.write(f"{url}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Fancaps Anime URL Scraper')
    parser.add_argument('--save_dir', type=str, required=True, help='URLを保存するディレクトリ')
    parser.add_argument('--extension', type=str, default='txt', help='ファイル拡張子')
    args = parser.parse_args()

    BASE_URL = "https://fancaps.net/anime/showList.php"
    START_LETTER = 'a'
    END_LETTER = 'z'

    print("アニメURLを取得中...")
    anime_urls = fetch_anime_urls(BASE_URL, START_LETTER, END_LETTER)
    file_name = f'anime_urls.{args.extension}'
    print(f"URLを {args.save_dir}/{file_name} に保存中...")
    save_urls_to_file(anime_urls, args.save_dir, file_name)
    print("完了しました。")
