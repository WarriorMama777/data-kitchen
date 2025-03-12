#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import cv2
import argparse
import signal
import gc
import shutil
import numpy as np
from collections import defaultdict
from tqdm import tqdm
import time
from pathlib import Path
import itertools

# シグナルハンドラー設定
def signal_handler(sig, frame):
    print('\nプログラムが中断されました。')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def calculate_dhash(image, hash_size=8):
    """画像からDifferential Hash（dhash）を計算する"""
    # グレースケールに変換
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # リサイズ（横に+1ピクセル）
    resized = cv2.resize(gray, (hash_size + 1, hash_size))
    
    # 差分を計算
    diff = resized[:, 1:] > resized[:, :-1]
    
    # 2次元配列を1次元に変換し、ビット列に変換
    return sum([2 ** i for i, v in enumerate(diff.flatten()) if v])

def hamming_distance(hash1, hash2):
    """2つのハッシュ値間のハミング距離を計算"""
    return bin(hash1 ^ hash2).count('1')

def get_image_files(directory, extensions, recursive=False):
    """指定されたディレクトリから対象拡張子の画像ファイルを取得"""
    image_files = []
    
    if recursive:
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.lower().endswith(f".{ext.lower()}") for ext in extensions):
                    image_files.append(os.path.join(root, file))
    else:
        for file in os.listdir(directory):
            if os.path.isfile(os.path.join(directory, file)) and any(file.lower().endswith(f".{ext.lower()}") for ext in extensions):
                image_files.append(os.path.join(directory, file))
    
    return image_files

def create_directory(directory):
    """ディレクトリが存在しない場合は作成"""
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

def get_save_path(src_path, src_dir, save_dir, preserve_structure=False, preserve_own_folder=False):
    """保存先パスを生成"""
    if preserve_structure:
        rel_path = os.path.relpath(src_path, src_dir)
        save_path = os.path.join(save_dir, rel_path)
    elif preserve_own_folder:
        src_folder_name = os.path.basename(os.path.normpath(src_dir))
        file_name = os.path.basename(src_path)
        save_path = os.path.join(save_dir, src_folder_name, file_name)
    else:
        file_name = os.path.basename(src_path)
        save_path = os.path.join(save_dir, file_name)
    
    # 保存先ディレクトリを作成
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    return save_path

def save_image(img_path, save_path, cache_images=None, mem_cache="OFF"):
    """画像を保存する関数（リトライ機能付き）"""
    try:
        if mem_cache == "ON" and cache_images and img_path in cache_images:
            # メモリからの保存
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            cv2.imwrite(save_path, cache_images[img_path])
        else:
            # ファイルからコピー
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            shutil.copy2(img_path, save_path)
        return True
    except Exception as e:
        print(f"エラー: {img_path} の保存中に例外が発生しました: {e}")
        # リトライ処理
        max_retries = 3
        for retry in range(max_retries):
            try:
                print(f"リトライ {retry+1}/{max_retries}...")
                time.sleep(1)  # 少し待機
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                if mem_cache == "ON" and cache_images and img_path in cache_images:
                    cv2.imwrite(save_path, cache_images[img_path])
                else:
                    shutil.copy2(img_path, save_path)
                print("リトライ成功")
                return True
            except Exception as e:
                print(f"リトライ失敗: {e}")
                if retry == max_retries - 1:
                    print(f"{img_path} の保存をスキップします。")
                    return False

