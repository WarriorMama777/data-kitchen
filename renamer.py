import argparse
import os

def rename_files(args):
    directory = args.dir
    if not os.path.isdir(directory):
        print(f"指定されたディレクトリが存在しません: {directory}")
        return

    files = os.listdir(directory)
    file_count = len(files)
    num_length = len(str(file_count))

    for i, filename in enumerate(files, start=1):
        new_name = filename

        if args.del_first:
            new_name = new_name[args.del_first:]

        if args.del_last:
            new_name = new_name[:-args.del_last]

        if args.add_first:
            new_name = args.add_first + new_name

        if args.add_last:
            new_name = new_name + args.add_last

        if args.add_number_first:
            new_name = f"{i:0{num_length}d}_" + new_name

        if args.add_number_last:
            new_name = new_name + f"_{i:0{num_length}d}"

        if args.replace:
            old, new = args.replace.split("->")
            new_name = new_name.replace(old, new)

        # 指定した文字以降を削除
        if args.del_after:
            pos = new_name.find(args.del_after)
            if pos != -1:
                new_name = new_name[:pos + len(args.del_after)]

        # 指定した文字以前を削除
        if args.del_before:
            pos = new_name.find(args.del_before)
            if pos != -1:
                new_name = new_name[pos:]

        # 指定した文字の後ろに文字を追加
        if args.add_after:
            search_str, add_str = args.add_after.split(",")
            pos = new_name.find(search_str)
            if pos != -1:
                new_name = new_name[:pos + len(search_str)] + add_str + new_name[pos + len(search_str):]

        # 指定した文字の前に文字を追加
        if args.add_before:
            search_str, add_str = args.add_before.split(",")
            pos = new_name.find(search_str)
            if pos != -1:
                new_name = new_name[:pos] + add_str + new_name[pos:]

        if new_name != filename:
            old_path = os.path.join(directory, filename)
            new_path = os.path.join(directory, new_name)
            try:
                os.rename(old_path, new_path)
            except Exception as e:
                print(f"ファイル名の変更中にエラーが発生しました: {e}")
            else:
                print(f"'{filename}' を '{new_name}' に変更しました。")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ファイル名を変更するスクリプト")
    parser.add_argument("--dir", type=str, required=True, help="作業対象のディレクトリ")
    parser.add_argument("--del_first", type=int, help="先頭の文字を指定された数だけ削除")
    parser.add_argument("--del_last", type=int, help="末尾の文字を指定された数だけ削除")
    parser.add_argument("--add_first", type=str, help="先頭に文字を追加")
    parser.add_argument("--add_last", type=str, help="末尾に文字を追加")
    parser.add_argument("--add_number_first", action='store_true', help="先頭に連番を追加")
    parser.add_argument("--add_number_last", action='store_true', help="末尾に連番を追加")
    parser.add_argument("--replace", type=str, help="文字を置換する(例: 'neko->piyo')")
    parser.add_argument("--del_after", type=str, help="指定した文字以降を削除")
    parser.add_argument("--del_before", type=str, help="指定した文字以前を削除")
    parser.add_argument("--add_after", type=str, help="指定した文字の後ろに文字を追加 (形式: '検索文字列,追加文字列')")
    parser.add_argument("--add_before", type=str, help="指定した文字の前に文字を追加 (形式: '検索文字列,追加文字列')")


    args = parser.parse_args()

    rename_files(args)
