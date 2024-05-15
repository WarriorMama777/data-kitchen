import argparse
from scraper.crawler import Crawler
from scraper.downloader import Downloader
from scraper.utils.colors import Colors
import os

parser = argparse.ArgumentParser()
parser.add_argument('url', nargs='?', help='Url to start scraping')
parser.add_argument('--output', type=str, default="Downloads", help='Path of the output folder')
args = parser.parse_args()

if __name__ == "__main__":
    crawler = Crawler()
    downloader = Downloader()

    # Crawl and download each episode sequentially
    episode_links = []
    for episode_url in crawler.crawl_season_episodes(args.url):
        episode_links.extend(episode_url['links'])
        Colors.print(f"Crawled episode: {episode_url['subfolder']}", Colors.GREEN)

        # Download episode immediately after crawling
        downloader.download_episode(args.output, episode_url['subfolder'], episode_url['links'])
        Colors.print(f"Downloaded episode: {episode_url['subfolder']}", Colors.GREEN)
