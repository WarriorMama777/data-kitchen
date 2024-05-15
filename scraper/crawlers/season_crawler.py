from bs4 import BeautifulSoup
from scraper.crawlers import episode_crawler
import re
import urllib.request
import urllib.error
from scraper.utils.colors import Colors

class SeasonCrawler:
    url = None
    name = None

    def crawl(self, url, download_func):
        ep_links = []
        pic_links = []
        self.url = url
        current_url = self.url
        page = 1

        while current_url:
            try:
                request = urllib.request.Request(current_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0'})
                content = urllib.request.urlopen(request)
            except urllib.error.URLError as e:
                Colors.print(f"Error occurred while opening the URL: {e.reason}", Colors.RED)
                break
            except urllib.error.HTTPError as e:
                Colors.print(f"HTTP Error: {e.code} {e.reason}", Colors.RED)
                break

            try:
                beautiful_soup = BeautifulSoup(content, 'html.parser')
            except Exception as e:
                Colors.print(f"Error occurred while parsing the page: {e}", Colors.RED)
                break

            for dom_link in beautiful_soup.find_all('a', class_='btn', href=re.compile("^.*?/episodeimages.php\?")):
                href = dom_link.get('href')
                if href:
                    if not re.match("^https://.*?/episodeimages.php\?", href):
                        href = 'https://fancaps.net' + dom_link.get('href')

                    match = re.search(r"https://fancaps.net/.*?/episodeimages.php\?\d+-(.*?)/", href)
                    if match:
                        if not self.name:
                            self.name = match.group(1)
                        if self.name == match.group(1):
                            ep_links.append(href)

            if beautiful_soup.find("a", text=re.compile(r'Next', re.IGNORECASE), href=lambda href: href and href != "#"):
                page += 1
                current_url = url + f"&page={page}"
            else:
                current_url = None

            for ep_link in ep_links:
                try:
                    episode_result = episode_crawler.EpisodeCrawler().crawl(ep_link)
                    pic_links.append(episode_result)
                    Colors.print(f"\t{ep_link} crawled", Colors.GREEN)
                    download_func(episode_result)  # Call the download function for each episode
                except Exception as e:
                    Colors.print(f"Failed to crawl {ep_link}: {e}", Colors.RED)

        return pic_links
