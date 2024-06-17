import argparse
import os
import requests
import json
from tqdm import tqdm
import signal
import sys

# Constants
API_URL = "https://api.jikan.moe/v4/characters"

# Signal handler to safely stop the script
def signal_handler(sig, frame):
    print('You pressed Ctrl+C! Exiting gracefully.')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Function to get character data from Jikan API
def get_character_data():
    character_data = []
    page = 1
    while True:
        response = requests.get(API_URL, params={"page": page})
        if response.status_code != 200:
            print(f"Failed to retrieve data: {response.status_code}")
            break
        data = response.json()
        if "data" in data:
            character_data.extend(data["data"])
        if "pagination" in data and not data["pagination"]["has_next_page"]:
            break
        page += 1
    return character_data

# Function to save character data and images
def save_character_data(character_data, save_dir, debug):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    for character in tqdm(character_data, desc="Downloading characters"):
        char_id = character['mal_id']
        char_name = character['name']
        char_image_url = character['images']['jpg']['image_url']
        char_meta = {
            'id': char_id,
            'name': char_name,
            'anime': character['anime'],
            'manga': character['manga']
        }
        
        if debug:
            print(f"Character ID: {char_id}")
            print(f"Name: {char_name}")
            print(f"Image URL: {char_image_url}")
            print(f"Meta: {json.dumps(char_meta, indent=2)}")
        else:
            image_response = requests.get(char_image_url)
            if image_response.status_code == 200:
                with open(os.path.join(save_dir, f"{char_id}.jpg"), 'wb') as img_file:
                    img_file.write(image_response.content)
                with open(os.path.join(save_dir, f"{char_id}.json"), 'w', encoding='utf-8') as meta_file:
                    json.dump(char_meta, meta_file, ensure_ascii=False, indent=2)
            else:
                print(f"Failed to download image for character {char_name} (ID: {char_id})")

# Main function
def main():
    parser = argparse.ArgumentParser(description="Download MyAnimeList character data using Jikan API")
    parser.add_argument("--dir", type=str, required=True, help="Processing target directory or file")
    parser.add_argument("--save_dir", type=str, default=".\\output", help="Output directory")
    parser.add_argument("--debug", action='store_true', help="Enable debug mode")

    args = parser.parse_args()
    debug = args.debug
    save_dir = args.save_dir

    print("Fetching character data from Jikan API...")
    try:
        character_data = get_character_data()
    except Exception as e:
        print(f"Error fetching character data: {e}")
        return

    print(f"Saving character data to {save_dir}...")
    try:
        save_character_data(character_data, save_dir, debug)
    except Exception as e:
        print(f"Error saving character data: {e}")

    print("Process completed.")

if __name__ == "__main__":
    main()
