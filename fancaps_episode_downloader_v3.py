#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import time
import signal
import logging
import argparse
import threading
import traceback
import concurrent.futures
from urllib.error import HTTPError, URLError
from urllib.request import urlopen, Request
from http.client import IncompleteRead
from bs4 import BeautifulSoup
from tqdm import tqdm
import sys

# グローバル変数
shutdown_flag = False
SUPPORTED_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif']
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0'

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('fancaps_downloader')


# シグナルハンドラー
def signal_handler(sig, frame):
    global shutdown_flag
    logging.warning("中断シグナルを受信しました。安全に停止します...")
    shutdown_flag = True


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
    def __init__(self, debug=False):
        self.debug = debug

    def crawl(self, url):
        if self.debug:
            logger.info(f"エピソードクローラー開始: {url}")
            
        picLinks = []  # List to store the picture links
        currentUrl = url  # Current URL to crawl
        pageNumber = 1  # Initialize page number
        alt = None  # Initialize alt attribute value for images
        subfolder = "unknown"  # Default subfolder name

        try:
            # Extract episode type, subfolder information from URL
            match = re.search(r"https://fancaps.net\/([a-zA-Z]+)\/.*\?\d+-(.*?)/(.*)", url)
            if not match:
                logger.error(f"URLフォーマットが無効です: {url}")
                return {"subfolder": subfolder, "links": []}

            epType = match.group(1)  # Episode type (tv or anime)
            subfolder = os.path.join(match.group(2), match.group(3))  # Construct subfolder path
            logger.debug(f"エピソードタイプ: {epType}, サブフォルダ: {subfolder}")

            # Set CDN based on episode type
            if epType == 'tv':
                cdn = 'tvcdn'
            else:
                cdn = 'ancdn'

            page_count = 0
            while currentUrl and not shutdown_flag:
                try:
                    # Make a request to the current URL
                    logger.debug(f"ページ {pageNumber} のクロール: {currentUrl}")
                    request = Request(currentUrl, headers={'User-Agent': USER_AGENT})
                    with urlopen(request, timeout=15) as page:
                        # Parse the HTML content
                        beautifulSoup = BeautifulSoup(page, "html.parser", from_encoding='utf-8')
                        
                    page_count += 1
                    
                    # Find all image tags with a specific source pattern
                    for img in beautifulSoup.find_all("img", src=re.compile(f"^https://{epType}thumbs.fancaps.net/")):
                        imgSrc = img.get("src")
                        imgAlt = img.get("alt")
                        if not alt:
                            alt = imgAlt  # Set alt if not already set
                        if alt == imgAlt:
                            # Add image source to list, replacing the domain with the CDN domain
                            cdn_url = imgSrc.replace(f"https://{epType}thumbs.fancaps.net/", f"https://{cdn}.fancaps.net/")
                            
                            # 画像形式のチェック
                            _, ext = os.path.splitext(cdn_url)
                            if ext.lower() in SUPPORTED_IMAGE_FORMATS:
                                picLinks.append(cdn_url)
                                logger.debug(f"画像リンクを追加: {cdn_url}")

                    # Check for a next page link
                    nextPage = beautifulSoup.find("a", href=lambda href: href and f"&page={pageNumber + 1}" in href)
                    if nextPage:
                        pageNumber += 1  # Increment page number
                        currentUrl = f"{url}&page={pageNumber}"  # Update current URL
                    else:
                        currentUrl = None  # No more pages, stop crawling
                        
                except (HTTPError, URLError) as e:
                    logger.error(f"ネットワークエラー: {e}")
                    if hasattr(e, 'code') and e.code == 429:  # Too Many Requests
                        logger.warning("レート制限の可能性があります。30秒待機します...")
                        time.sleep(30)
                        continue
                    else:
                        break
                except Exception as e:
                    logger.error(f"ページ処理中のエラー: {e}")
                    if self.debug:
                        logger.error(traceback.format_exc())
                    break

            logger.info(f"エピソードのクロール完了: {page_count} ページ, {len(picLinks)} 画像")

        except Exception as e:
            logger.error(f"クロールプロセス全体でエラーが発生しました: {e}")
            if self.debug:
                logger.error(traceback.format_exc())

        return {
            'subfolder': subfolder,  # Return subfolder path
            'links': picLinks  # Return list of picture links
        }


