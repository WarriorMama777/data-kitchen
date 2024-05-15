import requests
from bs4 import BeautifulSoup
from scraper.crawlers import episode_crawler
import re
from scraper.utils.colors import Colors
import time
from tqdm import tqdm  # 進行状況バーを表示するために tqdm をインポート

class SeasonCrawler:
    def __init__(self, url):
        self.url = url
        self.name = None
        self.current_url = url
        self.page = 1
        self.max_retries = 3

    def crawl(self):
        ep_links = []
        pic_links = []
        with tqdm(total=self.max_retries) as pbar:
            while self.current_url:
                retries = 0
                while retries < self.max_retries:
                    try:
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                        }
                        response = requests.get(self.current_url, headers=headers)
                        response.raise_for_status()  # HTTP エラーがあった場合に例外を送出
                        break
                    except requests.exceptions.RequestException as e:
                        Colors.print(f"Error occurred while opening the URL: {e}", Colors.RED)
                        retries += 1
                        time.sleep(2 ** retries)  # 指数バックオフでリトライ間隔を設定
                        if retries >= self.max_retries:
                            Colors.print(f"Max retries reached. Skipping {self.current_url}", Colors.YELLOW)
                            self.current_url = None
                            break
                    finally:
                        pbar.update(1)  # 進行状況バーを更新

                content = response.content
                beautiful_soup = self.parse_content(content)
                ep_links.extend(self.extract_episode_links(beautiful_soup))

                # 次のページへのリンクを確認する
                self.current_url = self.get_next_page_url(beautiful_soup)
                self.page += 1

        # エピソード リンクをクロールして画像リンクを取得する
        pic_links = self.crawl_episode_links(ep_links)

        return pic_links

    def parse_content(self, content):
        try:
            return BeautifulSoup(content, 'html.parser')
        except Exception as e:
            Colors.print(f"Error occurred while parsing the page: {e}", Colors.RED)
            return None

    def extract_episode_links(self, beautiful_soup):
        ep_links = []
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
        return ep_links

    def get_next_page_url(self, beautiful_soup):
        next_link = beautiful_soup.find("a", text=re.compile(r'Next', re.IGNORECASE), href=lambda href: href and href != "#")
        if next_link:
            return f"{self.url}&page={self.page}"
        else:
            return None

    def crawl_episode_links(self, ep_links):
        pic_links = []
        crawler = episode_crawler.EpisodeCrawler()
        with tqdm(total=len(ep_links)) as pbar:
            for ep_link in ep_links:
                retries = 0
                while retries < self.max_retries:
                    try:
                        episode_result = crawler.crawl(ep_link)
                        pic_links.append(episode_result)
                        Colors.print(f"\t{ep_link} crawled", Colors.GREEN)
                        break
                    except Exception as e:
                        Colors.print(f"Failed to crawl {ep_link}. Retrying... ({retries+1}/{self.max_retries})", Colors.YELLOW)
                        retries += 1
                        time.sleep(2 ** retries)  # 指数バックオフでリトライ間隔を設定
                        if retries >= self.max_retries:
                            Colors.print(f"Max retries reached. Skipping {ep_link}", Colors.RED)
                    finally:
                        pbar.update(1)  # 進行状況バーを更新

        return pic_links

# 使用例
crawler = SeasonCrawler(url="https://fancaps.net/anime/showimages.php?39590-_Tis_Time_for_Torture__Princess")
pic_links = crawler.crawl()
print(pic_links)
