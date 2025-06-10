import os
import sys
import traceback

from fabric import Connection, Result
from colorama import init as colorama_init
import humanize

from data import HOST, USER, PRIVATE_KEY_PATH

LOGS_FOLDER = 'logs'
SERVER_WD = '/home/tim/Vk-Happy-Birthday'
SUBFOLDER_INDENT = ' ' * 4


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    ENDC = '\033[0m'
    PURPLE = '\033[35m'
    DARKGRAY = '\033[90m'


class SFTPConnection:
    def __init__(self):
        self.conn = Connection(host=HOST, user=USER, connect_kwargs={'key_filename': PRIVATE_KEY_PATH})

    def folder_exists(self, folder_path: str) -> bool:
        result: Result = self.conn.run(f'test -d "{folder_path}"', hide=True, warn=True)
        return result.ok

    is_folder: callable = folder_exists

    def get_folder_items(self, remote_path: str):
        result: Result = self.conn.run(f'find "{remote_path}" -maxdepth 1 -print', hide=True, encoding='utf-8')
        if not result:
            raise Exception(f'Failed to get folder objects: {remote_path}. Error: {result.stderr}')
        files_and_dirs = result.stdout.strip().split('\n')
        return sorted([item for item in files_and_dirs if item and item != remote_path])

    def get(self, remote_path: str, local_path: str) -> None:
        result: Result = self.conn.get(remote_path, local_path)
        if not result:
            raise Exception(f'Failed to download file: {remote_path}. Error: {result.stderr}')

    def close(self):
        self.conn.close()


def download_logs_recursively(sftp, remote_path, local_path, indent=''):
    global total_size, total_files
    os.makedirs(local_path, exist_ok=True)

    items: list[str] = sftp.get_folder_items(remote_path)
    for item in items:
        local_item_path = os.path.join(local_path, os.path.basename(item))
        item_last_name = os.path.basename(item)

        if sftp.is_folder(item):
            print(f'{indent}{Colors.UNDERLINE}{item_last_name}{Colors.ENDC}')
            download_logs_recursively(sftp, item, local_item_path, indent + SUBFOLDER_INDENT)
        else:  # Это файл
            print(f'{indent}{Colors.BOLD}- {item_last_name}... {Colors.ENDC}', end='')
            try:
                sftp.get(item, local_item_path)
                total_size += os.path.getsize(local_item_path)
                total_files += 1
                file_size = humanize.naturalsize(os.path.getsize(local_item_path))
                print(f'{Colors.GREEN}downloaded  {Colors.PURPLE}({file_size}){Colors.ENDC}')
            except Exception as e:
                print(f'{Colors.RED}failed ({e}){Colors.ENDC}')


def carefully_delete_local_logs(folder=LOGS_FOLDER, feature_name=None):
    folder = folder if not feature_name else os.path.join(LOGS_FOLDER, feature_name)
    for item in os.listdir(folder):
        if os.path.isdir(os.path.join(folder, item)):
            carefully_delete_local_logs(os.path.join(folder, item))
        else:
            if not item.startswith('manual_collecting_'):
                os.remove(os.path.join(folder, item))


if __name__ == '__main__':
    SERVER_WD = SERVER_WD.rstrip('/')
    colorama_init()
    args = sys.argv
    total_size = 0.0
    total_files = 0
    sftp = SFTPConnection()
    print('Connection succesfully established ...')
    try:
        if len(args) > 1:
            match args[1]:
                case 'main':
                    sftp.get(f'{SERVER_WD}/main.log', 'main.log')
                    print('*** Файл на базе! ***')
                case _:
                    feature_logs_folder = f'{LOGS_FOLDER}/{args[1]}'
                    if not sftp.folder_exists(f'{SERVER_WD}/{feature_logs_folder}'):
                        print(f'Папки "{feature_logs_folder}" нет в проекте на сервере.')
                        exit(0)
                    if os.path.exists(LOGS_FOLDER):
                        carefully_delete_local_logs(feature_name=args[1])
                    download_logs_recursively(sftp, f'{SERVER_WD}/{feature_logs_folder}', feature_logs_folder)
                    print('\n*** Файлы на базе! ***\n')
        else:
            files = ['info.log', 'congratulations/no.txt', 'photos/no.txt']
            for file in files:
                print(f'{Colors.BOLD}- {file}... {Colors.ENDC}', end='')
                try:
                    sftp.get(f'{SERVER_WD}/{file}', file)
                    total_size += os.path.getsize(file)
                    total_files += 1
                    file_size = humanize.naturalsize(os.path.getsize(file))
                    print(f'{Colors.GREEN}downloaded  {Colors.PURPLE}({file_size}){Colors.ENDC}')
                except Exception as e:
                    print(f'{Colors.RED}failed ({e}){Colors.ENDC}')

            print('\n*** Файлы на базе! ***\n')

            print(f'Всего логов скачано: {total_files}')
            print(f'Общий размер: {humanize.naturalsize(total_size)}\n')

    except Exception as e:
        print(f'{e}\n{traceback.format_exc()}')
    finally:
        sftp.close()
