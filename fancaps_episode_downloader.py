import argparse
import os
import re
import requests
import time
import random
from bs4 import BeautifulSoup
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://fancaps.net/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }

    def crawl(self, url):
        pic_links = []
        current_url = url
        page_number = 1
        alt = None

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
                # リクエスト間に遅延を追加（ウェブサイトに負荷をかけないため）
                time.sleep(random.uniform(1.0, 3.0))
                
                response = self.session.get(current_url, headers=self.headers)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                print(f"リクエストエラー: {e}")
                break

            beautiful_soup = BeautifulSoup(response.content, "html.parser")

            for img in beautiful_soup.find_all("img", src=re.compile("^https://"+ep_type+"thumbs.fancaps.net/")):
                img_src = img.get("src")
                img_alt = img.get("alt")
                if not alt:
                    alt = img_alt
                if alt == img_alt:
                    pic_links.append(img_src.replace("https://"+ep_type+"thumbs.fancaps.net/", "https://"+cdn+".fancaps.net/"))

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
        print(f"{url} crawling started:")

        url_support = UrlSupport()
        url_type = url_support.getType(url)
        if url_type == 'season':
            print(f"\t\"{url_type}\" url detected")
            crawler = EpisodeCrawler()
            output = crawler.crawl(url)
        elif url_type == 'episode':
            print(f"\t\"{url_type}\" url detected")
            crawler = EpisodeCrawler()
            output = [crawler.crawl(url)]
        elif url_type == 'movie':
            print(f"\t\"{url_type}\" url detected")
            crawler = EpisodeCrawler()
            output = [crawler.crawl(url)]
        else:
            return []

        print(f"{url} crawling finished.")
        return output

# ダウンローダークラスの定義
class Downloader:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://fancaps.net/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }

    def downloadUrl(self, path, url):
        try:
            # リクエスト間に遅延を追加（ウェブサイトに負荷をかけないため）
            time.sleep(random.uniform(0.5, 2.0))
            
            response = self.session.get(url, headers=self.headers, stream=True)
            response.raise_for_status()
            file_name = os.path.basename(url)
            with open(os.path.join(path, file_name), 'wb') as file:
                for chunk in response.iter_content(chunk_size=1024):
                    file.write(chunk)
        except requests.exceptions.RequestException as e:
            print(f"Error downloading {url}: {e}")

    def downloadUrls(self, path, urls):
        os.makedirs(path, exist_ok=True)
        # 同時接続数を減らして負荷を軽減
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_url = {executor.submit(self.downloadUrl, path, url): url for url in urls}
            for future in tqdm(as_completed(future_to_url), total=len(urls)):
                future.result()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('url', nargs='?', help='Url to start download')
    parser.add_argument('--output', type=str, default="Downloads", help='Path of folder')
    args = parser.parse_args()

    if not args.url:
        print("URL を指定してください。")
        exit(1)

    crawler = Crawler()
    links = crawler.crawl(args.url)

    downloader = Downloader()
    for item in links:
        print(f"Download to {item['subfolder']} started:")
        path = os.path.join(args.output, item['subfolder'])
        downloader.downloadUrls(path, item['links'])
