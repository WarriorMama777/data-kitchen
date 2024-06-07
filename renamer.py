import argparse
import os
import re
from tqdm import tqdm

def rename_files(directory, args, is_recursive=False, level=0):
    try:
        files = os.listdir(directory)
    except FileNotFoundError:
        print(f"指定されたディレクトリが存在しません: {directory}")
        os.makedirs(directory)
        print(f"ディレクトリを作成しました: {directory}")
        return
    except Exception as e:
        print(f"ディレクトリの読み込み中にエラーが発生しました: {e}")
        return

    file_count = len(files)
    num_length = len(str(file_count))

    for i, filename in enumerate(tqdm(files, desc="Processing"), start=1):
        old_path = os.path.join(directory, filename)
        if os.path.isdir(old_path) and not args.folder:
            if is_recursive:
                rename_files(old_path, args, is_recursive=True, level=level + 1)
            continue
        elif not os.path.isdir(old_path) and not args.file:
            continue

        if os.path.isdir(old_path):
            extension = ""
            base_name = filename
        else:
            base_name, extension = os.path.splitext(filename)
        
        new_name = modify_name(i, base_name, num_length, args) + extension

        if new_name != filename:
            new_path = os.path.join(directory, new_name)
            if args.debug:
                print(f"デバッグモード: '{filename}' から '{new_name}' への変更をシミュレートします。")
                continue  # 実際の名前変更をスキップ
            else:
                try:
                    os.rename(old_path, new_path)
                    print(f"'{filename}' を '{new_name}' に変更しました。")
                except Exception as e:
                    print(f"ファイル名の変更中にエラーが発生しました: {e}")

def modify_name(index, base_name, num_length, args):
    new_name = base_name

    if args.del_first:
        new_name = new_name[args.del_first:]

    if args.del_last:
        new_name = new_name[:-args.del_last]

    if args.add_first:
        new_name = args.add_first + new_name

    if args.add_last:
        new_name = new_name + args.add_last

    if args.add_number_first:
        new_name = f"{index:0{num_length}d}_" + new_name

    if args.add_number_last:
        new_name = new_name + f"_{index:0{num_length}d}"

    # --replaceオプションの処理を修正
    if args.replace:
        old_patterns = args.replace[:-1]
        new_str = args.replace[-1]
        for old_pattern in old_patterns:
            pattern = re.compile(re.escape(old_pattern))
            new_name = pattern.sub(new_str, new_name)

    if args.del_after:
        pos = new_name.find(args.del_after)
        if pos != -1:
            new_name = new_name[:pos + len(args.del_after)]

    if args.del_before:
        pos = new_name.find(args.del_before)
        if pos != -1:
            new_name = new_name[pos:]

    if args.add_after:
        search_str, add_str = args.add_after.split(",")
        pos = new_name.find(search_str)
        if pos != -1:
            new_name = new_name[:pos + len(search_str)] + add_str + new_name[pos + len(search_str):]

    if args.add_before:
        search_str, add_str = args.add_before.split(",")
        pos = new_name.find(search_str)
        if pos != -1:
            new_name = new_name[:pos] + add_str + new_name[pos:]

    if args.reg_del:
        pattern = re.compile(args.reg_del)
        new_name = pattern.sub('', new_name)

    if args.reg_del_around:
        pattern = re.compile(args.reg_del_around)
        match = pattern.search(new_name)
        if match:
            new_name = new_name[match.start():match.end()]
        else:
            new_name = base_name  # 修正: マッチしなかった場合の処理を明確化

    return new_name

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ファイル名を一括で変更するスクリプト")
    parser.add_argument("--dir", type=str, help="対象ディレクトリ")
    parser.add_argument("--recursive", action="store_true", help="再帰的に処理を行う")
    parser.add_argument("--folder", action="store_true", help="フォルダを対象に含める")
    parser.add_argument("--file", action="store_true", help="ファイルを対象に含める")
    parser.add_argument("--del_first", type=int, help="先頭から削除する文字数")
    parser.add_argument("--del_last", type=int, help="末尾から削除する文字数")
    parser.add_argument("--add_first", type=str, help="先頭に追加する文字列")
    parser.add_argument("--add_last", type=str, help="末尾に追加する文字列")
    parser.add_argument("--add_number_first", action="store_true", help="先頭に番号を追加する")
    parser.add_argument("--add_number_last", action="store_true", help="末尾に番号を追加する")
    parser.add_argument("--replace", nargs='+', help="指定文字列を置換 (最後に定義された文字列を置換先として扱う) 例：--replace \"置換元A\" \"置換元B\" \"置換先\"")
    parser.add_argument("--del_after", type=str, help="指定文字列の後を削除")
    parser.add_argument("--del_before", type=str, help="指定文字列の前を削除")
    parser.add_argument("--add_after", type=str, help="指定文字列の後に追加 (カンマで区切る)")
    parser.add_argument("--add_before", type=str, help="指定文字列の前に追加 (カンマで区切る)")
    parser.add_argument("--reg_del", type=str, help="正規表現で一致した部分を削除")
    parser.add_argument("--reg_del_around", type=str, help="正規表現で一致した部分を残し、それ以外を削除")
    parser.add_argument("--debug", action="store_true", help="デバッグモード")

    args = parser.parse_args()

    if args.recursive:
        rename_files(args.dir, args, is_recursive=True)
    else:
        rename_files(args.dir, args)
