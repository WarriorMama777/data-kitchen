import argparse
import os
import re
import requests
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
                response = requests.get(current_url, headers={'User-Agent': 'Mozilla/5.0'})
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

# SeasonCrawler クラスの定義
class SeasonCrawler:
    def __init__(self):
        self.name = None

    def crawl(self, url):
        epLinks = []
        picLinks = []
        currentUrl = url
        page = 1

        while currentUrl:
            try:
                response = requests.get(currentUrl, headers={'User-Agent': 'Mozilla/5.0'})
                response.raise_for_status()
                content = response.content
            except requests.exceptions.RequestException as e:
                print(f"Error occurred while opening the URL: {e}", 'red')
                break

            beautifulSoup = BeautifulSoup(content, 'html.parser')

            for DOMLink in beautifulSoup.find_all('a', class_='btn', href=re.compile("^.*?/episodeimages.php\?")):
                href = DOMLink.get('href')
                if href:
                    if not re.match("^https://.*?/episodeimages.php\?", href):
                        href = 'https://fancaps.net' + href

                    match = re.search(r"https://fancaps.net/.*?/episodeimages.php\?\d+-(.*?)/", href)
                    if match:
                        if not self.name:
                            self.name = match.group(1)
                        if self.name == match.group(1):
                            epLinks.append(href)
            if beautifulSoup.find("a", text=re.compile(r'Next', re.IGNORECASE), href=lambda href: href and href != "#"):
                page += 1
                currentUrl = url + f"&page={page}"
            else:
                currentUrl = None

        episodeCrawler = EpisodeCrawler()
        for epLink in epLinks:
            episodeResult = episodeCrawler.crawl(epLink)
            picLinks.extend(episodeResult)  # epLinkから取得した画像リンクを追加

        return {"subfolder": self.name, "links": picLinks}

# MovieCrawler クラスの定義
class MovieCrawler:
    def crawl(self, url):
        picLinks = []
        currentUrl = url
        pageNumber = 1
        alt = None

        try:
            match = re.search(r"https://fancaps.net\/.*\?name=(.*)&", url)
            if match:
                subfolder = match.group(1)
            else:
                raise ValueError("URL does not contain a valid subfolder name.")
        except ValueError as e:
            print(f"Error extracting subfolder: {e}")
            return

        while currentUrl:
            try:
                response = requests.get(currentUrl, headers={'User-Agent': 'Mozilla/5.0'})
                beautifulSoup = BeautifulSoup(response.text, "html.parser")
            except Exception as e:
                print(f"Error fetching or parsing page: {e}")
                break

            for img in beautifulSoup.find_all("img", src=re.compile("^https://moviethumbs.fancaps.net/")):
                imgSrc = img.get("src")
                imgAlt = img.get("alt")
                if not alt:
                    alt = imgAlt
                if alt == imgAlt:
                    picLinks.append(imgSrc.replace("https://moviethumbs.fancaps.net/", "https://mvcdn.fancaps.net/"))

            try:
                next = url.replace(f'https://fancaps.net/movies/','') +f"&page={pageNumber + 1}"
                nextPage = beautifulSoup.find("a", href=next)
                if nextPage:
                    pageNumber += 1
                    currentUrl = url + f"&page={pageNumber}"
                else:
                    currentUrl = None
            except Exception as e:
                print(f"Error processing next page: {e}")
                break

        return {
            'subfolder': subfolder,
            'links': picLinks
        }

# クローラークラスの定義
class Crawler:
    def crawl(self, url):
        print(f"{url} crawling started:")

        url_support = UrlSupport()
        url_type = url_support.getType(url)
        # Crawler クラス内の変更点
        if url_type == 'season':
            print(f"\t\"{url_type}\" url detected")
            crawler = SeasonCrawler()  # SeasonCrawlerのインスタンス化
            output = [crawler.crawl(url)]  # SeasonCrawlerのcrawlメソッドの戻り値はリスト内に格納
        elif url_type == 'episode':
            print(f"\t\"{url_type}\" url detected")
            crawler = EpisodeCrawler()
            output = [crawler.crawl(url)]
        elif url_type == 'movie':
            print(f"\t\"{url_type}\" url detected")
            crawler = MovieCrawler()
            output = [crawler.crawl(url)]
        else:
            return []

        print(f"{url} crawling finished.")
        return output

# ダウンローダークラスの定義
class Downloader:
    def downloadUrl(self, path, url):
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            file_name = os.path.basename(url)
            with open(os.path.join(path, file_name), 'wb') as file:
                for chunk in response.iter_content(chunk_size=1024):
                    file.write(chunk)
        except requests.exceptions.RequestException as e:
            print(f"Error downloading {url}: {e}")

    def downloadUrls(self, path, urls):
        os.makedirs(path, exist_ok=True)
        with ThreadPoolExecutor(max_workers=5) as executor:
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
