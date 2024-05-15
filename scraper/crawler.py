from scraper.url_support import UrlSupport
from scraper.crawlers import episode_crawler, season_crawler, movie_crawler
from scraper.utils.colors import Colors
import time
class Crawler:
    def crawl(self, url, max_retries=3, delay=2):
        Colors.print(f"{url} crawling started:", Colors.YELLOW)

        urlSupport = UrlSupport()
        urlType = urlSupport.getType(url)
        output = []
        retries = 0

        while retries < max_retries:
            try:
                if urlType == 'season':
                    Colors.print(f"\t\"{urlType}\" url detected", Colors.GREEN)
                    crawler = season_crawler.SeasonCrawler()
                    output = crawler.crawl(url)
                elif urlType == 'episode':
                    Colors.print(f"\t\"{urlType}\" url detected", Colors.GREEN)
                    crawler = episode_crawler.EpisodeCrawler()
                    output = [crawler.crawl(url)]
                elif urlType == 'movie':
                    Colors.print(f"\t\"{urlType}\" url detected", Colors.GREEN)
                    crawler = movie_crawler.MovieCrawler()
                    output = [crawler.crawl(url)]
                else:
                    Colors.print(f"Unsupported URL type: {urlType}", Colors.RED)
                    # サポートされていないURLタイプの場合はリトライせずにループを抜ける
                    break
                # 成功したらループを抜ける
                break
            except Exception as e:
                retries += 1
                Colors.print(f"An error occurred during crawling: {e}", Colors.RED)
                Colors.print(f"Retrying... ({retries}/{max_retries})", Colors.YELLOW)
                time.sleep(delay)  # 指定された遅延時間を待つ
        else:
            # リトライが最大回数に達した場合
            Colors.print(f"Failed to crawl {url} after {max_retries} attempts.", Colors.RED)
 
    def crawl_season_episodes(self, url, max_retries=3, delay=2):
            Colors.print(f"{url} season episode crawling started:", Colors.YELLOW)

            url_support = UrlSupport()
            if url_support.getType(url) != 'season':
                Colors.print(f"Unsupported URL type: {url_support.getType(url)}", Colors.RED)
                return []

            retries = 0
            season_episodes = []
            while retries < max_retries:
                try:
                    crawler = season_crawler.SeasonCrawler()
                    season_episodes = crawler.crawl(url)
                    break
                except Exception as e:
                    retries += 1
                    Colors.print(f"An error occurred during crawling: {e}", Colors.RED)
                    Colors.print(f"Retrying... ({retries}/{max_retries})", Colors.YELLOW)
                    time.sleep(delay)

            Colors.print(f"{url} season episode crawling finished.", Colors.YELLOW)
            return season_episodes
