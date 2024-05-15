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
    parser = argparse.ArgumentParser(description='Fetch Fancaps episode URLs.')
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
    with open(output_path, 'w') as file:
        for url in all_episode_urls:
            file.write(f"{url}\n")

    if args.verbose:
        print(f"Episode URLs saved to {output_path}")

if __name__ == "__main__":
    main()
