#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import time
import argparse
import threading
import concurrent.futures
from urllib.error import HTTPError, URLError
from urllib.request import urlopen, Request
from http.client import IncompleteRead
from bs4 import BeautifulSoup
from tqdm import tqdm


# Console Colors Utility
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'

    @staticmethod
    def print(message, color):
        print(f"{color}{message}{Colors.RESET}")


# URL Support Class
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


# Episode Crawler Class
class EpisodeCrawler:
    def crawl(self, url):
        picLinks = []  # List to store the picture links
        currentUrl = url  # Current URL to crawl
        pageNumber = 1  # Initialize page number
        alt = None  # Initialize alt attribute value for images

        # Extract episode type, subfolder information from URL
        match = re.search(r"https://fancaps.net\/([a-zA-Z]+)\/.*\?\d+-(.*?)/(.*)", url)
        if not match:
            print("Invalid URL format.")
            return {"subfolder": "", "links": []}

        epType = match.group(1)  # Episode type (tv or anime)
        subfolder = os.path.join(match.group(2), match.group(3))  # Construct subfolder path

        # Set CDN based on episode type
        if epType == 'tv':
            cdn = 'tvcdn'
        else:
            cdn = 'ancdn'

        while currentUrl:
            try:
                # Make a request to the current URL
                request = Request(currentUrl, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0'})
                page = urlopen(request)
            except URLError as e:
                print(f"Error opening URL: {e.reason}")
                break
            except HTTPError as e:
                print(f"HTTP Error: {e.code} {e.reason}")
                break

            try:
                # Parse the HTML content
                beautifulSoup = BeautifulSoup(page, "html.parser")
            except Exception as e:
                print(f"Error parsing page: {e}")
                break

            # Find all image tags with a specific source pattern
            for img in beautifulSoup.find_all("img", src=re.compile(f"^https://{epType}thumbs.fancaps.net/")):
                imgSrc = img.get("src")
                imgAlt = img.get("alt")
                if not alt:
                    alt = imgAlt  # Set alt if not already set
                if alt == imgAlt:
                    # Add image source to list, replacing the domain with the CDN domain
                    picLinks.append(imgSrc.replace(f"https://{epType}thumbs.fancaps.net/", f"https://{cdn}.fancaps.net/"))

            # Check for a next page link
            nextPage = beautifulSoup.find("a", href=lambda href: href and f"&page={pageNumber + 1}" in href)
            if nextPage:
                pageNumber += 1  # Increment page number
                currentUrl = f"{url}&page={pageNumber}"  # Update current URL
            else:
                currentUrl = None  # No more pages, stop crawling

        return {
            'subfolder': subfolder,  # Return subfolder path
            'links': picLinks  # Return list of picture links
        }


# Movie Crawler Class
class MovieCrawler:
    def crawl(self, url):
        picLinks = []
        currentUrl = url
        pageNumber = 1
        alt = None

        try:
            # Extract subfolder name from URL
            match = re.search(r"https://fancaps.net\/.*\?name=(.*)&", url)
            if match:
                subfolder = match.group(1)
            else:
                raise ValueError("URL does not contain a valid subfolder name.")
        except ValueError as e:
            print(f"Error extracting subfolder: {e}")
            return {"subfolder": "", "links": []}

        while currentUrl:
            try:
                # Fetch and parse the webpage
                request = Request(currentUrl, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0'})
                page = urlopen(request)
                beautifulSoup = BeautifulSoup(page, "html.parser")
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
                # Generate and verify the existence of the next page URL
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


# Season Crawler Class
class SeasonCrawler:
    def crawl(self, url):
        epLinks = []
        picLinks = []
        self.url = url
        self.name = None
        currentUrl = url
        page = 1

        while currentUrl:
            try:
                request = Request(currentUrl, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0'})
                content = urlopen(request)
            except URLError as e:
                Colors.print(f"Error occurred while opening the URL: {e.reason}", Colors.RED)
                break
            except HTTPError as e:
                Colors.print(f"HTTP Error: {e.code} {e.reason}", Colors.RED)
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
            
            nextPageLink = beautifulSoup.find("a", text=re.compile(r'Next', re.IGNORECASE), href=lambda href: href and href != "#")
            if nextPageLink:
                page += 1
                currentUrl = url + f"&page={page}"
            else:
                currentUrl = None

        episodeCrawler = EpisodeCrawler()
        for epLink in epLinks:
            try:
                episodeResult = episodeCrawler.crawl(epLink)
                picLinks.append(episodeResult)
                Colors.print(f"\t{epLink} crawled", Colors.GREEN)
            except Exception as e:
                Colors.print(f"Failed to crawl {epLink}: {e}", Colors.RED)

        return picLinks


# Main Crawler Class
class Crawler:
    def crawl(self, url):
        Colors.print(f"{url} crawling started:", Colors.YELLOW)

        urlSupport = UrlSupport()
        urlType = urlSupport.getType(url)
        
        if urlType == 'season':
            print(f"\t\"{urlType}\" url detected")
            crawler = SeasonCrawler()
            output = crawler.crawl(url)
        elif urlType == 'episode':
            print(f"\t\"{urlType}\" url detected")
            crawler = EpisodeCrawler()
            output = [crawler.crawl(url)]
        elif urlType == 'movie':
            print(f"\t\"{urlType}\" url detected")
            crawler = MovieCrawler()
            output = [crawler.crawl(url)]
        else:
            Colors.print(f"Unsupported URL type: {url}", Colors.RED)
            return []

        Colors.print(f"{url} crawling finished.", Colors.YELLOW)
        return output


# Download Function
def _download(url, path, timeout=10, attempts=3, delay=0.01):
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0'})
    filename = os.path.join(path, url.split('/')[-1])

    for attempt in range(attempts):
        try:
            with urlopen(req, timeout=timeout) as response, open(filename, 'wb') as output:
                data = response.read()
                output.write(data)
                break  # Exit the loop if download is successful
        except (HTTPError, URLError, IncompleteRead) as e:
            print(f"An error occurred during download: {e}. Retrying...({attempt+1}/{attempts})")
            time.sleep(delay)  # Wait a bit before retrying after error
        except TimeoutError as e:
            print(f"Timeout Error: {e}. Retrying...({attempt+1}/{attempts})")
            time.sleep(delay)
        else:
            break  # Exit the loop if no other exceptions occur
        
        if attempt == attempts - 1:
            print(f"Download failed after {attempts} attempts: {url}")

    time.sleep(delay)  # Pause between downloads


# Downloader Class
class Downloader:
    def downloadUrls(self, path, urls, delay=1):
        os.makedirs(path, exist_ok=True)

        total = len(urls)
        lock = threading.Lock()

        def update_progress():
            with lock:
                pbar.update(1)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            with tqdm(total=total, desc=f"Downloading to {os.path.basename(path)}") as pbar:
                futures = []
                for url in urls:
                    future = executor.submit(_download, url, path, delay=delay)
                    future.add_done_callback(lambda _: update_progress())
                    futures.append(future)

                for future in concurrent.futures.as_completed(futures):
                    future.result()


# Main Application
def main():
    parser = argparse.ArgumentParser(description="FanCaps Episode Downloader - Download images from FanCaps.net")
    parser.add_argument('url', nargs='?', help='URL to start download (episode, season, or movie)')
    parser.add_argument('--output', type=str, default="Downloads", help='Path of output folder')
    args = parser.parse_args()

    if not args.url:
        parser.print_help()
        return

    # Crawl
    crawler = Crawler()
    links = crawler.crawl(args.url)

    if not links:
        Colors.print("No links found to download. Please check the URL and try again.", Colors.RED)
        return

    # Download
    downloader = Downloader()
    for item in links:
        if item['links']:
            Colors.print(f"Download to {item['subfolder']} started: {len(item['links'])} images found", Colors.YELLOW)
            path = os.path.join(args.output, item['subfolder'])
            downloader.downloadUrls(path, item['links'])
            Colors.print(f"Download to {item['subfolder']} completed!", Colors.GREEN)
        else:
            Colors.print(f"No images found for {item['subfolder']}", Colors.RED)

    Colors.print("All downloads completed successfully!", Colors.GREEN)


if __name__ == "__main__":
    main()
