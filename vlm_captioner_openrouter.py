#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
vlm_captioner.py - Vision Language Model Captioning Script
Uses Openrouter API to generate captions for images
"""

import argparse
import base64
import concurrent.futures
import json
import logging
import os
import signal
import sys
import time
import traceback
from typing import List, Dict, Any, Optional, Tuple, Union

import requests
from tqdm import tqdm

# グローバル変数
DEBUG = False
TERMINATE = False
DEFAULT_THREADS = max(1, os.cpu_count() - 1) if os.cpu_count() else 4


def setup_logger():
    """ロガーの設定"""
    logger = logging.getLogger("vlm-captioner")
    logger.setLevel(logging.INFO)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


logger = setup_logger()


def signal_handler(sig, frame):
    """SIGINTハンドラ - 処理を安全に中断"""
    global TERMINATE
    logger.info("中断シグナルを受信しました。処理を終了します...")
    TERMINATE = True


signal.signal(signal.SIGINT, signal_handler)


def parse_arguments():
    """コマンドライン引数の解析"""
    parser = argparse.ArgumentParser(description="VLMを使用して画像キャプションを生成するスクリプト")
    
    # 一般的なオプション
    parser.add_argument("--dir_image", required=True, help="処理対象ディレクトリまたはファイル")
    parser.add_argument("--recursive", type=bool, default=True, help="サブディレクトリを再帰的に探索するか")
    parser.add_argument("--dir_save", default=os.path.join(".", "output"), help="出力ディレクトリ")
    parser.add_argument("--preserve_own_folder", type=bool, default=True, 
                      help="処理対象ディレクトリ名でフォルダを作成してデータを保存")
    parser.add_argument("--preserve_structure", type=bool, default=True, 
                      help="ディレクトリ構造を保持してデータを保存")
    parser.add_argument("--by_folder", action="store_true", 
                      help="ディレクトリ内の各フォルダを個別に処理")
    parser.add_argument("--debug", action="store_true", help="デバッグモード")
    
    # OpenRouter API用オプション
    parser.add_argument("--model", default="openai/gpt-4o", help="使用するモデル")
    parser.add_argument("--prompt", default="Describe this image in detail", 
                      help="VLM用の推論プロンプト")
    parser.add_argument("--api", required=True, help="OpenRouter APIキー")
    parser.add_argument("--temperature", type=float, default=0.7, help="生成温度 (0-2)")
    parser.add_argument("--max_tokens", type=int, default=300, help="最大トークン数")
    parser.add_argument("--top_p", type=float, default=1.0, help="Top-p サンプリング (0-1)")
    parser.add_argument("--top_k", type=int, help="Top-k サンプリング (>0)")
    parser.add_argument("--frequency_penalty", type=float, help="頻度ペナルティ (-2 to 2)")
    parser.add_argument("--presence_penalty", type=float, help="存在ペナルティ (-2 to 2)")
    parser.add_argument("--repetition_penalty", type=float, help="繰り返しペナルティ (0-2)")
    parser.add_argument("--seed", type=int, help="生成の再現性のためのシード値")
    
    # キャプション用オプション
    parser.add_argument("--add_tag", help="キャプションに追加するタグ")
    parser.add_argument("--add_tag_position", default="first", choices=["first", "last"], 
                      help="タグを追加する位置")
    
    # 処理オプション
    parser.add_argument("--mem_cache", type=bool, default=True, 
                      help="メモリキャッシュを有効にするか")
    parser.add_argument("--threads", type=int, default=DEFAULT_THREADS, 
                      help=f"使用するスレッド数 (デフォルト: {DEFAULT_THREADS})")
    
    args = parser.parse_args()
    
    # promptがファイルの場合、ファイルからプロンプトを読み込む
    if os.path.isfile(args.prompt):
        with open(args.prompt, 'r', encoding='utf-8') as f:
            args.prompt = f.read().strip()
    
    return args


def get_image_files(path: str, recursive: bool = True) -> List[str]:
    """
    指定パスから画像ファイルのリストを取得
    
    Args:
        path: 検索対象のパスまたはファイル
        recursive: サブディレクトリを再帰的に探索するか
        
    Returns:
        画像ファイルパスのリスト
    """
    image_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
    
    if os.path.isfile(path):
        if path.lower().endswith(image_extensions):
            return [path]
        return []
    
    image_files = []
    
    if recursive:
        for root, _, files in os.walk(path):
            for file in files:
                if file.lower().endswith(image_extensions):
                    image_files.append(os.path.join(root, file))
    else:
        for file in os.listdir(path):
            file_path = os.path.join(path, file)
            if os.path.isfile(file_path) and file.lower().endswith(image_extensions):
                image_files.append(file_path)
    
    return sorted(image_files)


def encode_image_to_base64(image_path: str) -> str:
    """
    画像をBase64エンコード
    
    Args:
        image_path: 画像ファイルのパス
        
    Returns:
        Base64エンコードされた画像データ (data URL形式)
    """
    with open(image_path, "rb") as image_file:
        encoded_bytes = base64.b64encode(image_file.read())
        encoded_string = encoded_bytes.decode('utf-8')
        
        # MIMEタイプを判定
        ext = os.path.splitext(image_path)[1].lower()
        if ext in ('.jpg', '.jpeg'):
            mime_type = 'image/jpeg'
        elif ext == '.png':
            mime_type = 'image/png'
        elif ext == '.webp':
            mime_type = 'image/webp'
        else:  # .bmp など
            mime_type = 'image/jpeg'  # デフォルト
            
        return f"data:{mime_type};base64,{encoded_string}"


def generate_caption(
    image_path: str, 
    api_key: str, 
    model: str, 
    prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 300,
    top_p: float = 1.0,
    top_k: Optional[int] = None,
    frequency_penalty: Optional[float] = None,
    presence_penalty: Optional[float] = None,
    repetition_penalty: Optional[float] = None,
    seed: Optional[int] = None,
    retries: int = 3,
    retry_delay: float = 2.0
) -> Tuple[bool, str]:
    """
    VLMを使用して画像のキャプションを生成
    
    Args:
        image_path: 画像ファイルのパス
        api_key: OpenRouter APIキー
        model: 使用するモデル名
        prompt: VLM用の推論プロンプト
        temperature: 生成温度
        max_tokens: 最大トークン数
        top_p: Top-p サンプリング
        top_k: Top-k サンプリング
        frequency_penalty: 頻度ペナルティ
        presence_penalty: 存在ペナルティ
        repetition_penalty: 繰り返しペナルティ
        seed: 生成の再現性のためのシード値
        retries: リトライ回数
        retry_delay: リトライ間の待機時間(秒)
        
    Returns:
        (成功したか, キャプション文字列)
    """
    if DEBUG:
        logger.info(f"[DEBUG] 画像処理: {image_path}")
        return True, "デバッグモード: キャプション生成はスキップされました"
    
    # 画像をBase64エンコード
    try:
        base64_image = encode_image_to_base64(image_path)
    except Exception as e:
        logger.error(f"画像のエンコード中にエラーが発生しました: {image_path} - {str(e)}")
        return False, f"エラー: {str(e)}"
    
    # APIリクエストの準備
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "vlm-captioner/1.0"
    }
    
    # リクエストボディの作成
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": base64_image
                        }
                    }
                ]
            }
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p
    }
    
    # オプションパラメータの追加
    if top_k is not None:
        payload["top_k"] = top_k
    if frequency_penalty is not None:
        payload["frequency_penalty"] = frequency_penalty
    if presence_penalty is not None:
        payload["presence_penalty"] = presence_penalty
    if repetition_penalty is not None:
        payload["repetition_penalty"] = repetition_penalty
    if seed is not None:
        payload["seed"] = seed
    
    # リトライを含むAPIリクエスト
    for attempt in range(retries):
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    message = result["choices"][0].get("message", {})
                    caption = message.get("content", "")
                    return True, caption.strip()
                else:
                    logger.warning(f"APIから有効な応答がありません: {result}")
            else:
                logger.warning(f"API呼び出しがエラーを返しました (試行 {attempt+1}/{retries}): "
                             f"ステータスコード {response.status_code}, レスポンス: {response.text}")
        
        except Exception as e:
            logger.error(f"API呼び出し中にエラーが発生しました (試行 {attempt+1}/{retries}): {str(e)}")
            
        if attempt < retries - 1:
            logger.info(f"{retry_delay}秒後にリトライします...")
            time.sleep(retry_delay)
    
    return False, "キャプション生成に失敗しました"


def apply_tag(caption: str, tag: str, position: str = "first") -> str:
    """
    キャプションにタグを追加
    
    Args:
        caption: 元のキャプション
        tag: 追加するタグ
        position: タグを追加する位置 ("first" または "last")
        
    Returns:
        タグが追加されたキャプション
    """
    if not tag:
        return caption
    
    if position == "first":
        return f"{tag}, {caption}"
    else:  # "last"
        return f"{caption}, {tag}"


def get_output_path(
    input_path: str, 
    dir_image: str, 
    dir_save: str, 
    preserve_own_folder: bool, 
    preserve_structure: bool
) -> str:
    """
    出力ファイルのパスを生成
    
    Args:
        input_path: 入力ファイルのパス
        dir_image: 処理対象ディレクトリ
        dir_save: 出力ディレクトリ
        preserve_own_folder: 処理対象ディレクトリ名でフォルダを作成するか
        preserve_structure: ディレクトリ構造を保持するか
        
    Returns:
        出力ファイルのパス
    """
    # 出力ディレクトリのベースを設定
    base_save_dir = dir_save
    
    if preserve_own_folder:
        # 処理対象ディレクトリの名前を取得
        base_dir_name = os.path.basename(os.path.abspath(dir_image))
        base_save_dir = os.path.join(dir_save, base_dir_name)
    
    if preserve_structure:
        # 相対パスを計算し、出力パスに適用
        rel_path = os.path.relpath(input_path, dir_image)
        rel_dir = os.path.dirname(rel_path)
        file_name = os.path.basename(input_path)
        
        # 拡張子をtxtに変更
        txt_name = os.path.splitext(file_name)[0] + ".txt"
        
        # 出力パスを構築
        output_path = os.path.join(base_save_dir, rel_dir, txt_name)
    else:
        # 単純にファイル名だけを使用
        file_name = os.path.basename(input_path)
        txt_name = os.path.splitext(file_name)[0] + ".txt"
        output_path = os.path.join(base_save_dir, txt_name)
    
    return output_path


def process_image(
    image_path: str,
    api_key: str,
    model: str,
    prompt: str,
    dir_image: str,
    dir_save: str,
    add_tag: Optional[str],
    add_tag_position: str,
    preserve_own_folder: bool,
    preserve_structure: bool,
    temperature: float,
    max_tokens: int,
    top_p: float,
    top_k: Optional[int],
    frequency_penalty: Optional[float],
    presence_penalty: Optional[float],
    repetition_penalty: Optional[float],
    seed: Optional[int]
) -> Dict[str, Any]:
    """
    1つの画像を処理し、キャプションを生成
    
    Args:
        各種パラメータ
        
    Returns:
        処理結果の辞書
    """
    global TERMINATE
    
    if TERMINATE:
        return {"path": image_path, "success": False, "caption": "処理が中断されました", "output_path": None}
    
    try:
        # キャプション生成
        success, caption = generate_caption(
            image_path, 
            api_key, 
            model, 
            prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            top_k=top_k,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            repetition_penalty=repetition_penalty,
            seed=seed
        )
        
        # タグ適用
        if success and add_tag:
            caption = apply_tag(caption, add_tag, add_tag_position)
        
        # 出力パス計算
        output_path = get_output_path(
            image_path, 
            dir_image, 
            dir_save, 
            preserve_own_folder, 
            preserve_structure
        )
        
        return {
            "path": image_path,
            "success": success,
            "caption": caption,
            "output_path": output_path
        }
        
    except Exception as e:
        logger.error(f"画像処理中にエラーが発生しました: {image_path}\n{traceback.format_exc()}")
        return {
            "path": image_path,
            "success": False,
            "caption": f"エラー: {str(e)}",
            "output_path": None
        }


def save_results(results: List[Dict[str, Any]]) -> Tuple[int, int]:
    """
    結果をファイルに保存
    
    Args:
        results: 処理結果のリスト
        
    Returns:
        (成功件数, 失敗件数)
    """
    success_count = 0
    failure_count = 0
    
    for result in results:
        if not result["success"] or not result["output_path"]:
            failure_count += 1
            continue
        
        try:
            # 出力ディレクトリが存在しない場合は作成
            os.makedirs(os.path.dirname(result["output_path"]), exist_ok=True)
            
            # キャプションをファイルに保存
            with open(result["output_path"], 'w', encoding='utf-8') as f:
                f.write(result["caption"])
            
            success_count += 1
            
        except Exception as e:
            logger.error(f"キャプション保存中にエラーが発生しました: {result['path']} -> {result['output_path']}\n{str(e)}")
            failure_count += 1
    
    return success_count, failure_count


def process_directory(args, target_dir: str = None) -> None:
    """
    指定されたディレクトリを処理
    
    Args:
        args: コマンドライン引数
        target_dir: 処理対象ディレクトリ (None の場合は args.dir_image を使用)
    """
    global DEBUG
    DEBUG = args.debug
    
    if DEBUG:
        logger.info("[DEBUG モード有効] 実際の処理は行われません")
    
    dir_to_process = target_dir if target_dir else args.dir_image
    logger.info(f"処理開始: {dir_to_process}")
    
    # 画像ファイルのリストを取得
    image_files = get_image_files(dir_to_process, args.recursive)
    if not image_files:
        logger.warning(f"処理対象の画像ファイルが見つかりませんでした: {dir_to_process}")
        return
    
    logger.info(f"{len(image_files)}個の画像ファイルを処理します")
    
    # マルチスレッド処理の準備
    results = []
    threads = min(args.threads, len(image_files))
    
    # ThreadPoolExecutor で並列処理
    with tqdm(total=len(image_files), desc="画像処理") as pbar:
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_image = {
                executor.submit(
                    process_image,
                    image_path=image_path,
                    api_key=args.api,
                    model=args.model,
                    prompt=args.prompt,
                    dir_image=dir_to_process,
                    dir_save=args.dir_save,
                    add_tag=args.add_tag,
                    add_tag_position=args.add_tag_position,
                    preserve_own_folder=args.preserve_own_folder,
                    preserve_structure=args.preserve_structure,
                    temperature=args.temperature,
                    max_tokens=args.max_tokens,
                    top_p=args.top_p,
                    top_k=args.top_k,
                    frequency_penalty=args.frequency_penalty,
                    presence_penalty=args.presence_penalty,
                    repetition_penalty=args.repetition_penalty,
                    seed=args.seed
                ): image_path for image_path in image_files
            }
            
            for future in concurrent.futures.as_completed(future_to_image):
                result = future.result()
                if args.mem_cache:
                    results.append(result)
                else:
                    # メモリキャッシュを使用しない場合は即時保存
                    save_results([result])
                pbar.update(1)
                
                if TERMINATE:
                    break
    
    # メモリキャッシュを使用している場合は、全処理完了後に一括保存
    if args.mem_cache and results:
        logger.info("キャプションをファイルに保存しています...")
        success_count, failure_count = save_results(results)
        logger.info(f"処理完了: 成功={success_count}, 失敗={failure_count}")
    
    logger.info(f"ディレクトリ処理完了: {dir_to_process}")


def main():
    """メイン関数"""
    args = parse_arguments()
    
    # by_folder オプションの処理
    if args.by_folder and os.path.isdir(args.dir_image):
        # 対象ディレクトリ内のサブディレクトリを個別に処理
        for item in os.listdir(args.dir_image):
            item_path = os.path.join(args.dir_image, item)
            if os.path.isdir(item_path):
                process_directory(args, item_path)
                
                if TERMINATE:
                    logger.info("処理を中断しました")
                    break
    else:
        # 1つのディレクトリとして処理
        process_directory(args)
    
    logger.info("すべての処理が完了しました")


if __name__ == "__main__":
    main()
