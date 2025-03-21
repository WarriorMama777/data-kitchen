import requests
from bs4 import BeautifulSoup
import argparse
from tqdm import tqdm
import os

def fetch_episode_urls(anime_url, headers, verbose):
    episode_urls = []
    session = requests.Session()
    page = 1
    while True:
        try:
            response = session.get(f"{anime_url}&page={page}", headers=headers)
            response.raise_for_status()  # ステータスコードが200系でない場合にエラーを発生させる
        except requests.exceptions.RequestException as e:
            if verbose:
                print(f"URL: {anime_url} | Error: {e}")
            break
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # <div class="right_bar">要素を削除
        right_bar = soup.find('div', class_='right_bar')
        if right_bar:
            right_bar.decompose()  # もしくは right_bar.extract() を使用
        
        links = soup.find_all('a', href=True)
        found_new_link = False
        for link in links:
            href = link['href']
            if "episodeimages.php" in href:
                full_url = f"https://fancaps.net{href}" if href.startswith("/anime") else href
                if full_url not in episode_urls:
                    episode_urls.append(full_url)
                    found_new_link = True
        if not found_new_link:
            break
        page += 1
    return episode_urls

def main():
    parser = argparse.ArgumentParser(description='A script to obtain episode-specific URLs based on the URLs of each work obtained with `fancaps_url_scraper.py`.')
    parser.add_argument('--dir', type=str, help='Path to the input URL list file.', required=True)
    parser.add_argument('--save_dir', type=str, help='Directory to save the episode URLs file.', required=True)
    parser.add_argument('--verbose', action='store_true', help='Increase output verbosity')
    args = parser.parse_args()

    # ユーザーエージェントを設定
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    if not os.path.exists(args.save_dir):
        os.makedirs(args.save_dir)  # 指定された保存ディレクトリが存在しない場合、作成する

    with open(args.dir, 'r') as file:
        anime_urls = [line.strip() for line in file.readlines()]

    all_episode_urls = []
    for anime_url in tqdm(anime_urls, desc="Fetching URLs", disable=not args.verbose):
        episode_urls = fetch_episode_urls(anime_url, headers, args.verbose)
        all_episode_urls.extend(episode_urls)

    output_path = os.path.join(args.save_dir, "episode_urls.txt")
    # 既存のファイルと同じ名前がある場合は、一意のファイル名を生成する
    base_filename, file_extension = os.path.splitext(output_path)
    counter = 1
    while os.path.exists(output_path):
        output_path = f"{base_filename}_{counter}{file_extension}"
        counter += 1

    with open(output_path, 'w', encoding='utf-8') as file:  # ここでエンコーディングを指定
        for url in all_episode_urls:
            file.write(f"{url}\n")

    if args.verbose:
        print(f"Episode URLs saved to {output_path}")

if __name__ == "__main__":
    main()
