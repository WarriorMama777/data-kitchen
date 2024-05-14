import os
import argparse
from imutils import paths
import cv2
from typing import List, Dict

def dhash(image, hashSize=8):
    # Resize the image and convert it to grayscale
    resized = cv2.resize(image, (hashSize + 1, hashSize))
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

    # Compute the horizontal gradient
    diff = gray[:, 1:] > gray[:, :-1]

    # Generate the hash value
    return sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])

def main():
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, help="Directory to process")
    parser.add_argument("--save_dir", default="output/", help="Directory to save the output")
    parser.add_argument("--extension", default="jpg png webp", help="File extensions to process")
    parser.add_argument("--recursive", action='store_true', help="Search subdirectories recursively")
    parser.add_argument("--debug", action='store_true', help="Enable debug mode without actual image processing")
    args = parser.parse_args()

    # Create the output directory if it does not exist
    if not os.path.exists(args.save_dir):
        os.makedirs(args.save_dir)

    # Get the paths of the image files
    if args.recursive:
        imagePathList = list(paths.list_images(args.dir))
    else:
        imagePathList = [os.path.join(args.dir, f) for f in os.listdir(args.dir) if f.split('.')[-1] in args.extension.split()]

    # Dictionary to store hash values
    hashes: Dict[int, List[str]] = {}

    # Process images
    for imagePath in imagePathList:
        # In debug mode, only display the intended actions
        if args.debug:
            print(f"Debug: Would process {imagePath}")
            continue

        # Load the image
        image = cv2.imread(imagePath)
        # Compute the hash
        h = dhash(image)

        # Compare with existing hash values
        if h in hashes:
            print(f"Duplicate image detected: {imagePath} will be ignored.")
            continue
        else:
            hashes[h] = imagePath

            # Save the file in the output directory, maintaining directory structure
            relative_path = os.path.relpath(imagePath, args.dir)
            save_path = os.path.join(args.save_dir, relative_path)
            save_dir = os.path.dirname(save_path)
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            cv2.imwrite(save_path, image)
            print(f"Saved {imagePath} to {save_path}.")

if __name__ == "__main__":
    main()
