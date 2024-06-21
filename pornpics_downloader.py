import argparse
import os
import requests
import shutil
import time
import json
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
def getting_post_urls(keyword, save_dir, limit_post_urls):
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
        
        post_links_path = os.path.join(save_dir, f'{keyword}_post_links.txt')
        with open(post_links_path, "w") as file:
            for i, link in enumerate(json_data):
                if limit_post_urls and i >= limit_post_urls:
                    break
                file.write(f"{link['g_url']}\n")
                
        print("Got all post's URLs.")
    except requests.RequestException as e:
        print(f"Error fetching post URLs: {e}")
        sys.exit(1)

# Function to get image URLs
def getting_image_urls(keyword, save_dir, limit_image_urls):
    try:
        post_links_path = os.path.join(save_dir, f'{keyword}_post_links.txt')
        with open(post_links_path, 'r') as file:
            post_urls = file.readlines()
        
        if limit_image_urls:
            post_urls = post_urls[:limit_image_urls]

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
        metadata = []

        for url in tqdm(post_urls, desc="Fetching image URLs", unit="URL"):
            try:
                response = requests.get(url.strip(), headers=headers, cookies=cookies)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')

                # 除外する領域を削除
                main2_div = soup.find(id="main2")
                if main2_div:
                    main2_div.decompose()

                gallery_id = url.strip().split("/")[-2]
                title = soup.find("h1").get_text(strip=True) if soup.find("h1") else None
                channel = soup.select_one(".gallery-info__item:has(.gallery-info__title:contains('Channel:')) a")
                channel = channel.get_text(strip=True) if channel else None

                # Extract models
                models = [a.get_text(strip=True) for a in soup.select('.gallery-info__item:has(.gallery-info__title:contains("Models:")) .gallery-info__content a')]

                # Extract categories
                categories = [a.get_text(strip=True) for a in soup.select('.gallery-info__item.tags:has(.gallery-info__title:contains("Categories:")) .gallery-info__content a')]

                # Extract tags
                tags = [a.get_text(strip=True) for a in soup.select('.gallery-info__item.tags:has(.gallery-info__title:contains("Tags List:")) .gallery-info__content a')]

                # Extract stats
                stats = soup.select_one('.gallery-info__item:has(.gallery-info__title:contains("Stats:")) .gallery-info__content')
                rating = stats.select_one('.info-rate .rate-count').get_text(strip=True) if stats and stats.select_one('.info-rate .rate-count') else None
                views_text = stats.select_one('.info-views').get_text(strip=True) if stats and stats.select_one('.info-views') else "Views: 0"
                views = views_text.split(":")[1].strip().replace(",", "") if ":" in views_text else "0"
                views = int(views) if views else 0

                count = len(soup.find_all("a", class_='rel-link'))

                for img_tag in soup.find_all("a", class_='rel-link'):
                    img_url = img_tag.get("href")
                    filename = img_url.split("/")[-1]
                    image_urls.append(img_url)
                    metadata.append({
                        "gallery_id": gallery_id,
                        "slug": title.lower().replace(" ", "-") if title else None,
                        "title": title,
                        "channel": channel,
                        "rating": rating,
                        "models": models,
                        "categories": categories,
                        "tags": tags,
                        "views": views,
                        "count": count,
                        "category": "pics",
                        "subcategory": "gallery",
                        "num": len(image_urls),
                        "filename": os.path.splitext(filename)[0],
                        "extension": os.path.splitext(filename)[1][1:],
                        "keyword": keyword  # 検索クエリキーワードも含めるようにする
                    })
            except requests.RequestException as e:
                print(f"Error fetching image URLs from {url.strip()}: {e}")
                continue

        image_links_path = os.path.join(save_dir, f'{keyword}_image_links.txt')
        with open(image_links_path, "w") as file:
            for img_url in image_urls:
                file.write(f"{img_url}\n")

        metadata_path = os.path.join(save_dir, f'{keyword}_metadata.json')
        with open(metadata_path, "w") as file:
            json.dump(metadata, file, indent=4)

        print("Got all image's URLs and metadata.")
        print(f"Total images: {len(image_urls)}")
    except FileNotFoundError:
        print(f"File {keyword}_post_links.txt not found in {save_dir}. Please run the script to get post URLs first.")
        sys.exit(1)

# Function to download an image
def download_image(url, save_dir, metadata, write_metadata):
    retries = 3
    for _ in range(retries):
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            filename = os.path.join(save_dir, url.split("/")[-1])
            with open(filename, 'wb') as file:
                shutil.copyfileobj(response.raw, file)
            if write_metadata:
                metadata_filename = os.path.splitext(filename)[0] + ".json"
                with open(metadata_filename, 'w') as metafile:
                    json.dump(metadata, metafile, indent=4)
            return
        except requests.RequestException:
            time.sleep(1)
    print(f"Failed to download {url}")

# Wrapper function to handle download with arguments
def download_image_wrapper(args):
    return download_image(*args)

# Main function
def main(keyword, save_dir, write_metadata, limit_download, limit_post_urls, limit_image_urls):
    save_dir = os.path.join(save_dir, keyword)
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    getting_post_urls(keyword, save_dir, limit_post_urls)
    getting_image_urls(keyword, save_dir, limit_image_urls)

    image_links_path = os.path.join(save_dir, f'{keyword}_image_links.txt')
    metadata_path = os.path.join(save_dir, f'{keyword}_metadata.json')

    with open(image_links_path, 'r') as file:
        image_urls = file.readlines()

    with open(metadata_path, 'r') as file:
        metadata_list = json.load(file)

    if limit_download > 0:
        image_urls = image_urls[:limit_download]
        metadata_list = metadata_list[:limit_download]

    print(f"Downloading {len(image_urls)} images. Please wait.")
    
    with Pool(4) as pool:
        list(tqdm(pool.imap_unordered(download_image_wrapper, [(url.strip(), save_dir, metadata_list[idx], write_metadata) for idx, url in enumerate(image_urls)]), total=len(image_urls), desc="Downloading images", unit="image"))

    print("Done.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Image downloader script.")
    parser.add_argument('--keyword', required=True, help="Keyword for searching images")
    parser.add_argument('--save_dir', default="./output", help="Directory to save images")
    parser.add_argument('--write-metadata', action='store_true', help="Write metadata for each image in JSON format")
    parser.add_argument('--limit_download', type=int, default=0, help="Limit the number of images to download")
    parser.add_argument('--limit_post_urls', type=int, default=0, help="Limit the number of post URLs to retrieve")
    parser.add_argument('--limit_image_urls', type=int, default=0, help="Limit the number of image URLs to retrieve")

    args = parser.parse_args()
    main(args.keyword, args.save_dir, args.write_metadata, args.limit_download, args.limit_post_urls, args.limit_image_urls)
    