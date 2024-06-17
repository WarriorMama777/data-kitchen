import argparse
import os
import requests
import shutil
import time
from bs4 import BeautifulSoup
from multiprocessing import Pool
from tqdm import tqdm
import signal
import sys

# Signal handler to gracefully handle script interruption
def signal_handler(sig, frame):
    print("\nProcess interrupted. Exiting gracefully...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Function to get post URLs
def getting_post_urls(keyword):
    url = f'https://www.pornpics.com/search/srch.php?q={keyword}&limit=100000&offset='
    headers = {
        "Connection": "close",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "en-US,en;q=0.9,hi;q=0.8"
    }
    cookies = {
        "cookie": "__ae_uid_sess_id=b162cbb3-9e86-4a55-ac81-f1b1cccdd6e0; PP_UVM=1; _stat=2598133695.1528214785.23479322.3739817806; _ga=GA1.2.1272764643.1603974465; _gid=GA1.2.1206331922.1605948774"
    }
    
    try:
        response = requests.get(url, headers=headers, cookies=cookies)
        response.raise_for_status()
        json_data = response.json()
        
        with open(f'{keyword}_post_links.txt', "w") as file:
            for link in json_data:
                file.write(f"{link['g_url']}\n")
                
        print("Got all post's URLs.")
    except requests.RequestException as e:
        print(f"Error fetching post URLs: {e}")
        sys.exit(1)

# Function to get image URLs
def getting_image_urls(keyword):
    try:
        with open(f'{keyword}_post_links.txt', 'r') as file:
            post_urls = file.readlines()

        headers = {
            "Connection": "close",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.9,hi;q=0.8"
        }
        cookies = {
            "cookie": "__ae_uid_sess_id=b162cbb3-9e86-4a55-ac81-f1b1cccdd6e0; PP_UVM=1; _stat=2598133695.1528214785.23479322.3739817806; _ga=GA1.2.1272764643.1603974465; _gid=GA1.2.1206331922.1605948774"
        }

        image_urls = []

        for url in tqdm(post_urls, desc="Fetching image URLs", unit="URL"):
            try:
                response = requests.get(url.strip(), headers=headers, cookies=cookies)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                for img_tag in soup.find_all("a", class_='rel-link'):
                    image_urls.append(img_tag.get("href"))
            except requests.RequestException as e:
                print(f"Error fetching image URLs from {url.strip()}: {e}")
                continue

        with open(f'{keyword}_image_links.txt', "w") as file:
            for img_url in image_urls:
                file.write(f"{img_url}\n")
                
        print("Got all image's URLs.")
        print(f"Total images: {len(image_urls)}")
    except FileNotFoundError:
        print(f"File {keyword}_post_links.txt not found. Please run the script to get post URLs first.")
        sys.exit(1)

# Function to download an image
def download_image(url, save_dir):
    retries = 3
    for _ in range(retries):
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            filename = os.path.join(save_dir, url.split("/")[-1])
            with open(filename, 'wb') as file:
                shutil.copyfileobj(response.raw, file)
            return
        except requests.RequestException:
            time.sleep(1)
    print(f"Failed to download {url}")

# Wrapper function to handle download with arguments
def download_image_wrapper(args):
    return download_image(*args)

# Main function
def main(keyword, save_dir):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    getting_post_urls(keyword)
    getting_image_urls(keyword)

    with open(f'{keyword}_image_links.txt', 'r') as file:
        image_urls = file.readlines()

    print(f"Downloading {len(image_urls)} images. Please wait.")
    
    with Pool(4) as pool:
        list(tqdm(pool.imap_unordered(download_image_wrapper, [(url.strip(), save_dir) for url in image_urls]), total=len(image_urls), desc="Downloading images", unit="image"))

    print("Done.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Image downloader script.")
    parser.add_argument('--keyword', required=True, help="Keyword for searching images")
    parser.add_argument('--save_dir', default="./output", help="Directory to save images")
    
    args = parser.parse_args()
    main(args.keyword, args.save_dir)
