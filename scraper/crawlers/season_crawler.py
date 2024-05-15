import requests
from bs4 import BeautifulSoup
from scraper.crawlers import episode_crawler
import re
from scraper.utils.colors import Colors
import time

class SeasonCrawler:
    url = None
    name = None

    def crawl(self, url):
        ep_links = []
        pic_links = []
        self.url = url
        current_url = self.url
        page = 1
        max_retries = 3  # リトライの最大回数

        while current_url:
            retries = 0
            while retries < max_retries:
                try:
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0'}
                    response = requests.get(current_url, headers=headers)
                    response.raise_for_status()  # HTTP エラーがあった場合に例外を送出
                    break
                except requests.exceptions.RequestException as e:
                    Colors.print(f"Error occurred while opening the URL: {e}", Colors.RED)
                    retries += 1
                    time.sleep(2 ** retries)  # 指数バックオフでリトライ間隔を設定
                    if retries >= max_retries:
                        Colors.print(f"Max retries reached. Skipping {current_url}", Colors.YELLOW)
                        current_url = None
                        break

            content = response.content

            try:
                beautiful_soup = BeautifulSoup(content, 'html.parser')
            except Exception as e:
                Colors.print(f"Error occurred while parsing the page: {e}", Colors.RED)
                break

            # ページ内のリンクをクロールする
            for dom_link in beautiful_soup.find_all('a', class_='btn', href=re.compile("^.*?/episodeimages.php\?")):
                href = dom_link.get('href')
                if href:
                    href = re.sub("^https?://", "https://", href)  # URL の正規化
                    match = re.search(r"https://fancaps.net/.*?/episodeimages.php\?\d+-(.*?)/", href)
                    if match:
                        if not self.name:
                            self.name = match.group(1)
                        if self.name == match.group(1):
                            ep_links.append(href)

            # 次のページへのリンクを確認する
            next_link = beautiful_soup.find("a", text=re.compile(r'Next', re.IGNORECASE), href=lambda href: href and href != "#")
            if next_link:
                page += 1
                current_url = url + f"&page={page}"
            else:
                current_url = None

        # エピソード リンクをクロールして画像リンクを取得する
        crawler = episode_crawler.EpisodeCrawler()
        for ep_link in ep_links:
            retries = 0
            while retries < max_retries:
                try:
                    episode_result = crawler.crawl(ep_link)
                    pic_links.append(episode_result)
                    Colors.print(f"\t{ep_link} crawled", Colors.GREEN)
                    break
                except Exception as e:
                    Colors.print(f"Failed to crawl {ep_link}. Retrying... ({retries+1}/{max_retries})", Colors.YELLOW)
                    retries += 1
                    time.sleep(2 ** retries)  # 指数バックオフでリトライ間隔を設定
                    if retries >= max_retries:
                        Colors.print(f"Max retries reached. Skipping {ep_link}", Colors.RED)

            # 最大リトライ回数に達した場合はエラーとして扱い、次のリンクに進む
            # ...

        return pic_links