# Movie Crawler Class
class MovieCrawler:
    def __init__(self, debug=False):
        self.debug = debug
        
    def crawl(self, url):
        if self.debug:
            logger.info(f"映画クローラー開始: {url}")
            
        picLinks = []
        currentUrl = url
        pageNumber = 1
        alt = None
        subfolder = "unknown_movie"

        try:
            # Extract subfolder name from URL
            match = re.search(r"https://fancaps.net\/.*\?name=(.*)&", url)
            if match:
                subfolder = match.group(1)
                logger.debug(f"抽出されたサブフォルダ名: {subfolder}")
            else:
                logger.warning(f"URLから有効なサブフォルダ名を抽出できません: {url}")
                
            page_count = 0
            while currentUrl and not shutdown_flag:
                try:
                    # Fetch and parse the webpage
                    logger.debug(f"ページ {pageNumber} のクロール: {currentUrl}")
                    request = Request(currentUrl, headers={'User-Agent': USER_AGENT})
                    with urlopen(request, timeout=15) as page:
                        beautifulSoup = BeautifulSoup(page, "html.parser", from_encoding='utf-8')
                    
                    page_count += 1
                    
                    for img in beautifulSoup.find_all("img", src=re.compile("^https://moviethumbs.fancaps.net/")):
                        imgSrc = img.get("src")
                        imgAlt = img.get("alt")
                        if not alt:
                            alt = imgAlt
                        if alt == imgAlt:
                            cdn_url = imgSrc.replace("https://moviethumbs.fancaps.net/", "https://mvcdn.fancaps.net/")
                            
                            # 画像形式のチェック
                            _, ext = os.path.splitext(cdn_url)
                            if ext.lower() in SUPPORTED_IMAGE_FORMATS:
                                picLinks.append(cdn_url)
                                logger.debug(f"画像リンクを追加: {cdn_url}")
                    
                    # Generate and verify the existence of the next page URL
                    next_path = url.replace('https://fancaps.net/movies/','') + f"&page={pageNumber + 1}"
                    nextPage = beautifulSoup.find("a", href=next_path)
                    if nextPage:
                        pageNumber += 1
                        currentUrl = url + f"&page={pageNumber}"
                    else:
                        currentUrl = None
                        
                except (HTTPError, URLError) as e:
                    logger.error(f"ネットワークエラー: {e}")
                    if hasattr(e, 'code') and e.code == 429:  # Too Many Requests
                        logger.warning("レート制限の可能性があります。30秒待機します...")
                        time.sleep(30)
                        continue
                    else:
                        break
                except Exception as e:
                    logger.error(f"ページ処理中のエラー: {e}")
                    if self.debug:
                        logger.error(traceback.format_exc())
                    break
            
            logger.info(f"映画のクロール完了: {page_count} ページ, {len(picLinks)} 画像")
            
        except Exception as e:
            logger.error(f"クロールプロセス全体でエラーが発生しました: {e}")
            if self.debug:
                logger.error(traceback.format_exc())

        return {
            'subfolder': subfolder,
            'links': picLinks
        }


