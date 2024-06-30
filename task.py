import argparse
import subprocess
import sys
import shutil

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

    internal_commands = [
        'assoc', 'attrib', 'break', 'cacls', 'cd', 'chcp', 'chdir', 'chkdsk', 'chkntfs', 'cls', 
        'cmd', 'color', 'comp', 'compact', 'convert', 'copy', 'date', 'del', 'dir', 'diskcomp', 
        'diskcopy', 'doskey', 'echo', 'endlocal', 'erase', 'exit', 'fc', 'find', 'findstr', 
        'for', 'format', 'ftype', 'goto', 'graftabl', 'help', 'if', 'label', 'md', 'mkdir', 
        'mode', 'more', 'move', 'path', 'pause', 'popd', 'print', 'prompt', 'pushd', 'rd', 
        'rem', 'ren', 'rename', 'replace', 'rmdir', 'set', 'setlocal', 'shift', 'sort', 
        'start', 'subst', 'time', 'title', 'tree', 'type', 'ver', 'verify', 'vol', 'xcopy'
    ]

    for index, task in enumerate(tasks, start=1):
        task = task.strip()
        if not task:
            continue

        if debug:
            # コマンドの最初の部分を取得
            command = task.split()[0]
            # Windowsの内部コマンドかどうかを確認
            if command in internal_commands or shutil.which(command) is not None:
                print(f"{index}番目のタスク '{task}' はシステム上に存在します。")
            else:
                print(f"{index}番目のタスク '{task}' はシステム上に存在しません。")
        else:
            print(f"{index}番目のタスクを実行中: {task}")
            try:
                subprocess.run(task, shell=True, check=True, text=True)
            except subprocess.CalledProcessError as e:
                print(f"エラー: タスクの実行中にエラーが発生しました - コマンド '{e.cmd}'、終了コード {e.returncode}")
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
