import argparse
import os
import re
import requests
from tqdm import tqdm
from bs4 import BeautifulSoup

# カラーコードの定義
class Colors:
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'

    @staticmethod
    def print(text, color):
        print(color + text + Colors.RESET)

# URLサポートクラスの定義
class UrlSupport:
    reSupportedUrls = {
        'season': r"https://fancaps.net/(.*?)/showimages.php.*?", 
        'episode': r"https://fancaps.net/(.*?)/episodeimages.php.*?", 
        'movie': r"https://fancaps.net/movies/MovieImages.php.*?" 
    }

    def getType(self, url):
        for type, reSupportedUrl in self.reSupportedUrls.items():
            if re.search(reSupportedUrl, url):
                return type
        return None

# エピソードクローラークラスの定義
class EpisodeCrawler:
    def crawl(self, url):
        pic_links = []
        current_url = url
        page_number = 1
        alt = None

        # エピソードタイプを取得して CDN と正規表現を設定
        match = re.search(r"https://fancaps.net/([a-zA-Z]+)/.*\?\d+-(.*)/(.*)", url)
        if not match:
            print("無効な URL 形式です。")
            return {"subfolder": "", "links": []}

        ep_type = match.group(1)
        subfolder = os.path.join(match.group(2), match.group(3))

        if ep_type == 'tv':
            cdn = 'tvcdn'
        else:
            cdn = 'ancdn'

        while current_url:
            try:
                response = requests.get(current_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0'})
                response.raise_for_status()  # HTTP エラーをチェック
            except requests.exceptions.RequestException as e:
                print(f"リクエストエラー: {e}")
                break

            try:
                beautiful_soup = BeautifulSoup(response.content, "html.parser")
            except Exception as e:
                print(f"ページの解析中にエラーが発生しました: {e}")
                break

            # 画像リンクを取得
            for img in beautiful_soup.find_all("img", src=re.compile("^https://"+ep_type+"thumbs.fancaps.net/")):
                img_src = img.get("src")
                img_alt = img.get("alt")
                if not alt:
                    alt = img_alt
                if alt == img_alt:
                    pic_links.append(img_src.replace("https://"+ep_type+"thumbs.fancaps.net/", "https://"+cdn+".fancaps.net/"))

            # 次のページの URL を取得
            next_page = beautiful_soup.find("a", href=lambda href: href and f"&page={page_number + 1}" in href)
            if next_page:
                page_number += 1
                current_url = f"{url}&page={page_number}"
            else:
                current_url = None

        return {
            'subfolder': subfolder,
            'links': pic_links
        }

# クローラークラスの定義
class Crawler:
    def crawl(self, url):
        Colors.print(f"{url} crawling started:", Colors.YELLOW)

        url_support = UrlSupport()
        url_type = url_support.getType(url)
        if url_type == 'season':
            print(f"\t\"{url_type}\" url detected")
            crawler = EpisodeCrawler()  # season_crawler を episode_crawler に変更
            output = crawler.crawl(url)
        elif url_type == 'episode':
            print(f"\t\"{url_type}\" url detected")
            crawler = EpisodeCrawler()
            output = [crawler.crawl(url)]
        elif url_type == 'movie':
            print(f"\t\"{url_type}\" url detected")
            crawler = EpisodeCrawler()  # movie_crawler を episode_crawler に変更
            output = [crawler.crawl(url)]
        else:
            return []

        Colors.print(f"{url} crawling finished.", Colors.YELLOW)
        return output

# ダウンローダークラスの定義
class Downloader:
    def downloadUrls(self, path, urls):
        os.makedirs(path, exist_ok=True)
        for i, url in tqdm(enumerate(urls), total=len(urls)):
            try:
                response = requests.get(url, stream=True)
                response.raise_for_status()
                file_name = os.path.basename(url)
                with open(os.path.join(path, file_name), 'wb') as file:
                    for chunk in response.iter_content(chunk_size=1024):
                        file.write(chunk)
            except requests.exceptions.RequestException as e:
                print(f"Error downloading {url}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('url', nargs='?', help='Url to start download')
    parser.add_argument('--output', type=str, default="Downloads", help='Path of folder')
    args = parser.parse_args()

    if not args.url:
        print("URL を指定してください。")
        exit(1)

    # クロール
    crawler = Crawler()
    links = crawler.crawl(args.url)

    # ダウンロード
    downloader = Downloader()
    for item in links:
        Colors.print(f"Download to {item['subfolder']} started:", Colors.YELLOW)
        path = os.path.join(args.output, item['subfolder'])
        downloader.downloadUrls(path, item['links'])