def find_similar_images(image_hashes, threshold, process_group_size):
    """
    類似画像を見つけてグループ化する
    連結成分アルゴリズムを使用
    """
    # 各画像をグループIDにマッピング
    image_to_group = {}
    # 各グループIDに属する画像のリスト
    groups = defaultdict(list)
    next_group_id = 0
    
    files_list = list(image_hashes.keys())
    n = len(files_list)
    
    print(f"画像ペアの類似性を判定中... 合計 {n} 枚の画像")
    
    # 処理ブロックに分割
    block_size = min(process_group_size, n)
    
    for i in tqdm(range(0, n, block_size), desc="ブロック処理"):
        block_end = min(i + block_size, n)
        block_files = files_list[i:block_end]
        
        # ブロック内の画像ペアを比較
        for img1, img2 in itertools.combinations(block_files, 2):
            hash1 = image_hashes[img1]
            hash2 = image_hashes[img2]
            
            distance = hamming_distance(hash1, hash2)
            
            if distance <= threshold:
                # 両方の画像がすでにグループに属しているかチェック
                if img1 in image_to_group and img2 in image_to_group:
                    if image_to_group[img1] != image_to_group[img2]:
                        # 異なるグループを結合
                        g1 = image_to_group[img1]
                        g2 = image_to_group[img2]
                        
                        # g2のすべての画像をg1に移動
                        for img in groups[g2]:
                            image_to_group[img] = g1
                            groups[g1].append(img)
                        
                        # g2を削除
                        groups.pop(g2)
                
                # img1がグループに属しているが、img2は属していない場合
                elif img1 in image_to_group:
                    g = image_to_group[img1]
                    image_to_group[img2] = g
                    groups[g].append(img2)
                
                # img2がグループに属しているが、img1は属していない場合
                elif img2 in image_to_group:
                    g = image_to_group[img2]
                    image_to_group[img1] = g
                    groups[g].append(img1)
                
                # 両方ともグループに属していない場合、新しいグループを作成
                else:
                    image_to_group[img1] = next_group_id
                    image_to_group[img2] = next_group_id
                    groups[next_group_id] = [img1, img2]
                    next_group_id += 1
    
    # 単一画像のグループを除外
    similar_groups = [group for group in groups.values() if len(group) > 1]
    
    # 処理された画像のセットを取得
    processed_images = set()
    for group in similar_groups:
        processed_images.update(group)
    
    return similar_groups, processed_images

def process_images(args):
    """画像処理のメイン関数"""
    # ガベージコレクションの無効化
    if args.gc_disable:
        gc.disable()
    
    # 保存先ディレクトリの作成
    create_directory(args.save_dir)
    if args.save_dir_duplicate:
        create_directory(args.save_dir_duplicate)
    
    # 処理対象ディレクトリのリストを取得
    dirs_to_process = []
    if args.by_folder:
        # フォルダごとに処理
        for item in os.listdir(args.dir):
            item_path = os.path.join(args.dir, item)
            if os.path.isdir(item_path):
                dirs_to_process.append(item_path)
        if not dirs_to_process:
            print(f"警告: {args.dir} 内にサブディレクトリが見つかりませんでした。親ディレクトリを処理します。")
            dirs_to_process = [args.dir]
    else:
        # 単一ディレクトリとして処理
        dirs_to_process = [args.dir]
    
    total_processed = 0
    total_duplicates = 0
    
    # 各ディレクトリを処理
    for current_dir in dirs_to_process:
        if args.debug:
            print(f"処理ディレクトリ: {current_dir}")
        
        # 画像ファイルを取得
        extensions = args.extension.split()
        image_files = get_image_files(current_dir, extensions, args.recursive)
        
        if not image_files:
            print(f"警告: {current_dir} に処理対象の画像ファイルが見つかりませんでした。")
            continue
        
        print(f"\n{current_dir} 内の {len(image_files)} 枚の画像を処理中...")
        
        # 画像のハッシュ値を計算
        image_hashes = {}
        cache_images = {}  # メモリキャッシュ用
        
        for img_path in tqdm(image_files, desc="ハッシュ値の計算"):
            try:
                # デバッグモードの場合はハッシュ計算をスキップ
                if args.debug:
                    image_hashes[img_path] = hash(img_path)  # 仮のハッシュ値
                    continue
                
                image = cv2.imread(img_path)
                if image is None:
                    print(f"警告: {img_path} を読み込めませんでした。スキップします。")
                    continue
                
                hash_value = calculate_dhash(image)
                image_hashes[img_path] = hash_value
                
                # メモリキャッシュが有効な場合は画像を保存
                if args.mem_cache == "ON":
                    cache_images[img_path] = image
                
            except Exception as e:
                print(f"エラー: {img_path} の処理中に例外が発生しました: {e}")
                # リトライ処理
                max_retries = 3
                for retry in range(max_retries):
                    try:
                        print(f"リトライ {retry+1}/{max_retries}...")
                        time.sleep(1)  # 少し待機
                        image = cv2.imread(img_path)
                        if image is None:
                            continue
                        hash_value = calculate_dhash(image)
                        image_hashes[img_path] = hash_value
                        if args.mem_cache == "ON":
                            cache_images[img_path] = image
                        print("リトライ成功")
                        break
                    except Exception as e:
                        print(f"リトライ失敗: {e}")
                        if retry == max_retries - 1:
                            print(f"{img_path} の処理をスキップします。")
        
        # 類似画像のグループ化
        if args.debug:
            print("デバッグモード: 類似画像のグループ化をシミュレート")
            similar_groups = [['img1.jpg', 'img2.jpg'], ['img3.jpg', 'img4.jpg']]
            processed_images = set(['img1.jpg', 'img2.jpg', 'img3.jpg', 'img4.jpg'])
        else:
            print("\n類似画像のグループ化を実行中...")
            similar_groups, processed_images = find_similar_images(
                image_hashes, args.threshold, args.process_group
            )
        
        # 画像の保存処理
        if args.debug:
            print("デバッグモード: 画像の保存処理をシミュレート")
        else:
            # 非重複画像の保存
            non_duplicate_images = set(image_hashes.keys()) - processed_images
            
            print(f"\n非重複画像 {len(non_duplicate_images)} 枚を保存中...")
            for img_path in tqdm(non_duplicate_images, desc="非重複画像の保存"):
                save_path = get_save_path(
                    img_path, current_dir, args.save_dir, 
                    args.preserve_structure, args.preserve_own_folder
                )
                
                save_image(img_path, save_path, cache_images, args.mem_cache)
            
            # 重複グループの処理
            print(f"\n重複グループ {len(similar_groups)} 個を処理中...")
            for group in tqdm(similar_groups, desc="重複グループの処理"):
                # 各グループから1枚を選択して保存
                selected_img = group[0]
                save_path = get_save_path(
                    selected_img, current_dir, args.save_dir, 
                    args.preserve_structure, args.preserve_own_folder
                )
                
                save_image(selected_img, save_path, cache_images, args.mem_cache)
                
                # 残りの画像を重複ディレクトリに保存（オプション）
                if args.save_dir_duplicate:
                    for dup_img in group[1:]:
                        dup_save_path = get_save_path(
                            dup_img, current_dir, args.save_dir_duplicate, 
                            args.preserve_structure, args.preserve_own_folder
                        )
                        
                        save_image(dup_img, dup_save_path, cache_images, args.mem_cache)
            
            # メモリキャッシュのクリア
            if args.mem_cache == "ON":
                cache_images.clear()
        
        # 統計情報の更新
        total_processed += len(image_files)
        total_duplicates += sum(len(group) - 1 for group in similar_groups)
    
    # 処理結果の表示
    print("\n処理完了!")
    print(f"合計処理画像数: {total_processed}")
    print(f"検出された重複画像数: {total_duplicates}")
    print(f"保存された一意の画像数: {total_processed - total_duplicates}")
    
    # ガベージコレクションの再有効化
    if args.gc_disable:
        gc.enable()

