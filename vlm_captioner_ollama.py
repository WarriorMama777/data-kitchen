#!/usr/bin/env python3
"""
vlm_captioner_ollama.py - Ollama APIを使用して画像にキャプションを付けるスクリプト
"""
import os
import sys
import argparse
import base64
import json
import time
import signal
import traceback
import requests
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Union, Optional, Tuple, Any
from tqdm import tqdm
import multiprocessing
import re
import shutil
import logging
from urllib.parse import urlparse

# シグナルハンドリング
def signal_handler(sig, frame):
    print("\nプログラムを停止しています...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ollama APIの接続テスト
def test_ollama_connection(api_base: str) -> bool:
    """Ollama APIへの接続をテストする関数"""
    try:
        # バージョン情報の取得を試みる
        response = requests.get(f"{api_base}/api/version", timeout=10)
        if response.status_code == 200:
            version_info = response.json()
            logger.info(f"Ollama APIに接続しました (バージョン: {version_info.get('version', '不明')})")
            return True
        else:
            logger.error(f"Ollama APIへの接続は成功しましたが、ステータスコードが異常です: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Ollama APIへの接続に失敗しました: {api_base}")
        logger.error("以下の原因が考えられます:")
        logger.error(" - Ollamaサーバーが起動していない")
        logger.error(" - URLが間違っている")
        logger.error(" - ポートがファイアウォールでブロックされている")
        return False
    except Exception as e:
        logger.error(f"Ollama API接続テスト中にエラーが発生しました: {str(e)}")
        return False

# モデルの存在確認
def check_model_exists(api_base: str, model_name: str) -> bool:
    """指定したモデルがOllamaにインストールされているか確認する関数"""
    try:
        response = requests.get(f"{api_base}/api/tags", timeout=10)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [model["name"] for model in models]
            
            # 完全一致または接頭辞一致をチェック
            if model_name in model_names:
                logger.info(f"モデル '{model_name}' が見つかりました")
                return True
            
            # タグなしでの一致をチェック
            base_name = model_name.split(':')[0]
            for m in model_names:
                if m.startswith(f"{base_name}:") or m == base_name:
                    logger.info(f"モデル '{model_name}' の代わりに '{m}' が見つかりました")
                    return True
            
            logger.error(f"モデル '{model_name}' が見つかりません。以下のモデルがインストールされています:")
            for m in model_names:
                logger.error(f" - {m}")
            logger.error(f"モデルをインストールするには: ollama pull {model_name}")
            return False
        else:
            logger.error(f"モデル一覧の取得に失敗しました: ステータスコード {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"モデル確認中にエラーが発生しました: {str(e)}")
        return False

# Base64エンコード関数
def encode_image_to_base64(image_path: str) -> Optional[str]:
    """画像をBase64にエンコードする関数"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logger.error(f"画像のエンコード中にエラーが発生しました: {str(e)}")
        return None

# Ollama APIリクエスト関数
def generate_caption_with_retry(args, image_base64: str, retry_count: int = 3, retry_delay: float = 1.0) -> str:
    """
    Ollamaを使用して画像のキャプションを生成する関数（リトライ機能付き）
    """
    prompt = args.prompt
    
    # プロンプトがファイルの場合、ファイルから読み込む
    if os.path.isfile(prompt):
        try:
            with open(prompt, 'r', encoding='utf-8') as f:
                prompt = f.read()
                logger.debug(f"プロンプトファイルを読み込みました: {prompt[:50]}...")
        except Exception as e:
            logger.error(f"プロンプトファイルの読み込みに失敗しました: {str(e)}")
            prompt = "Describe this image in detail."

    # APIリクエストの準備
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "VLM-Captioner/1.0"
    }
    
    # APIキーが指定されている場合
    if args.api:
        headers["Authorization"] = f"Bearer {args.api}"
    
    # オプションパラメータを追加
    options = {}
    option_params = [
        'temperature', 'top_p', 'top_k', 'num_predict', 'seed',
        'num_ctx', 'repeat_penalty', 'presence_penalty', 'frequency_penalty',
        'mirostat', 'mirostat_tau', 'mirostat_eta'
    ]
    
    for option in option_params:
        value = getattr(args, option, None)
        if value is not None:
            options[option] = value
    
    # APIパスの選択（まずは /api/chat を試す）
    api_endpoints = [
        ("chat", {
            "model": args.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_base64]
                }
            ],
            "stream": False
        }),
        ("generate", {
            "model": args.model,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False
        })
    ]
    
    if options:
        for _, payload in api_endpoints:
            payload["options"] = options.copy()
    
    # 両方のエンドポイントでリトライする
    for endpoint_name, payload in api_endpoints:
        api_url = f"{args.api_base}/api/{endpoint_name}"
        
        # デバッグ出力
        if args.debug:
            logger.debug(f"API URL: {api_url}")
            logger.debug(f"リクエストヘッダー: {headers}")
            logger.debug(f"リクエストペイロード: {json.dumps(payload)[:500]}...")

        # リトライループ
        for attempt in range(retry_count):
            try:
                # APIリクエスト
                response = requests.post(
                    api_url,
                    headers=headers,
                    json=payload,
                    timeout=60  # タイムアウト時間を増加
                )
                
                # デバッグ出力
                if args.debug:
                    logger.debug(f"レスポンスステータス: {response.status_code}")
                    logger.debug(f"レスポンス (最初の500文字): {response.text[:500]}")
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        
                        # レスポース形式ごとの処理
                        if endpoint_name == "chat":
                            if "message" in result and "content" in result["message"]:
                                caption = result["message"]["content"].strip()
                            else:
                                logger.warning(f"予期しないレスポンス形式: {result}")
                                caption = "No caption generated."
                        else:  # generate
                            caption = result.get("response", "").strip()
                        
                        # キャプションが空の場合
                        if not caption:
                            logger.warning("APIは成功しましたが、キャプションが空でした")
                            caption = "No caption generated."
                        
                        # キャプションにタグを追加
                        if args.add_tag:
                            if args.add_tag_position == "first":
                                caption = f"{args.add_tag}, {caption}"
                            elif args.add_tag_position == "last":
                                caption = f"{caption}, {args.add_tag}"
                        
                        return caption
                    except json.JSONDecodeError:
                        logger.error(f"JSON解析エラー: {response.text[:500]}")
                        logger.error(traceback.format_exc())
                else:
                    # エラーメッセージ
                    try:
                        error_json = response.json()
                        logger.warning(f"APIリクエストが失敗しました [{endpoint_name}] (ステータスコード: {response.status_code}): {json.dumps(error_json)}")
                    except:
                        logger.warning(f"APIリクエストが失敗しました [{endpoint_name}] (ステータスコード: {response.status_code}): {response.text[:200]}")
                    
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Ollama APIへの接続に失敗しました [{endpoint_name}]: {str(e)}")
                if args.debug:
                    logger.debug(traceback.format_exc())
            except requests.exceptions.Timeout:
                logger.warning(f"APIリクエストがタイムアウトしました [{endpoint_name}] (試行 {attempt+1}/{retry_count})")
            except Exception as e:
                logger.warning(f"キャプション生成中にエラーが発生しました [{endpoint_name}] (試行 {attempt+1}/{retry_count}): {str(e)}")
                if args.debug:
                    logger.debug(traceback.format_exc())
            
            # リトライ前の遅延（指数バックオフ）
            backoff_time = retry_delay * (2 ** attempt)
            logger.info(f"{backoff_time:.2f}秒後にリトライします...")
            time.sleep(backoff_time)
    
    logger.error(f"キャプション生成が失敗しました。両方のエンドポイントで{retry_count}回試行しました。")
    return "Caption generation failed."

def process_image(args, image_path: str, save_path: str, results: Dict) -> Optional[str]:
    """単一画像を処理する関数"""
    try:
        # レート制限の処理
        if args.rate_limit:
            time.sleep(float(args.rate_limit))
        
        # 画像をBase64エンコード
        image_base64 = encode_image_to_base64(image_path)
        if not image_base64:
            logger.error(f"画像のエンコードに失敗しました: {image_path}")
            return None
        
        # デバッグモードなら実際の処理はスキップ
        if args.debug and args.debug_skip_api:
            logger.debug(f"デバッグモード (API呼び出しスキップ): {image_path} -> {save_path}")
            caption = f"DEBUG: This is a debug caption for {os.path.basename(image_path)}"
        else:
            # キャプション生成
            caption = generate_caption_with_retry(args, image_base64)
        
        # 結果をディクショナリに保存（メモリキャッシュ）
        if args.mem_cache:
            results[image_path] = {
                "caption": caption,
                "save_path": save_path
            }
        else:
            # メモリキャッシュが無効なら直接保存
            save_caption(caption, save_path)
        
        return caption
    except Exception as e:
        logger.error(f"画像処理中にエラーが発生しました {image_path}: {str(e)}")
        if args.debug:
            traceback.print_exc()
        return None

def save_caption(caption: str, save_path: str) -> bool:
    """キャプションをファイルに保存する関数"""
    try:
        # ディレクトリが存在しない場合は作成
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        
        # キャプションをファイルに書き込み
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(caption)
        return True
    except Exception as e:
        logger.error(f"キャプションの保存中にエラーが発生しました {save_path}: {str(e)}")
        return False

def get_image_files(directory: str, recursive: bool = True) -> List[str]:
    """画像ファイルのリストを取得する関数"""
    image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.bmp']
    image_files = []
    
    if os.path.isfile(directory):
        ext = os.path.splitext(directory)[1].lower()
        if ext in image_extensions:
            return [directory]
        else:
            logger.error(f"指定されたファイルは対応する画像形式ではありません: {directory}")
            return []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in image_extensions:
                image_files.append(os.path.join(root, file))
        
        # 再帰的な探索をしない場合は最初のディレクトリだけ処理
        if not recursive:
            break
    
    return sorted(image_files)  # ファイルリストをソート

def get_save_path(args, image_path: str) -> str:
    """保存先のパスを生成する関数"""
    # ベースディレクトリを取得
    base_input_dir = os.path.abspath(args.dir_image)
    
    # 入力がファイルの場合の処理
    if os.path.isfile(base_input_dir):
        filename = os.path.basename(base_input_dir)
        base_name = os.path.splitext(filename)[0]
        return os.path.join(args.dir_save, f"{base_name}.txt")
    
    # ディレクトリ構造を保持する場合
    if args.preserve_structure:
        rel_path = os.path.relpath(image_path, base_input_dir)
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        dir_path = os.path.dirname(rel_path)
        
        # 親フォルダの保持が有効な場合
        if args.preserve_own_folder:
            parent_folder = os.path.basename(base_input_dir)
            save_dir = os.path.join(args.dir_save, parent_folder, dir_path)
        else:
            save_dir = os.path.join(args.dir_save, dir_path)
            
        return os.path.join(save_dir, f"{base_name}.txt")
    else:
        # 構造を保持しない場合
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        
        # 親フォルダの保持が有効な場合
        if args.preserve_own_folder:
            parent_folder = os.path.basename(base_input_dir)
            save_dir = os.path.join(args.dir_save, parent_folder)
        else:
            save_dir = args.dir_save
            
        return os.path.join(save_dir, f"{base_name}.txt")

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='画像キャプション生成スクリプト (Ollama API使用)')
    
    # 一般的な引数
    parser.add_argument('--dir_image', required=True, help='処理対象ディレクトリまたはファイル')
    parser.add_argument('--recursive', action='store_true', default=True, help='サブディレクトリも含めて処理するかどうか')
    parser.add_argument('--dir_save', default='./output', help='出力ディレクトリ')
    parser.add_argument('--preserve_own_folder', action='store_true', default=True, help='親フォルダ名を保持するかどうか')
    parser.add_argument('--preserve_structure', action='store_true', default=True, help='ディレクトリ構造を保持するかどうか')
    parser.add_argument('--by_folder', action='store_true', help='フォルダごとに処理するかどうか')
    parser.add_argument('--debug', action='store_true', help='デバッグモード')
    parser.add_argument('--debug_skip_api', action='store_true', help='デバッグモードでAPI呼び出しをスキップ')
    parser.add_argument('--mem_cache', action='store_true', default=True, help='処理結果をメモリにキャッシュするかどうか')
    parser.add_argument('--threads', type=int, default=None, help='使用するスレッド数')
    parser.add_argument('--skip_connection_test', action='store_true', help='接続テストをスキップ')
    
    # Ollama API関連の引数
    parser.add_argument('--api_base', default='http://localhost:11434', help='Ollama APIベースURL')
    parser.add_argument('--model', default='llava', help='Ollamaのモデル名')
    parser.add_argument('--prompt', default='Describe this image in detail.', help='VLM用の推論プロンプトまたはプロンプトファイル')
    parser.add_argument('--api', help='Ollama APIキー')
    parser.add_argument('--rate_limit', type=float, help='APIリクエストの間隔（秒）')
    
    # Ollama生成パラメータ
    parser.add_argument('--temperature', type=float, default=0.7, help='生成温度 (0.0-1.0)')
    parser.add_argument('--top_p', type=float, help='Top-p サンプリング確率 (0.0-1.0)')
    parser.add_argument('--top_k', type=int, help='Top-k サンプリング数')
    parser.add_argument('--num_predict', type=int, help='生成するトークン数')
    parser.add_argument('--num_ctx', type=int, help='コンテキスト長')
    parser.add_argument('--seed', type=int, help='乱数シード')
    parser.add_argument('--repeat_penalty', type=float, help='繰り返しペナルティ')
    parser.add_argument('--presence_penalty', type=float, help='存在ペナルティ')
    parser.add_argument('--frequency_penalty', type=float, help='頻度ペナルティ')
    parser.add_argument('--mirostat', type=int, choices=[0, 1, 2], help='Mirostatサンプリングモード (0, 1, または 2)')
    parser.add_argument('--mirostat_tau', type=float, help='Mirostatタウ値')
    parser.add_argument('--mirostat_eta', type=float, help='Mirostatエータ値')
    
    # キャプション関連の引数
    parser.add_argument('--add_tag', help='キャプションに追加するタグ')
    parser.add_argument('--add_tag_position', default='first', choices=['first', 'last'], help='タグの追加位置')
    
    args = parser.parse_args()
    
    # デバッグモードの設定
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("デバッグモードが有効です")
        logger.debug(f"API Base URL: {args.api_base}")
    
    # 接続テスト（スキップしない場合）
    if not args.skip_connection_test and not args.debug_skip_api:
        if not test_ollama_connection(args.api_base):
            logger.error("Ollama APIへの接続に失敗しました。以下を確認してください:")
            logger.error(f" 1. Ollamaサーバーが起動しているか (ollama serve)")
            logger.error(f" 2. APIベースURLが正しいか (現在: {args.api_base})")
            logger.error(f" 3. ファイアウォールが接続を許可しているか")
            logger.error("接続テストをスキップするには --skip_connection_test を使用してください")
            sys.exit(1)
        
        # モデル確認
        if not check_model_exists(args.api_base, args.model):
            logger.error(f"モデル '{args.model}' がインストールされていないようです")
            logger.error(f"インストールコマンド: ollama pull {args.model}")
            logger.error("モデル確認をスキップするには --skip_connection_test を使用してください")
            sys.exit(1)
    
    # ディレクトリの存在確認
    if not os.path.exists(args.dir_image):
        logger.error(f"指定されたディレクトリが存在しません: {args.dir_image}")
        sys.exit(1)
    
    # 保存先ディレクトリの作成
    os.makedirs(args.dir_save, exist_ok=True)
    
    # スレッド数の設定
    if args.threads is None:
        args.threads = max(1, multiprocessing.cpu_count() - 1)
        logger.info(f"スレッド数を自動設定しました: {args.threads}")
    
    # 設定情報の表示
    logger.info(f"モデル: {args.model}")
    logger.info(f"API Base URL: {args.api_base}")
    logger.info(f"スレッド数: {args.threads}")
    if args.add_tag:
        logger.info(f"追加タグ: {args.add_tag} (位置: {args.add_tag_position})")
    
    # フォルダごと処理するかの分岐
    if args.by_folder and os.path.isdir(args.dir_image):
        folders = [f.path for f in os.scandir(args.dir_image) if f.is_dir()]
        logger.info(f"{len(folders)}個のフォルダを処理します")
        for folder in folders:
            process_directory(args, folder)
    else:
        process_directory(args, args.dir_image)
    
    logger.info("すべての処理が完了しました")

def process_directory(args, directory):
    """ディレクトリ内の画像を処理する関数"""
    logger.info(f"処理対象ディレクトリ: {directory}")
    
    # 画像ファイルのリストを取得
    image_files = get_image_files(directory, args.recursive)
    if not image_files:
        logger.warning(f"処理対象の画像ファイルが見つかりませんでした: {directory}")
        return
    
    logger.info(f"合計 {len(image_files)} 個の画像を処理します")
    
    # 結果を格納するディクショナリ
    results = {}
    
    # ThreadPoolExecutorを使用してマルチスレッド処理
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        # 各画像ファイルの保存先パスを計算
        save_paths = [get_save_path(args, img_path) for img_path in image_files]
        
        # デバッグモードの場合は保存先パスを表示
        if args.debug:
            for img_path, save_path in zip(image_files[:5], save_paths[:5]):
                logger.debug(f"計画: {img_path} -> {save_path}")
            if len(image_files) > 5:
                logger.debug(f"... 他 {len(image_files) - 5} ファイル")
        
        # 進捗バーの表示
        with tqdm(total=len(image_files), desc="画像キャプション生成中") as progress_bar:
            # 画像処理のタスクをスケジュール
            futures = [
                executor.submit(process_image, args, img_path, save_path, results)
                for img_path, save_path in zip(image_files, save_paths)
            ]
            
            # 完了したタスクを処理
            for future in futures:
                try:
                    future.result()
                    progress_bar.update(1)
                except Exception as e:
                    logger.error(f"タスク実行中にエラーが発生しました: {str(e)}")
                    if args.debug:
                        traceback.print_exc()
    
    # メモリキャッシュが有効なら、処理完了後にまとめて保存
    if args.mem_cache and results:
        logger.info("キャプションをファイルに保存しています...")
        with tqdm(total=len(results), desc="ファイル保存中") as progress_bar:
            for image_path, data in results.items():
                save_caption(data["caption"], data["save_path"])
                progress_bar.update(1)
    
    logger.info(f"{len(image_files)} 個の画像の処理が完了しました")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("ユーザーにより処理が中断されました")
        sys.exit(0)
    except Exception as e:
        logger.error(f"予期せぬエラーが発生しました: {str(e)}")
        traceback.print_exc()
        sys.exit(1)