# Season Crawler Class
class SeasonCrawler:
    def __init__(self, debug=False):
        self.debug = debug
        self.url = None
        self.name = None
        
    def crawl(self, url):
        if self.debug:
            logger.info(f"シーズンクローラー開始: {url}")
            
        epLinks = []
        picLinks = []
        self.url = url
        self.name = None
        currentUrl = url
        page = 1

        try:
            page_count = 0
            while currentUrl and not shutdown_flag:
                try:
                    logger.debug(f"ページ {page} のクロール: {currentUrl}")
                    request = Request(currentUrl, headers={'User-Agent': USER_AGENT})
                    with urlopen(request, timeout=15) as content:
                        beautifulSoup = BeautifulSoup(content, 'html.parser', from_encoding='utf-8')
                    
                    page_count += 1
                    
                    for DOMLink in beautifulSoup.find_all('a', class_='btn', href=re.compile("^.*?/episodeimages.php\?")):
                        href = DOMLink.get('href')
                        if href:
                            if not re.match("^https://.*?/episodeimages.php\?", href):
                                href = 'https://fancaps.net' + DOMLink.get('href')

                            match = re.search(r"https://fancaps.net/.*?/episodeimages.php\?\d+-(.*?)/", href)
                            if match:
                                season_name = match.group(1)
                                if not self.name:
                                    self.name = season_name
                                    logger.debug(f"シーズン名を設定: {self.name}")
                                if self.name == season_name:
                                    epLinks.append(href)
                                    logger.debug(f"エピソードリンクを追加: {href}")
                    
                    nextPageLink = beautifulSoup.find("a", text=re.compile(r'Next', re.IGNORECASE), href=lambda href: href and href != "#")
                    if nextPageLink:
                        page += 1
                        currentUrl = url + f"&page={page}"
                    else:
                        currentUrl = None
                        
                except (HTTPError, URLError) as e:
                    logger.error(f"ネットワークエラー: {e}")
                    if hasattr(e, 'code') and e.code == 429:  # Too Many Requests
                        logger.warning("レート制限の可能性があります。30秒待機します...")
                        time.sleep(30)
                        continue
                    else:
                        break
                except Exception as e:
                    logger.error(f"ページ処理中のエラー: {e}")
                    if self.debug:
                        logger.error(traceback.format_exc())
                    break
            
            logger.info(f"シーズンページのクロール完了: {page_count} ページ, {len(epLinks)} エピソード")
            
            # クロールしたエピソードリンクをクロールする
            episodeCrawler = EpisodeCrawler(debug=self.debug)
            
            if epLinks:
                Colors.print(f"{len(epLinks)}個のエピソードリンクが見つかりました。各エピソードをクロールします...", Colors.BLUE)
                
                # tqdmでエピソードのクロール進捗を表示
                for epLink in tqdm(epLinks, desc="エピソードのクロール中", unit="エピソード"):
                    if shutdown_flag:
                        logger.warning("中断シグナルを受信しました。エピソードクロールを停止します。")
                        break
                        
                    try:
                        episodeResult = episodeCrawler.crawl(epLink)
                        if episodeResult['links']:
                            picLinks.append(episodeResult)
                            Colors.print(f"\t{epLink} クロール完了: {len(episodeResult['links'])}画像", Colors.GREEN)
                        else:
                            Colors.print(f"\t{epLink} クロール完了: 画像が見つかりませんでした", Colors.YELLOW)
                    except Exception as e:
                        Colors.print(f"エピソードのクロールに失敗しました {epLink}: {e}", Colors.RED)
                        if self.debug:
                            logger.error(traceback.format_exc())
            else:
                logger.warning("エピソードリンクが見つかりませんでした")
                
        except Exception as e:
            logger.error(f"シーズンクロール全体でエラーが発生しました: {e}")
            if self.debug:
                logger.error(traceback.format_exc())

        return picLinks


# Main Crawler Class
class Crawler:
    def __init__(self, debug=False):
        self.debug = debug
        
    def crawl(self, url):
        Colors.print(f"{url} クロール開始:", Colors.YELLOW)
        logger.info(f"URL {url} のクローリングを開始します")

        urlSupport = UrlSupport()
        urlType = urlSupport.getType(url)
        
        if not urlType:
            Colors.print(f"サポートされていないURLタイプです: {url}", Colors.RED)
            logger.error(f"サポートされていないURLタイプ: {url}")
            return []
            
        try:
            if urlType == 'season':
                print(f"\t\"{urlType}\" URLが検出されました")
                crawler = SeasonCrawler(debug=self.debug)
                output = crawler.crawl(url)
            elif urlType == 'episode':
                print(f"\t\"{urlType}\" URLが検出されました")
                crawler = EpisodeCrawler(debug=self.debug)
                output = [crawler.crawl(url)]
            elif urlType == 'movie':
                print(f"\t\"{urlType}\" URLが検出されました")
                crawler = MovieCrawler(debug=self.debug)
                output = [crawler.crawl(url)]
            else:
                Colors.print(f"サポートされていないURLタイプです: {url}", Colors.RED)
                logger.error(f"クロールできません: {url}")
                return []

            Colors.print(f"{url} クロール完了", Colors.YELLOW)
            logger.info(f"URL {url} のクローリングが完了しました")
            
            total_images = sum(len(item['links']) for item in output if item and 'links' in item)
            logger.info(f"合計 {len(output)} アイテム、{total_images} 画像が見つかりました")
            
            return output
            
        except Exception as e:
            Colors.print(f"クロール中にエラーが発生しました: {e}", Colors.RED)
            logger.error(f"クロール中に例外が発生しました: {e}")
            if self.debug:
                logger.error(traceback.format_exc())
            return []


