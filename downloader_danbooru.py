from argparse import ArgumentParser
from pathlib import Path
import requests
import os
import json
from datetime import datetime
from tqdm import tqdm

parser = ArgumentParser(description="Scrape content from danbooru based on tag search.")
parser.add_argument("--tags", type=str, required=True, help="Tags to search for when downloading content.")
parser.add_argument("--output", type=Path, default="output", help="Output directory. (default: output/")
parser.add_argument("--url", type=str, default="https://danbooru.donmai.us", help="Danbooru url to make api calls to. (default: https://danbooru.donmai.us)")
parser.add_argument("--page_limit", type=int, default=1000, help="Maximum number of pages to parse through when downloading. (default: 1000)")
parser.add_argument("--api_key", type=str, help="API key for Danbooru, optional unless you want to link a higher level account to surpass tag search and page limit restrictions. Username must also be provided.")
parser.add_argument("--username", type=str, help="Username to log on to Danbooru with, to be provided alongside an api_key")
parser.add_argument("--max_file_size", action='store_true', help="Attempt to download the maximum available file size instead of the default size.")
parser.add_argument("--extensions", type=str, default=".png,.jpg", help="Extensions of file types to download, comma-separated. Pass * to download all file types. (default: .png,.jpg)")
parser.add_argument("--save_tags", action='store_true', help="Save the tags for each image in a text file with the same name.")
parser.add_argument("--tags_only", action='store_true', help="Only save tags for existing images. Do not download any images.")
parser.add_argument("--write_translation", action='store_true', help="Write the translation of foreign text in the image to the tag file.")
parser.add_argument("--year_start", type=int, help="Start year for downloading content. Format: YYYY")
parser.add_argument("--year_end", type=int, help="End year for downloading content. Format: YYYY")

def is_within_year_range(date_str, year_start, year_end):
    post_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%f%z')
    if year_start and post_date.year < year_start:
        return False
    if year_end and post_date.year > year_end:
        return False
    return True

def get_posts(tags, url, login_info=None, page_limit=1000, year_start=None, year_end=None):
    print(f"Downloading posts for tags: {tags}...")
    for i in tqdm(range(1, page_limit+1), desc="Analyzing", unit="page"):
        params = {
            "tags": tags,
            "page": i
        }
        if login_info:
            params.update(login_info)
        req = requests.get(f"{url}/posts.json", params=params)
        content = req.json()
        if content == []:
            return
        if "success" in content and not content["success"]:
            raise Exception("Danbooru API: " + content["message"]) 
        for post in content:
            if not is_within_year_range(post['created_at'], year_start, year_end):
                continue
            yield post

def download_image(url, path):
    try:
        response = requests.get(url)
        # Ensure the request was successful; otherwise, raise an exception
        response.raise_for_status()
        with open(path, 'wb') as file:
            file.write(response.content)
    except Exception as e:
        print(f"Error downloading {url}: {e}")
def save_metadata(post, path):
    with open(path, 'w', encoding='utf-8') as file:
        json.dump(post, file, ensure_ascii=False, indent=4)

def main(args):
    os.makedirs(args.output, exist_ok=True)

    login_info = None
    if any([args.username, args.api_key]):
        if all([args.username, args.api_key]):
            login_info = {
                "login": args.username,
                "api_key": args.api_key
            }
        else:
            raise Exception("You must pass both a --username and an --api_key in order to log on")

    all_extensions = args.extensions == "*"
    extensions = [e.strip().lower() for e in args.extensions.split(",")]

    if args.tags_only:
        args.save_tags = True

    i = 0
    j = 0
    try:
        posts = list(get_posts(args.tags, args.url, login_info, args.page_limit, args.year_start, args.year_end))
        for post in tqdm(posts, desc="Processing posts", unit="post"):
            if 'file_url' not in post:  # 追加した確認処理
                print(f"Skipping post {post['id']} due to missing 'file_url'")
                continue

            file_url = post['file_url']
            file_ext = os.path.splitext(file_url)[1].lower()
            if all_extensions or file_ext in extensions:
                file_name = f"{post['id']}{file_ext}"
                file_path = os.path.join(args.output, file_name)

                if not args.tags_only:
                    download_image(file_url, file_path)
                    i += 1
                    print(f"Downloaded {file_name}")

                metadata_path = f"{os.path.splitext(file_path)[0]}.txt"
                save_metadata(post, metadata_path)
                j += 1
                print(f"Saved metadata for {file_name}")

    except KeyboardInterrupt:
        pass

    if not args.tags_only:
        print(f"Scraped {i} files")
    print(f"Saved {j} metadata files")

if __name__ == "__main__":
    try:
        main(parser.parse_args())
    except Exception as e:
        print(e)