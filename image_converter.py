import cv2
import os
import numpy as np
from tqdm import tqdm
import argparse
from pathlib import Path

def convert_colorcode_to_bgr(colorcode):
    colorcode = colorcode.lstrip('#')
    lv = len(colorcode)
    return tuple(int(colorcode[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))[::-1]

def process_image(image_path, save_path, background, resize, format, quality):
    image = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if image is None:
        print(f"Failed to load image: {image_path}")
        return False

    if background and image.shape[2] == 4:
        bgr_color = convert_colorcode_to_bgr(background)
        alpha_channel = image[:, :, 3]
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        mask = alpha_channel[:, :, np.newaxis] / 255.0
        background_layer = np.full(image.shape, bgr_color, np.uint8)
        image = (background_layer * (1 - mask) + image * mask).astype(np.uint8)

    if resize:
        h, w = image.shape[:2]
        scale = resize / max(h, w)
        image = cv2.resize(image, (int(w * scale), int(h * scale)))

    if format:
        save_path = f"{save_path}.{format}"
        if format.lower() == 'webp':
            cv2.imwrite(save_path, image, [cv2.IMWRITE_WEBP_QUALITY, quality])
        elif format.lower() in ['jpg', 'jpeg']:
            cv2.imwrite(save_path, image, [cv2.IMWRITE_JPEG_QUALITY, quality])
        elif format.lower() == 'png':
            cv2.imwrite(save_path, image, [cv2.IMWRITE_PNG_COMPRESSION, quality])
        else:
            cv2.imwrite(save_path, image)
    else:
        cv2.imwrite(save_path, image)

    return True

def process_directory(dir_path, save_dir, extensions, recursive, background, resize, format, quality):
    if recursive:
        files = [f for ext in extensions for f in Path(dir_path).rglob(f'*.{ext}')]
    else:
        files = [f for ext in extensions for f in Path(dir_path).glob(f'*.{ext}')]

    for file_path in tqdm(files, desc="Processing images"):
        relative_path = file_path.relative_to(dir_path)
        save_path = save_dir / relative_path
        save_path.parent.mkdir(parents=True, exist_ok=True)

        process_image(file_path, save_path, background, resize, format, quality)

def main():
    parser = argparse.ArgumentParser(description='Convert and process images.')
    parser.add_argument('--dir', required=True, help='Directory to process')
    parser.add_argument('--save_dir', default='output/', help='Directory to save processed images')
    parser.add_argument('--extension', nargs='+', required=True, help='Extensions of files to process')
    parser.add_argument('--recursive', action='store_true', help='Process directories recursively')
    parser.add_argument('--background', help='Background color code for transparent images (e.g., ffffff)')
    parser.add_argument('--resize', type=int, help='Resize the long side to this size')
    parser.add_argument('--format', help='Format to convert images to')
    parser.add_argument('--quality', nargs='?', type=int, default=90, help='Quality for conversion, applicable to formats like webp, jpg, png')

    args = parser.parse_args()

    process_directory(
        Path(args.dir),
        Path(args.save_dir),
        args.extension,
        args.recursive,
        args.background,
        args.resize,
        args.format,
        args.quality
    )

if __name__ == '__main__':
    main()