def main():
    parser = argparse.ArgumentParser(description='画像の重複を検出して削減するツール')
    
    parser.add_argument('--dir', required=True, help='処理対象ディレクトリ')
    parser.add_argument('--save_dir', default='output/', help='出力ディレクトリ（デフォルト: output/）')
    parser.add_argument('--extension', default='jpg png webp', help='処理対象の拡張子（スペース区切り、デフォルト: jpg png webp）')
    parser.add_argument('--recursive', action='store_true', help='サブディレクトリも探索する')
    parser.add_argument('--debug', action='store_true', help='デバッグモード')
    parser.add_argument('--threshold', type=int, default=10, help='類似度判定のしきい値（ハミング距離、デフォルト: 10）')
    parser.add_argument('--preserve_own_folder', action='store_true', help='元ディレクトリ名を保持する')
    parser.add_argument('--preserve_structure', action='store_true', help='ディレクトリ構造を保持する')
    parser.add_argument('--gc_disable', action='store_true', help='ガベージコレクションを無効化する')
    parser.add_argument('--by_folder', action='store_true', help='フォルダごとに処理する')
    parser.add_argument('--process_group', type=int, default=1000, help='類似判定をグループ化する画像数（デフォルト: 1000）')
    parser.add_argument('--save_dir_duplicate', help='重複画像の保存先ディレクトリ')
    parser.add_argument('--mem_cache', default='ON', choices=['ON', 'OFF'], help='メモリキャッシュを使用する（デフォルト: ON）')
    
    args = parser.parse_args()
    
    print("画像重複検出ツール")
    print(f"処理対象ディレクトリ: {args.dir}")
    print(f"保存先ディレクトリ: {args.save_dir}")
    print(f"対象拡張子: {args.extension}")
    print(f"類似度しきい値: {args.threshold}")
    
    # 入力ディレクトリの存在確認
    if not os.path.exists(args.dir):
        print(f"エラー: 指定されたディレクトリ {args.dir} が存在しません。")
        sys.exit(1)
    
    try:
        # メイン処理の実行
        process_images(args)
    except KeyboardInterrupt:
        print("\nプログラムが中断されました。")
        sys.exit(0)
    except Exception as e:
        print(f"エラー: 処理中に予期しない例外が発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
