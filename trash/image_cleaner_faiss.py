import os
import cv2
import faiss
import numpy as np
from itertools import combinations
import argparse

def extract_features(image_path, model):
    image = cv2.imread(image_path)
    keypoints, descriptors = model.detectAndCompute(image, None)
    return descriptors

def faiss_index(descriptors_list):
    dimension = descriptors_list[0].shape[1]
    index = faiss.IndexFlatL2(dimension)
    for descriptors in descriptors_list:
        if descriptors is not None:
            faiss.normalize_L2(descriptors)
            index.add(descriptors)
    return index

def search_similar_images(index, threshold=0.8):
    duplicate_pairs = []
    for i in range(index.ntotal):
        _, I = index.search(index.reconstruct(i).reshape(1, -1), index.ntotal)
        for j in I[0]:
            if i != j and j > i:
                similarity = np.dot(index.reconstruct(i), index.reconstruct(j))
                if similarity > threshold:
                    duplicate_pairs.append((i, j))
    return duplicate_pairs

def parse_arguments():
    parser = argparse.ArgumentParser(description='Detect and reduce duplicate images in a dataset.')
    parser.add_argument('--dir', required=True, help='Directory of images to process')
    parser.add_argument('--save_dir', default='output/', help='Directory to save processed images')
    parser.add_argument('--extension', nargs='+', default=['jpg', 'png', 'webp'], help='File extensions to process')
    parser.add_argument('--recursive', action='store_true', help='Process images in subdirectories recursively')
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    if not os.path.exists(args.save_dir):
        os.makedirs(args.save_dir)
    
    model = cv2.SIFT_create()
    descriptors_list = []
    image_paths = []

    for root, dirs, files in os.walk(args.dir):
        if not args.recursive and root != args.dir:
            continue
        for file in files:
            if file.split('.')[-1].lower() in args.extension:
                path = os.path.join(root, file)
                descriptors = extract_features(path, model)
                if descriptors is not None:
                    descriptors_list.append(descriptors)
                    image_paths.append(path)
    
    print(f"Total images processed: {len(image_paths)}")
    
    index = faiss_index(descriptors_list)
    duplicate_pairs = search_similar_images(index)

    for i, j in duplicate_pairs:
        os.remove(image_paths[j])
        print(f"Removed {image_paths[j]} as a duplicate of {image_paths[i]}")

if __name__ == "__main__":
    main()
