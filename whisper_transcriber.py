import argparse
import os
import whisper
from datetime import datetime

def transcribe_audio(file_path, model_name, prompt, output_format, save_dir):
    # モデルのロード
    model = whisper.load_model(model_name)

    # 書き起こしの実行
    result = model.transcribe(file_path)

    # ファイル名と拡張子の取得
    filename, file_extension = os.path.splitext(os.path.basename(file_path))

    # 書き起こしテキストの取得
    transcription = result['text']

    # 出力ファイル名の形式に従ってファイル名を生成
    if output_format == '<filename>':
        output_filename = filename
    elif output_format == '<extension>':
        output_filename = file_extension.replace('.', '')
    elif output_format == 'nekoneko_v1':
        output_filename = 'nekoneko_v1'
    elif output_format == '<date>_<time>':
        output_filename = datetime.now().strftime('%Y%m%d_%H%M%S')
    elif output_format == '<transcription>':
        output_filename = transcription[:10]  # 先頭10文字を使用
    else:
        output_filename = 'transcription'

    # 保存先のパスを生成
    save_path = os.path.join(save_dir, f"{output_filename}.txt")

    # 書き起こしテキストの保存
    with open(save_path, 'w') as f:
        f.write(transcription)

    print(f"File saved to {save_path}")

def main():
    parser = argparse.ArgumentParser(description="Transcribe audio files using OpenAI's Whisper model.")
    parser.add_argument('--dir', type=str, required=True, help='Directory containing audio or video files to transcribe.')
    parser.add_argument('--save', type=str, required=True, help='Directory to save the transcriptions.')
    parser.add_argument('--format', type=str, default='<filename>', help='Format for the transcription file name.')
    parser.add_argument('--model', type=str, default='base', choices=['tiny', 'base', 'small', 'medium', 'large', 'large-v2, `large-v3`'], help='Whisper model to use for transcription.')
    parser.add_argument('--prompt', type=str, default='', help='Prompt for guiding the transcription.')

    args = parser.parse_args()

    # 指定されたディレクトリのファイルを処理
    for file in os.listdir(args.dir):
        file_path = os.path.join(args.dir, file)
        # サポートされている拡張子を持つファイルのみ処理
        if file_path.endswith(('.mp3', '.wav', '.mp4', '.avi')):
            print(f"Transcribing {file}...")
            transcribe_audio(file_path, args.model, args.prompt, args.format, args.save)

if __name__ == '__main__':
    main()
