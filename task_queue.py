import argparse
import shlex
import subprocess
import sys
import shutil  # shutilをインポート

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

    executable_tasks = []
    not_executable_tasks = []

    for index, task in enumerate(tasks, start=1):
        task = task.strip()
        if not task:
            continue

        cmd_list = shlex.split(task)  # コマンドラインをリストに分割

        if debug:  # デバッグモード時の追加情報
            print(f"デバッグ: {index}番目のタスク '{task}' を処理しています。コマンドリスト: {cmd_list}")
        
        # 実行ファイルがシステムのパス上に存在するかどうかをチェック
        if shutil.which(cmd_list[0]) is None:
            print(f"{index}番目のタスク '{task}' は実行不可能です: コマンド '{cmd_list[0]}' が見つかりません")
            not_executable_tasks.append(task)
        else:
            print(f"{index}番目のタスク '{task}' は実行可能です")
            executable_tasks.append(task)

        print(f"{index}番目のタスクのチェックが完了しました\n")

    # デバッグ情報の最終結果を表示
    if debug:
        print("デバッグ情報の最終結果:")
        print("実行可能なタスク:")
        for task in executable_tasks:
            print(f" - {task}")
        print("実行不可能なタスク:")
        for task in not_executable_tasks:
            print(f" - {task}")

def main():
    parser = argparse.ArgumentParser(description="指定されたテキストファイルに記載されたタスクをチェックするスクリプト")
    parser.add_argument('task_file', type=str, help="チェックするタスクが記載されたテキストファイルのパス")
    parser.add_argument('--debug', action='store_true', help="デバッグ情報を表示する")
    
    args = parser.parse_args()
    execute_task(args.task_file, args.debug)

if __name__ == '__main__':
    main()
