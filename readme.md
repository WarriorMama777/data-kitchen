
- [▼日本語](#日本語)
- [data-kitchen🍳](#data-kitchen)
  - [概要](#概要)
  - [プログラムについて](#プログラムについて)
  - [主な機能](#主な機能)
  - [インストール](#インストール)
    - [必要な環境](#必要な環境)
    - [インストール手順](#インストール手順)
  - [使い方](#使い方)
    - [image\_converter\_pillow.py](#image_converter_pillowpy)
      - [スクリプトの概要](#スクリプトの概要)
      - [引数の解説一覧](#引数の解説一覧)
      - [実行コマンドサンプル](#実行コマンドサンプル)
    - [image\_converter\_wand.py](#image_converter_wandpy)
      - [引数](#引数)
      - [実行コマンドサンプル](#実行コマンドサンプル-1)
    - [fire\_organizer.py](#fire_organizerpy)
      - [スクリプトの概要](#スクリプトの概要-1)
      - [引数の解説一覧](#引数の解説一覧-1)
      - [実行コマンドサンプル](#実行コマンドサンプル-2)
    - [downloader\_danbooru.py](#downloader_danboorupy)
      - [引数の解説一覧](#引数の解説一覧-2)
        - [実行コマンドサンプル](#実行コマンドサンプル-3)
    - [downloader\_e621.py](#downloader_e621py)
      - [スクリプトの概要](#スクリプトの概要-2)
      - [引数の解説一覧](#引数の解説一覧-3)
      - [実行コマンドサンプル](#実行コマンドサンプル-4)
    - [fancaps\_episode\_downloader.py](#fancaps_episode_downloaderpy)
      - [スクリプトの概要](#スクリプトの概要-3)
      - [引数の解説一覧](#引数の解説一覧-4)
      - [実行コマンドサンプル](#実行コマンドサンプル-5)
    - [image\_cleaner.py](#image_cleanerpy)
      - [概要](#概要-1)
      - [引数一覧](#引数一覧)
      - [実行コマンドサンプル](#実行コマンドサンプル-6)
      - [しきい値のガイドライン](#しきい値のガイドライン)
    - [Danbooruメタデータコンバータスクリプト：metadata\_converter\_danbooru.py](#danbooruメタデータコンバータスクリプトmetadata_converter_danboorupy)
      - [概要](#概要-2)
      - [引数一覧](#引数一覧-1)
      - [仕様](#仕様)
      - [実行コマンドサンプル](#実行コマンドサンプル-7)
    - [EXIFリムーバースクリプト: exif\_remover.py](#exifリムーバースクリプト-exif_removerpy)
      - [概要](#概要-3)
      - [引数一覧](#引数一覧-2)
      - [実行コマンドサンプル](#実行コマンドサンプル-8)
  - [コントリビューション](#コントリビューション)
  - [ライセンス](#ライセンス)
  - [作者](#作者)
- [▼English](#english)
- [data-kitchen 🍳](#data-kitchen-)
  - [Overview](#overview)
  - [About the Program](#about-the-program)
  - [Main Features](#main-features)
  - [Installation](#installation)
    - [Required Environment](#required-environment)
    - [Installation Steps](#installation-steps)
  - [Usage](#usage)
    - [image\_converter\_pillow.py](#image_converter_pillowpy-1)
      - [Script Overview](#script-overview)
      - [Explanation of Arguments](#explanation-of-arguments)
      - [Sample Execution Command](#sample-execution-command)
    - [image\_converter\_wand.py](#image_converter_wandpy-1)
      - [Arguments](#arguments)
      - [Sample Execution Command](#sample-execution-command-1)
    - [fire\_organizer.py](#fire_organizerpy-1)
      - [Script Overview](#script-overview-1)
      - [Explanation of Arguments](#explanation-of-arguments-1)
      - [Sample Execution Command](#sample-execution-command-2)
    - [downloader\_danbooru.py](#downloader_danboorupy-1)
      - [Explanation of Arguments](#explanation-of-arguments-2)
        - [Sample Execution Command](#sample-execution-command-3)
    - [downloader\_e621.py](#downloader_e621py-1)
      - [Script Overview](#script-overview-2)
      - [Explanation of Arguments](#explanation-of-arguments-3)
      - [Sample Execution Command](#sample-execution-command-4)
    - [fancaps\_episode\_downloader.py](#fancaps_episode_downloaderpy-1)
      - [Script Overview](#script-overview-3)
      - [Explanation of Arguments](#explanation-of-arguments-4)
      - [Sample Execution Command](#sample-execution-command-5)
    - [image\_cleaner.py](#image_cleanerpy-1)
      - [Overview](#overview-1)
      - [Argument List](#argument-list)
      - [Sample Execution Command](#sample-execution-command-6)
      - [Threshold Guidelines](#threshold-guidelines)
    - [Danbooru Metadata Converter Script: metadata\_converter\_danbooru.py](#danbooru-metadata-converter-script-metadata_converter_danboorupy)
      - [Overview](#overview-2)
      - [Argument List](#argument-list-1)
      - [Specifications](#specifications)
      - [Sample Execution Command](#sample-execution-command-7)
    - [EXIF Remover Script: exif\_remover.py](#exif-remover-script-exif_removerpy)
      - [Overview](#overview-3)
      - [Argument List](#argument-list-2)
      - [Sample Execution Command](#sample-execution-command-8)
  - [Contribution](#contribution)
  - [License](#license)
  - [Author](#author)

# ▼日本語

# data-kitchen🍳

## 概要

「data-kitchen」は、収集した画像やメタデータなどを前処理するためのスクリプト集です。画像生成AIなどの機械学習用データセット作成を効率化するためのツールを提供します。

![](https://raw.githubusercontent.com/WarriorMama777/imgup/main/img/__Repository/Github/data-kitchen/WebAssets_heroimage_data-kitchen_03_comp001.webp "WarriorMama777/data-kitchen")

## プログラムについて

重要：このリポジトリのすべてのプログラムはChatGPT4等によって書かれています。私はノンプログラマーであり、1行もコードは書いていないことをご了承ください。

## 主な機能

- 画像のダウンロード
- メタデータの取得と処理
- 画像の前処理（リサイズ、フィルタリング、アノテーションなど）
- データセットの作成と管理

## インストール

### 必要な環境

- Python 3.x

### インストール手順

1.  リポジトリをクローンします。

```cmd
git clone https://github.com/WarriorMama777/data-kitchen.git
```

```
cd data-kitchen
```

2.  (推奨)Pythonの仮想環境を作成します

```cmd
python -m venv venv
```

3.  Pythonの仮想環境をアクティブにします

- Windows

```cmd
.\venv\Scripts\activate
```

- Linux

```
source venv/bin/activate
```

4.  必要なライブラリをインストールします。

```cmd
pip install -r requirements.txt
```

5.  完了  
    処理する目的に沿ったスクリプトを選択して実行します。  
    例: tag_editor.py

```
python tag_editor.py --dir .\data --save_dir .\output --extension txt --del_first 5 --add_last _edited
```

## 使い方

### image_converter_pillow.py

#### スクリプトの概要

pillowを使用した画像変換処理スクリプトです。

#### 引数の解説一覧

- `--dir`: 必須。対象ディレクトリ
- `--save_dir`: 出力ディレクトリ。デフォルトは 'output/'
- `--extension`: 必須。対象ファイルの拡張子
- `--recursive`: サブディレクトリを処理する場合は指定
- `--background`: 透明画像の背景色
- `--resize`: 画像の最大サイズを指定してリサイズ
- `--format`: 出力画像のフォーマット
- `--quality`: 出力画像の品質
- `--comp`: 圧縮レベル
- `--debug`: デバッグモード
- `--preserve_own_folder`: 元のディレクトリ構造を保持
- `--preserve_structure`: ディレクトリ構造を保持
- `--gc_disable`: ガベージコレクションを無効にする
- `--by_folder`: フォルダごとに処理する
- `--mem_cache`: メモリキャッシュを使用するかどうか
- `--threads`: 使用するスレッド数
- `--save_only_alphachannel`: アルファチャンネルデータのみ保存

#### 実行コマンドサンプル

Basic

```bash
python image_converter_pillow.py --dir "/path/to/directory" --extension jpg png --recursive --background FFFFFF --resize 300 --format JPEG --quality 80 --threads 4
```

Exsample  
以下は実際のコマンド例です。指定されたディレクトリ内の画像ファイル（jpg、png、webp）を指定された形式(webp)に変換し、指定された保存先ディレクトリに保存します。  
また、変換された画像の品質は90に設定され、圧縮率を4に、解像度は2048ピクセルにリサイズされ、背景色はffffff(完全な白背景)に設定されます。さらに、ガベージコレクションを無効化し、20個のスレッドを使用して並列で処理されるように設定しています。  
また、`--preserve_own_folder`によって、保存先には変換元の対象フォルダである"id_990001__1005000"が新規作成されて、そこに変換された画像が保存されます。

```bash
python image_converter_pillow.py --dir "H:\Resources\images_by_15000id_02\id_990001__1005000" --save_dir "H:\Resources\webp\images_by_15000id_02" --extension jpg png webp --preserve_own_folder --format webp --quality 90 --comp 4 --resize 2048 --background ffffff --gc_disable --threads 20
```

### image_converter_wand.py

image magick のpythonラッパーであるwandを使用した画像変換処理スクリプトです。通常はpillowバージョンで十分で、あえて使う必要はないでしょう。使用するにはimage magickがインストールされている必要があります。例えばchocolateyでインストールします。`choco install imagemagick` (Windows)

#### 引数

- `--dir`: 処理対象ディレクトリ
- `--save_dir`: 出力ディレクトリ
- `--extension`: 処理対象となるファイルの拡張子
- `--recursive`: サブディレクトリも含めて探索
- `--background`: 透過画像の背景色 例：#ffffff
- `--resize`: リサイズする長辺のサイズ
- `--format`: 変換後の画像形式
- `--quality`: 画像品質
- `--comp`: 画像圧縮の強度
- `--debug`: デバッグモード
- `--preserve_own_folder`: 元のフォルダ名を保持
- `--preserve_structure`: ディレクトリ構造を保持
- `--gc_disable`: ガベージコレクションを無効化
- `--by_folder`: フォルダごとに処理
- `--mem_cache`: メモリキャッシュの使用 (ON / OFF)
- `--threads`: 使用するスレッド数

#### 実行コマンドサンプル

```bash
python image_converter_wand.py --dir input_images/ --save_dir "./output_images" --extension jpg jpeg png --recursive --resize 800 --format jpeg --quality 80 --comp 6 --debug
```

### fire_organizer.py

#### スクリプトの概要

このスクリプトは、指定したディレクトリ内のファイルを整頓するためのものです。

#### 引数の解説一覧

- --copy: ファイルをコピーします
- --cut: ファイルを切り取ります
- --dir: 処理対象となるディレクトリ
- --extensions: 処理対象となるファイルの拡張子
- --file_name: 処理対象となるファイル名
- --save: 処理対象ファイルを保存するディレクトリ
- --preserve_structure: ディレクトリの構造を保持してファイルを保存します
- --preserve_own_folder: `--dir`で指定されたディレクトリ自体のフォルダを`--save`の場所に作成します
- --debug: デバッグ情報を表示します
- --processes: 使用するプロセス数
- --multi_threading: マルチスレッド処理を有効にします
- --gc-disable: ガベージコレクションを無効にします

#### 実行コマンドサンプル

```python
python fire_organizer.py --copy --dir "/input/directory" --extensions .txt --save "/output/directory" --preserve_structure --processes 4
```

### downloader_danbooru.py

※gallery-dlを使ったほうが早いので使う必要はほとんどありません。  
このスクリプトは、指定したタグでDanbooruからコンテンツをスクレイピングするためのものです。

#### 引数の解説一覧

- --tags: コンテンツをダウンロードする際に検索するタグを指定します。
- --output: 出力ディレクトリを指定します。(デフォルト: output/)
- --url: DanbooruのAPIコールを行うためのURLを指定します。(デフォルト: https://danbooru.donmai.us)
- --page_limit: ダウンロード時に解析する最大ページ数を指定します。(デフォルト: 1000)
- --api_key: DanbooruのAPIキーを指定します。高レベルのアカウントをリンクして制限を超える場合にのみ必要です。ユーザー名も指定する必要があります。
- --username: Danbooruにログインするためのユーザー名を指定します。api_keyと共に指定する必要があります。
- --max_file_size: デフォルトのファイルサイズではなく、最大利用可能なファイルサイズをダウンロードしようとします。
- --extensions: ダウンロードするファイルの拡張子を指定します。カンマ区切りで複数指定できます。(デフォルト: .png,.jpg)
- --save_tags: 各画像のタグを同じ名前のテキストファイルに保存します。
- --tags_only: 画像をダウンロードせず、存在する画像のタグのみを保存します。
- --write_translation: 画像内の外国語の翻訳をタグファイルに書き込みます。
- --year_start: 内容をダウンロードするための開始年を指定します。フォーマット: YYYY
- --year_end: 内容をダウンロードするための終了年を指定します。フォーマット: YYYY

##### 実行コマンドサンプル

```bash
python downloader_danbooru.py --tags "cat" --output "./downloaded_images" --page_limit 500 --api_key "api_key_here" --username "username_here" --extensions ".png,.jpg" --save_tags --year_start 2020 --year_end 2022
```

### downloader_e621.py

#### スクリプトの概要

※gallery-dlを使ったほうが早いので使う必要はほとんどありません。  
このスクリプトは、e621から指定したタグや検索キーワードに関連する画像を取得し、それらの画像とメタデータを保存するためのものです。

#### 引数の解説一覧

- ターゲットのタグまたは検索キーワードを入力してください。
- 取得するページ数を入力してください。
- 画像を保存するディレクトリ名を入力してください。

#### 実行コマンドサンプル

```python
python downloader_e621.py
Enter the target tag or search keyword: cat
Enter the number of pages to retrieve: 3
Enter the name of the directory to save images: cat_images
```

### fancaps_episode_downloader.py

#### スクリプトの概要

このスクリプトは、fancapsサイトから、指定されたエピソードURLに含まれるスクリーンショット画像をクローリングしてダウンロードするためのツールです。  
次のリポジトリのコードをベースとして改良させていただきました：[m-patino/fancaps-downloader: Fancaps Downloader](https://github.com/m-patino/fancaps-downloader)

#### 引数の解説一覧

- url: ダウンロードを開始するURL
- --output: ダウンロード先のフォルダのパス（デフォルトは"Downloads"）

#### 実行コマンドサンプル

```python
python fancaps_episode_downloader.py "https://fancaps.net/anime/episodeimages.php?21914-hack_Roots/Episode_1" --output "./Downloads"
```

### image_cleaner.py

#### 概要

このスクリプトは、指定されたディレクトリ内の画像ファイルを処理し、重複した画像を検出して整理します。

#### 引数一覧

- `--dir`: 処理するディレクトリ（必須）
- `--save_dir`: 重複していない画像を保存するディレクトリ（デフォルト: `output/`）
- `--save_dir_duplicate`: 重複した画像を保存するディレクトリ
- `--extension`: 処理する画像の拡張子（デフォルト: `jpg png webp`）
- `--recursive`: ディレクトリを再帰的に検索する（オプション）
- `--debug`: デバッグモード（オプション）
- `--threshold`: 重複判定のためのハミング距離閾値（デフォルト: 10）
- `--preserve_own_folder`: 自身のフォルダ構造を保持する（オプション）
- `--preserve_structure`: ディレクトリ構造を保持する（オプション）
- `--gc_disable`: ガベージコレクションを無効にする（オプション）
- `--by_folder`: フォルダ単位で処理する（オプション）
- `--process_group`: 処理グループの画像数（デフォルト: 2）
- `--mem_cache`: メモリキャッシュを有効にする（デフォルト: 有効）

#### 実行コマンドサンプル

```python
python image_cleaner.py --dir "/path/to/images" --save_dir "/path/to/output" --threshold 5 --recursive --preserve_structure
```

#### しきい値のガイドライン

dhash（差分ハッシュ）を使用して画像の類似性を判定する際の適切なしきい値（Hamming距離の閾値）は、具体的な用途や画像の性質に依存しますが、一般的には以下のようなガイドラインを参考にしてみてください。

- **厳密な一致を求める場合（同一画像の検出）**:
    
    - しきい値: **5以下**
    - この設定は、ほぼ同一の画像（ごくわずかな違いのみ）を重複として検出します。
- **一般的な類似性の検出**:
    
    - しきい値: **10前後**
    - この範囲は、ほとんど同じ画像（色合いや小さな変更を含む）を検出するのに適しています。多くの用途でこれがデフォルトのしきい値として使われます。
- **より緩やかな類似性の検出**:
    
    - しきい値: **15以上**
    - これは、かなり異なる画像でも類似性があると見なしたい場合に使用します。ただし、この設定では誤検出（本来異なる画像を重複と判定する）の可能性が増加します。

### Danbooruメタデータコンバータスクリプト：metadata_converter_danbooru.py

#### 概要

このスクリプトは、Danbooruのjsonメタデータファイルをプレーンテキスト形式に変換します。

#### 引数一覧

- `--dir`: メタデータファイルが含まれるディレクトリ（必須）
- `--save_dir`: 変換されたファイルを保存するディレクトリ（必須）
- `--metadata_order`: 抽出するメタデータラベルの順序。例: `--metadata_order "title" "artist" "tags"`（必須）
- `--insert_custom_text`: 出力にカスタムテキストを指定されたインデックスに挿入する。例: `--insert_custom_text 2 "CUSTOM_TEXT"`（任意）
- `--debug`: デバッグモードを有効にして、実際の変更を行わずに処理ログを表示する（オプション）
- `--save_extension`: 出力ファイルの拡張子（デフォルト: `txt`）（任意）
- `--mem_cache`: メモリキャッシュを有効または無効にする。デフォルトは`ON`（任意）
- `--threads`: 使用するスレッド数。デフォルトはCPUコア数（任意）
- `--recursive`: ディレクトリを再帰的に処理する（オプション）
- `--preserve_own_folder`: 保存ディレクトリ内に自身のフォルダ構造を保持する（オプション）
- `--preserve_structure`: 保存ディレクトリ内にディレクトリ構造を保持する（オプション）
- `--gc_disable`: ガベージコレクションを無効にする（オプション）
- `--by_folder`: 各フォルダを一つずつ処理する（オプション）

#### 仕様

- `--dir`で指定するディレクトリにあるjsonメタデータファイルは、次のような形式で記述されていることが期待されます。これは基本的には、gallery-dlの`--write-metadata`引数を渡してダウンロードすると得られます。：[json metadata example](https://github.com/WarriorMama777/data-kitchen/blob/main/example/metadata/danbooru_1_d34e4cf0a437a5d65f8e82b7bcd02606.json)

#### 実行コマンドサンプル

```python
python metadata_converter_danbooru.py --metadata_order "tag_string_artist" "tag_string_copyright" "tag_string_character" "tag_string_general" "rating" --dir "/path/to/metadata" --save_dir "/path/to/output" --insert_custom_text 3 "illustration,|||" 4 "|||" --recursive --preserve_own_folder --preserve_structure --gc_disable --by_folder
```

### EXIFリムーバースクリプト: exif_remover.py

#### 概要

このスクリプトは、画像ファイルからEXIFメタデータを削除します。内部で使用される主なライブラリは以下の通りです：

- `cv2`: 画像の読み込みおよび保存

#### 引数一覧

- `--dir`: 対象とするディレクトリ（必須）
- `--remove`: EXIFを削除する（オプション）
- `--save`: 保存するディレクトリ。指定しない場合、画像は上書きされる（オプション）
- `--cpu`: 使用するスレッド数。指定しない場合、自動的に決定される（オプション）

#### 実行コマンドサンプル

```bash
python exif_remover.py --dir "/path/to/images" --remove --save "/path/to/output" --cpu 4
```

## コントリビューション

貢献を歓迎します。バグ報告や機能提案はIssueにてお願いします。プルリクエストも歓迎です。

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 作者

- GitHub: [WarriorMama777](https://github.com/WarriorMama777)
- huggingface: [WarriorMama777](https://huggingface.co/WarriorMama777)

* * *

# ▼English

# data-kitchen 🍳

## Overview

"data-kitchen" is a collection of scripts for pre-processing images and metadata downloaded from image sites such as Danbooru, aimed at improving efficiency in creating machine learning datasets for image generation AI and other purposes.

![](https://raw.githubusercontent.com/WarriorMama777/imgup/main/img/__Repository/Github/data-kitchen/WebAssets_heroimage_data-kitchen_03_comp001.webp "WarriorMama777/data-kitchen")

## About the Program

Important: Please note that all programs in this repository are written by ChatGPT4, and I am a non-programmer who has not written a single line of code.

## Main Features

- Image downloading
- Metadata acquisition and processing
- Image pre-processing (resizing, filtering, annotation, etc.)
- Dataset creation and management

## Installation

### Required Environment

- Python 3.x

### Installation Steps

1.  Clone the repository:

```cmd
git clone https://github.com/WarriorMama777/data-kitchen.git
cd data-kitchen
```

2.  Install the required libraries:

```bash
pip install -r requirements.txt
```

## Usage

### image_converter_pillow.py

#### Script Overview

This is a script for image processing.

#### Explanation of Arguments

- `--dir`: Required. Target directory
- `--save_dir`: Output directory. Default is 'output/'
- `--extension`: Required. Target file extensions
- `--recursive`: Process subdirectories if specified
- `--background`: Background color for transparent images
- `--resize`: Resize images to have this max dimension
- `--format`: Output image format
- `--quality`: Output image quality
- `--comp`: Compression level
- `--debug`: Debug mode
- `--preserve_own_folder`: Preserve original directory structure
- `--preserve_structure`: Preserve directory structure
- `--gc_disable`: Disable garbage collection
- `--by_folder`: Process folders one by one
- `--mem_cache`: Use memory cache
- `--threads`: Number of threads to use
- `--save_only_alphachannel`: Save only alpha channel data

#### Sample Execution Command

- Basic

```bash
python image_converter_pillow.py --dir "/path/to/directory" --extension jpg png --recursive --background FFFFFF --resize 300 --format JPEG --quality 80 --threads 4
```

- Exsample  
    The following is an actual command example. It converts the image files (jpg, png, webp) in the specified directory to the specified format (webp) and saves them in the specified destination directory.  
    Additionally, the quality of the converted images is set to 90, with a compression rate of 4, a resolution resized to 2048 pixels, and a background color set to ffffff (pure white). Furthermore, garbage collection is disabled, and it is configured to be processed in parallel using 20 threads.  
    Additionally, the --preserve_own_folder flag creates a new folder in the destination directory named after the original source folder "id_990001__1005000", and the converted images are saved there.

```bash
python image_converter_pillow.py --dir "H:\Resources\images_by_15000id_02\id_990001__1005000" --save_dir "H:\Resources\webp\images_by_15000id_02" --extension jpg png webp --preserve_own_folder --format webp --quality 90 --comp 4 --resize 2048 --background ffffff --gc_disable --threads 20
```

### image_converter_wand.py

Image processing script using wand, a python wrapper for image magick. Usually, the pillow version is sufficient, so there is no need to use it.  
To use this, ImageMagick needs to be installed. For example, you can install it with Chocolatey: `choco install imagemagick` (Windows)

#### Arguments

- `--dir`: Target directory for processing
- `--save_dir`: Output directory
- `--extension`: File extensions to be processed
- `--recursive`: Include subdirectories in the search
- `--background`: Background color for transparent images (e.g., #ffffff)
- `--resize`: Size of the longer side for resizing
- `--format`: Format of the converted images
- `--quality`: Image quality
- `--comp`: Compression strength for images
- `--debug`: Debug mode
- `--preserve_own_folder`: Preserve the original folder name
- `--preserve_structure`: Preserve the directory structure
- `--gc_disable`: Disable garbage collection
- `--by_folder`: Process images by folder
- `--mem_cache`: Use memory cache (ON / OFF)
- `--threads`: Number of threads to use

#### Sample Execution Command

```bash
python image_converter_wand.py --dir input_images/ --save_dir "./output_images" --extension jpg jpeg png --recursive --resize 800 --format jpeg --quality 80 --comp 6 --debug
```

### fire_organizer.py

#### Script Overview

This script is used to organize files within a specified directory. It utilizes the following libraries: argparse, pathlib, shutil, tqdm, concurrent.futures, time, and gc.

#### Explanation of Arguments

- --copy: Copy files
- --cut: Cut files
- --dir: Directory to be processed
- --extensions: File extensions to be processed
- --file_name: Name of the file to be processed
- --save: Directory to save processed files
- --preserve_structure: Preserve the directory structure when saving files
- --preserve_own_folder: Create a folder for the specified directory at the location specified by --save
- --debug: Display debug information
- --processes: Number of processes to use
- --multi_threading: Enable multi-threaded processing
- --gc-disable: Disable garbage collection

#### Sample Execution Command

```python
python fire_organizer.py --copy --dir "/input/directory" --extensions .txt --save "/output/directory" --preserve_structure --processes 4
```

### downloader_danbooru.py

**※ There is almost no need to use this script since using gallery-dl is faster.**  
This script is used to scrape content from Danbooru based on specified tags. It utilizes the following libraries: argparse, pathlib, requests, os, json, datetime, and tqdm.

#### Explanation of Arguments

- --tags: Specify the tags to search for when downloading content.
- --output: Specify the output directory. (default: output/)
- --url: Specify the Danbooru URL to make API calls to. (default: https://danbooru.donmai.us)
- --page_limit: Specify the maximum number of pages to parse through when downloading. (default: 1000)
- --api_key: Specify the API key for Danbooru. This is optional unless you want to link a higher level account to surpass tag search and page limit restrictions. Username must also be provided.
- --username: Specify the username to log on to Danbooru with, to be provided alongside an api_key.
- --max_file_size: Attempt to download the maximum available file size instead of the default size.
- --extensions: Specify the extensions of file types to download, comma-separated. Pass * to download all file types. (default: .png,.jpg)
- --save_tags: Save the tags for each image in a text file with the same name.
- --tags_only: Only save tags for existing images. Do not download any images.
- --write_translation: Write the translation of foreign text in the image to the tag file.
- --year_start: Specify the start year for downloading content. Format: YYYY
- --year_end: Specify the end year for downloading content. Format: YYYY

##### Sample Execution Command

```bash
python downloader_danbooru.py --tags "cat" --output "./downloaded_images" --page_limit 500 --api_key "api_key_here" --username "username_here" --extensions ".png,.jpg" --save_tags --year_start 2020 --year_end 2022
```

### downloader_e621.py

#### Script Overview

**※ There is almost no need to use this script since using gallery-dl is faster.**  
This script is designed to retrieve and save images and their metadata related to a specified tag or search keyword. It utilizes libraries such as requests, urllib, BeautifulSoup, and json.

#### Explanation of Arguments

- Please enter the target tag or search keyword.
- Enter the number of pages to retrieve.
- Enter the name of the directory to save images.

#### Sample Execution Command

```python
python downloader_e621.py
Enter the target tag or search keyword: cat
Enter the number of pages to retrieve: 3
Enter the name of the directory to save images: cat_images
```

### fancaps_episode_downloader.py

#### Script Overview

This script is a tool for crawling and downloading screenshot images from the specified episode URL on the fancaps site. It was improved based on the code from the following repository: [m-patino/fancaps-downloader: Fancaps Downloader](https://github.com/m-patino/fancaps-downloader).

#### Explanation of Arguments

- url: URL to start the download
- --output: Path of the output folder (default is "Downloads")

#### Sample Execution Command

```python
python fancaps_episode_downloader.py "https://fancaps.net/anime/episodeimages.php?21914-hack_Roots/Episode_1" --output "./Downloads"
```

### image_cleaner.py

#### Overview

This script processes image files in a specified directory, detects and organizes duplicate images.

#### Argument List

- `--dir`: Directory to process (required)
- `--save_dir`: Directory to save non-duplicate images (default: `output/`)
- `--save_dir_duplicate`: Directory to save duplicate images
- `--extension`: Extensions of images to process (default: `jpg png webp`)
- `--recursive`: Recursively search directories (optional)
- `--debug`: Debug mode (optional)
- `--threshold`: Hamming distance threshold for duplicates (default: 10)
- `--preserve_own_folder`: Preserve own folder structure (optional)
- `--preserve_structure`: Preserve directory structure (optional)
- `--gc_disable`: Disable garbage collection (optional)
- `--by_folder`: Process folders one by one (optional)
- `--process_group`: Number of images in a processing group (default: 2)
- `--mem_cache`: Enable in-memory caching (default: enabled)

#### Sample Execution Command

```python
python image_cleaner.py --dir "/path/to/images" --save_dir "/path/to/output" --threshold 5 --recursive --preserve_structure
```

#### Threshold Guidelines

The appropriate threshold for determining image similarity using dhash (difference hash) depends on the specific use case and the nature of the images, but generally, you can refer to the following guidelines:

- **For strict matching (detecting identical images)**:
    
    - Threshold: **5 or below**
    - This setting detects nearly identical images (with very slight differences) as duplicates.
- **For general similarity detection**:
    
    - Threshold: **around 10**
    - This range is suitable for detecting almost identical images (including slight changes in color or small modifications). This is often used as the default threshold for many applications.
- **For looser similarity detection**:
    
    - Threshold: **15 or above**
    - This is used when you want to consider even significantly different images as similar. However, this setting increases the possibility of false positives (detecting genuinely different images as duplicates).

### Danbooru Metadata Converter Script: metadata_converter_danbooru.py

#### Overview

This script converts Danbooru metadata files to plain text format. The main libraries used internally are as follows:

- `argparse`: Command line argument parsing
- `json`: JSON file reading and parsing
- `os`: File and directory operations
- `signal`: Signal handling
- `sys`: System-related operations
- `pathlib`: Path operations
- `tqdm`: Progress bar display
- `time`: Time-related operations
- `multiprocessing`: Parallel processing
- `gc`: Garbage collection

#### Argument List

- `--dir`: Directory containing metadata files (required)
- `--save_dir`: Directory to save converted files (required)
- `--metadata_order`: Order of metadata labels to extract. Example: `--metadata_order "title" "artist" "tags"` (required)
- `--insert_custom_text`: Insert custom texts at specified indexes in the output. Example: `--insert_custom_text 2 "CUSTOM_TEXT"` (optional)
- `--debug`: Enable debug mode to display processing logs without making actual changes (optional)
- `--save_extension`: Extension of the output file (default: `txt`) (optional)
- `--mem_cache`: Enable or disable memory caching. Default is `ON` (optional)
- `--threads`: Number of threads to use. Default is the number of CPU cores (optional)
- `--recursive`: Recursively process directories (optional)
- `--preserve_own_folder`: Preserve own folder structure in the save directory (optional)
- `--preserve_structure`: Preserve directory structure in the save directory (optional)
- `--gc_disable`: Disable garbage collection (optional)
- `--by_folder`: Process each folder one by one (optional)

#### Specifications

- The json metadata files in the directory specified by `--dir` are expected to be in the following format. This is basically obtained by downloading with the `--write-metadata` argument of gallery-dl: [json metadata example](https://github.com/WarriorMama777/data-kitchen/blob/main/example/metadata/danbooru_1_d34e4cf0a437a5d65f8e82b7bcd02606.json)

#### Sample Execution Command

```python
python metadata_converter_danbooru.py --metadata_order "tag_string_artist" "tag_string_copyright" "tag_string_character" "tag_string_general" "rating" --dir "/path/to/metadata" --save_dir "/path/to/output" --insert_custom_text 3 "illustration,|||" 4 "|||" --recursive --preserve_own_folder --preserve_structure --gc_disable --by_folder
```

### EXIF Remover Script: exif_remover.py

#### Overview

This script removes EXIF metadata from image files. The main libraries used internally are as follows:

- `cv2`: Image reading and saving

#### Argument List

- `--dir`: Target directory (required)
- `--remove`: Remove EXIF metadata (optional)
- `--save`: Directory to save the images. If not specified, the images will be overwritten (optional)
- `--cpu`: Number of threads to use. If not specified, it will be determined automatically (optional)

#### Sample Execution Command

```bash
python exif_remover.py --dir "/path/to/images" --remove --save "/path/to/output" --cpu 4
```

## Contribution

Contributions are welcome. Please feel free to report bugs, suggest features, or contribute via pull requests.

## License

This project is licensed under the MIT license.

## Author

- GitHub: [WarriorMama777](https://github.com/WarriorMama777)
- huggingface: [WarriorMama777](https://huggingface.co/WarriorMama777)