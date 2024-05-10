import argparse
import subprocess
import sys
import shutil  # shutil.whichを使用するために追加

def execute_task(task_file, debug=False):
    try:
        with open(task_file, 'r', encoding='utf-8') as file:
            tasks = file.readlines()
    except FileNotFoundError:
        print(f"エラー: 指定されたファイルが見つかりません - {task_file}")
        sys.exit(1)
    except Exception as e:
        print(f"エラー: ファイルの読み込み中に問題が発生しました - {e}")
        sys.exit(1)

    for index, task in enumerate(tasks, start=1):
        task = task.strip()
        if not task:
            continue

        if debug:
            # コマンドがシステム上に存在するかどうかを確認
            command = task.split()[0]  # コマンド名を取得
            if shutil.which(command):
                print(f"{index}番目のタスク '{task}' はシステム上に存在します。")
            else:
                print(f"{index}番目のタスク '{task}' はシステム上に存在しません。")
        else:
            print(f"{index}番目のタスクを実行中: {task}")
            try:
                # シェルコマンドを実行
                result = subprocess.run(task, shell=True, check=True, text=True, capture_output=True)
                print(f"実行結果:\n{result.stdout}")
            except subprocess.CalledProcessError as e:
                print(f"エラー: タスクの実行中にエラーが発生しました - {e.stderr}")
            except Exception as e:
                print(f"エラー: 予期せぬエラーが発生しました - {e}")
                
def main():
    parser = argparse.ArgumentParser(description="指定されたテキストファイルに記載されたタスクを実行するスクリプト")
    parser.add_argument('task_file', type=str, help="実行するタスクが記載されたテキストファイルのパス")
    parser.add_argument('--debug', action='store_true', help="デバッグモードを有効にする")
    
    args = parser.parse_args()
    execute_task(args.task_file, debug=args.debug)

if __name__ == '__main__':
    main()
