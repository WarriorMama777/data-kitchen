import argparse
import subprocess
import sys

def execute_task(task_file):
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

        print(f"{index}番目のタスクを実行中: {task}")
        try:
            # subprocess.runを使用してPythonコードを実行
            result = subprocess.run(['python', '-c', task], check=True, text=True, capture_output=True)
            print(f"実行結果:\n{result.stdout}")
        except subprocess.CalledProcessError as e:
            print(f"エラー: タスクの実行中にエラーが発生しました - {e.stderr}")
        except Exception as e:
            print(f"エラー: 予期せぬエラーが発生しました - {e}")
        finally:
            print(f"{index}番目のタスクの実行が完了しました\n")

def main():
    parser = argparse.ArgumentParser(description="指定されたテキストファイルに記載されたタスクを実行するスクリプト")
    parser.add_argument('task_file', type=str, help="実行するタスクが記載されたテキストファイルのパス")
    
    args = parser.parse_args()
    execute_task(args.task_file)

if __name__ == '__main__':
    main()
