import os
import sys
import psutil

def kill_processes_using_path(path):
    """
    指定されたパスを使用しているプロセスを終了する
    """
    for proc in psutil.process_iter(['pid', 'name', 'open_files']):
        try:
            open_files = proc.info['open_files']
            if open_files:
                for file in open_files:
                    if file.path.startswith(path):
                        print(f"Killing process {proc.info['name']} (PID: {proc.info['pid']}) using {file.path}")
                        proc.terminate()
                        proc.wait()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python util\\task_kill.py <path>")
        sys.exit(1)

    path = sys.argv[1]

    if not os.path.exists(path):
        print(f"Path {path} does not exist.")
        sys.exit(1)

    kill_processes_using_path(path)