# Download Function
def _download(url, path, timeout=30, max_attempts=5, base_delay=1.0, max_delay=30.0):
    """
    画像をダウンロードする関数 (再試行機能付き)
    
    引数:
        url: ダウンロードするURL
        path: 保存先パス
        timeout: 接続タイムアウト (秒)
        max_attempts: 最大再試行回数
        base_delay: 基本待機時間 (秒)
        max_delay: 最大待機時間 (秒)
    """
    req = Request(url, headers={'User-Agent': USER_AGENT})
    filename = os.path.join(path, url.split('/')[-1])
    
    # 既にファイルが存在し、サイズが0より大きい場合はスキップ
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        logger.debug(f"ファイルは既に存在します: {filename}")
        return
    
    # ディレクトリが存在しない場合は作成
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    for attempt in range(max_attempts):
        if shutdown_flag:
            logger.warning(f"中断シグナルのため、ダウンロードを中止します: {url}")
            return
            
        try:
            # 指数バックオフによる待機時間の計算 (再試行時)
            if attempt > 0:
                delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                logger.debug(f"再試行前に {delay:.2f} 秒待機します... ({attempt+1}/{max_attempts})")
                time.sleep(delay)
            
            with urlopen(req, timeout=timeout) as response, open(filename, 'wb') as output:
                data = response.read()
                output.write(data)
                logger.debug(f"ダウンロード成功: {url} -> {filename}")
                break  # 成功したらループを抜ける
                
        except (HTTPError, URLError) as e:
            if hasattr(e, 'code'):
                # サーバーエラー (5xx) またはレート制限 (429) は再試行
                if 500 <= e.code < 600 or e.code == 429:
                    logger.warning(f"サーバーエラー {e.code}: {e.reason}. 再試行中... ({attempt+1}/{max_attempts})")
                    continue
                # クライアントエラー (4xx) は再試行しない (429 を除く)
                else:
                    logger.error(f"HTTP エラー {e.code}: {e.reason}. ダウンロードをスキップします: {url}")
                    return
            else:
                logger.warning(f"URL エラー: {e.reason}. 再試行中... ({attempt+1}/{max_attempts})")
                
        except IncompleteRead as e:
            logger.warning(f"不完全な読み込み: {e}. 再試行中... ({attempt+1}/{max_attempts})")
            
        except TimeoutError:
            logger.warning(f"タイムアウト. 再試行中... ({attempt+1}/{max_attempts})")
            
        except Exception as e:
            logger.error(f"予期しないエラー: {e}")
            logger.debug(traceback.format_exc())
            
        # 最大再試行回数に達した場合
        if attempt == max_attempts - 1:
            logger.error(f"{max_attempts}回の試行後にダウンロードに失敗しました: {url}")
            # 空または部分的にダウンロードされたファイルを削除
            if os.path.exists(filename):
                try:
                    os.remove(filename)
                    logger.debug(f"不完全なファイルを削除しました: {filename}")
                except:
                    pass


# Downloader Class
class Downloader:
    def __init__(self, max_workers=5, debug=False):
        self.max_workers = max_workers
        self.debug = debug
        
    def downloadUrls(self, path, urls, delay=0.5):
        """
        URLのリストから画像をダウンロードする

        引数:
            path: 保存先ディレクトリ
            urls: ダウンロードするURLのリスト
            delay: 各ダウンロード間の遅延 (秒)
        """
        if not urls:
            logger.warning(f"ダウンロードするURLがありません: {path}")
            return
            
        os.makedirs(path, exist_ok=True)
        logger.info(f"ダウンロードディレクトリを準備しました: {path}")

        total = len(urls)
        completed = 0
        errors = 0
        lock = threading.Lock()
        
        logger.info(f"{total}個のファイルのダウンロードを開始します: {path}")

        def update_progress(future):
            nonlocal completed, errors
            with lock:
                try:
                    future.result()  # エラーがあれば例外が発生
                    completed += 1
                except Exception:
                    errors += 1
                pbar.update(1)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            with tqdm(total=total, desc=f"ダウンロード中: {os.path.basename(path)}", unit="ファイル") as pbar:
                futures = []
                
                for url in urls:
                    if shutdown_flag:
                        logger.warning("中断シグナルを受信しました。ダウンロードを停止します。")
                        break
                        
                    # ファイル拡張子をチェック
                    _, ext = os.path.splitext(url)
                    if ext.lower() not in SUPPORTED_IMAGE_FORMATS:
                        logger.debug(f"サポートされていない画像形式のためスキップします: {url}")
                        continue
                        
                    future = executor.submit(_download, url, path, 
                                            timeout=30, 
                                            max_attempts=5, 
                                            base_delay=delay)
                    future.add_done_callback(update_progress)
                    futures.append(future)
                    # サーバー負荷を減らすために小さな遅延を入れる
                    time.sleep(delay * 0.1)
                
                # すべてのタスクが完了するか、または中断されるまで待機
                for future in concurrent.futures.as_completed(futures):
                    if shutdown_flag:
                        logger.warning("中断シグナルを受信しました。残りのダウンロードをキャンセルします。")
                        executor.shutdown(wait=False)
                        break

        logger.info(f"ダウンロード完了: {completed}成功 / {errors}失敗 / {total}合計")
        return {
            'total': total,
            'completed': completed,
            'errors': errors
        }


