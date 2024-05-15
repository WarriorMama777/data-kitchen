from bs4 import BeautifulSoup
from scraper.crawlers import episode_crawler
import re
import urllib.request
import urllib.error
from scraper.utils.colors import Colors
import time

class SeasonCrawler:
    url = None
    name = None
    max_retries = 3  # 最大リトライ回数

    def crawl(self, url):
        epLinks = []
        picLinks = []
        self.url = url
        currentUrl = self.url
        page = 1

        while currentUrl:
            attempt = 0
            while attempt < self.max_retries:
                try:
                    request = urllib.request.Request(currentUrl, headers={'User-Agent': 'Mozilla/5.0'})
                    content = urllib.request.urlopen(request)
                    # ページの読み込みに成功したらリトライループを抜ける
                    break
                except urllib.error.URLError as e:
                    Colors.print(f"Error occurred while opening the URL: {e.reason} - Retrying {attempt+1}/{self.max_retries}", Colors.RED)
                    attempt += 1
                    time.sleep(1)  # リトライ間に少し待つ
                except urllib.error.HTTPError as e:
                    Colors.print(f"HTTP Error: {e.code} {e.reason} - Retrying {attempt+1}/{self.max_retries}", Colors.RED)
                    attempt += 1
                    time.sleep(1)
            if attempt == self.max_retries:
                # 最大リトライ回数に達した場合、次のURLへ移行
                Colors.print("Max retries reached. Skipping to next URL.", Colors.YELLOW)
                break

            try:
                beautifulSoup = BeautifulSoup(content, 'html.parser')
            except Exception as e:
                Colors.print(f"Error occurred while parsing the page: {e}", Colors.RED)
                break

            for DOMLink in beautifulSoup.find_all('a', class_='btn', href=re.compile("^.*?/episodeimages.php\?")):
                href = DOMLink.get('href')
                if href:
                    if not re.match("^https://.*?/episodeimages.php\?", href):
                        href = 'https://fancaps.net' + DOMLink.get('href')

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

        crawler = episode_crawler.EpisodeCrawler()
        for epLink in epLinks:
            attempt = 0
            while attempt < self.max_retries:
                try:
                    episodeResult = crawler.crawl(epLink)
                    picLinks.append(episodeResult)
                    Colors.print(f"\t{epLink} crawled", Colors.GREEN)
                    # 成功したら次へ
                    break
                except Exception as e:
                    Colors.print(f"Failed to crawl {epLink}: {e} - Retrying {attempt+1}/{self.max_retries}", Colors.RED)
                    attempt += 1
                    time.sleep(1)  # リトライ間に少し待つ
            if attempt == self.max_retries:
                Colors.print(f"Max retries reached for {epLink}. Skipping.", Colors.YELLOW)

        return picLinks