# Main Application
def main():
    parser = argparse.ArgumentParser(description="FanCaps Episode Downloader - Download images from FanCaps.net")
    parser.add_argument('url', nargs='?', help='URL to start download (episode, season, or movie)')
    parser.add_argument('--output', type=str, default="Downloads", help='Path of output folder')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode with detailed logging')
    parser.add_argument('--workers', type=int, default=5, help='Number of concurrent download workers (default: 5)')
    parser.add_argument('--delay', type=float, default=0.5, help='Delay between requests in seconds (default: 0.5)')
    args = parser.parse_args()

    # デバッグモードの設定
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("デバッグモードが有効になりました")
    
    # シグナルハンドラを設定
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if not args.url:
        parser.print_help()
        return
    
    try:
        start_time = time.time()
        
        # クロール
        crawler = Crawler(debug=args.debug)
        links = crawler.crawl(args.url)

        if not links:
            Colors.print("ダウンロードするリンクが見つかりませんでした。URLを確認して再試行してください。", Colors.RED)
            return
            
        total_links = sum(len(item['links']) for item in links if item and 'links' in item)
        Colors.print(f"合計 {len(links)} アイテム、{total_links} 画像が見つかりました", Colors.GREEN)

        # ダウンロード
        downloader = Downloader(max_workers=args.workers, debug=args.debug)
        total_completed = 0
        total_errors = 0
        
        for item in links:
            if shutdown_flag:
                Colors.print("中断シグナルを受信しました。処理を停止します。", Colors.YELLOW)
                break
                
            if item and 'links' in item and item['links']:
                subfolder = item['subfolder']
                Colors.print(f"ダウンロード開始: {subfolder} ({len(item['links'])}画像)", Colors.YELLOW)
                path = os.path.join(args.output, subfolder)
                
                result = downloader.downloadUrls(path, item['links'], delay=args.delay)
                if result:
                    total_completed += result['completed']
                    total_errors += result['errors']
                    
                if not shutdown_flag:
                    Colors.print(f"ダウンロード完了: {subfolder} ({result['completed']}/{result['total']}成功)", 
                                Colors.GREEN if result['errors'] == 0 else Colors.YELLOW)
            else:
                if item and 'subfolder' in item:
                    subfolder = item['subfolder']
                    Colors.print(f"画像が見つかりませんでした: {subfolder}", Colors.RED)

        elapsed_time = time.time() - start_time
        minutes, seconds = divmod(elapsed_time, 60)
        
        if shutdown_flag:
            Colors.print(f"\n処理は中断されました。{total_completed}個のファイルがダウンロードされました。", Colors.YELLOW)
        else:
            Colors.print(f"\n全ての処理が完了しました！", Colors.GREEN)
            
        Colors.print(f"合計: {total_completed}成功 / {total_errors}失敗", 
                    Colors.GREEN if total_errors == 0 else Colors.YELLOW)
        Colors.print(f"処理時間: {int(minutes)}分 {seconds:.1f}秒", Colors.BLUE)
        
    except Exception as e:
        Colors.print(f"予期しないエラーが発生しました: {e}", Colors.RED)
        logger.error(f"予期しない例外: {e}")
        logger.error(traceback.format_exc())
        return 1
        
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
