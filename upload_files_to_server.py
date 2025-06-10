import os
import warnings
from dataclasses import dataclass

from fabric import Connection, Result
from colorama import init as colorama_init

from data import HOST, USER, PRIVATE_KEY_PATH


files_to_upload = [
    # Папки
    'congratulations',
    'photos',

    # Файлы
    'main.py',
    'data.py',
    'static_text.txt',
    'requirements.txt',
]

files_to_ignore = [
    '__pycache__',
]

# Файлы на сервере, которые не удаляются при загрузке остальных данных туда (без путей, чисто названия)
protected_server_files = [

]


class Colors:
    PINK = '\033[95m'
    BLUE = '\033[94m'
    PURPLE = '\033[35m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    ORANGE = '\033[33m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    LIGHTGRAY = '\033[37m'
    DARKGRAY = '\033[90m'
    ENDC = '\033[0m'


class SFTPConnection:
    def __init__(self):
        self.conn = Connection(host=HOST, user=USER, connect_kwargs={'key_filename': PRIVATE_KEY_PATH})

    def folder_exists(self, folder_path: str) -> bool:
        result: Result = self.conn.run(f'test -d "{folder_path}"', hide=True, warn=True)
        return result.ok

    def execute(self, command: str) -> None:
        result: Result = self.conn.run(command, hide=True)
        if not result:
            raise Exception(f'Command execution failed: {command}. Error: {result.stderr}')

    def mkdir(self, folder_path: str, mode: int) -> None:
        result: Result = self.conn.run(f'mkdir -pm {mode} "{folder_path}"')
        if not result:
            raise Exception(f'Failed to create directory: {folder_path}. Error: {result.stderr}')

    def chmod(self, file_path: str, mode: int) -> None:
        result: Result = self.conn.run(f'chmod {mode} "{file_path}"')
        if not result:
            raise Exception(f'Failed to change permissions for file: {file_path}. Error: {result.stderr}')

    def put(self, local_path: str, remote_path: str) -> None:
        result: Result = self.conn.put(local_path, remote_path)
        if not result:
            raise Exception(f'Failed to upload file: {local_path}. Error: {result.stderr}')

    def close(self):
        self.conn.close()


@dataclass
class Folder:
    folder_name: str
    files: list[str]
                
                
class FileUploader:
    def __init__(self, files: list[str]):
        self.server_wd = '/home/tim/Vk-Happy-Birthday'

        self.files = []
        self.sftp = None
        self.subfolder_indent = ' ' * 4
        self.server_wd = self.server_wd.rstrip('/') + '/'
        colorama_init()
        for file in files:
            if os.path.isdir(file):
                self.files.append(Folder(folder_name=file, files=self.__read_files_from_folder(file)))
            elif os.path.isfile(file):
                self.files.append(file)
            else:
                print(f'Файл {file} не найден')
                exit(0)

    def upload_files_to_server(self) -> None:
        warnings.filterwarnings('ignore')
        self.sftp = SFTPConnection()
        if not self.sftp.folder_exists(self.server_wd):
            print(f'На сервере нет папки {self.server_wd[:-1]}')
            self.sftp.close()
            exit(0)
        files_uploaded = [0]
        self.__upload_folder_files(self.files, files_uploaded)
        self.sftp.close()
        total_files = self.files_amount
        if files_uploaded[0] == total_files:
            print(f'\nВсе файлы ({total_files}) были успешно загружены на сервер!\n')
        else:
            print(f'\nЗагружено файлов: {files_uploaded[0]} из {total_files}\n')

    def __upload_folder_files(self, files: list[str | Folder], files_uploaded: list[int], indent=''):
        for file in files:
            if isinstance(file, Folder):
                print(f'{indent}{Colors.UNDERLINE}{file.folder_name[file.folder_name.rfind("/") + 1:]}{Colors.ENDC}')
                if self.sftp.folder_exists(f'{self.server_wd}{file.folder_name}'):
                    self.sftp.execute(self.__generate_removing_command(f'{self.server_wd}{file.folder_name}'))
                    self.sftp.execute(f'find {self.server_wd}{file.folder_name} -type d -empty -delete')
                if not self.sftp.folder_exists(f'{self.server_wd}{file.folder_name}'):
                    self.sftp.mkdir(f'{self.server_wd}{file.folder_name}', mode=744)
                self.__upload_folder_files(file.files, files_uploaded, f'{indent}{self.subfolder_indent}')
            else:
                print(f'{indent}{Colors.BOLD}- {file[file.rfind("/") + 1:] if file.find("/") != -1 else file}... {Colors.ENDC}', end='')
                try:
                    self.sftp.put(file, f'{self.server_wd}{file}')
                    if 'chromedriver' in file:
                        self.sftp.chmod(f'{self.server_wd}{file}', 744)
                    files_uploaded[0] += 1
                    print(f'{Colors.GREEN}uploaded{Colors.ENDC}')
                except Exception as e:
                    print(f'{Colors.RED}failed ({e}){Colors.ENDC}')

    @staticmethod
    def __generate_removing_command(path: str) -> str:
        if protected_server_files:
            exclude_patterns = ' -o '.join([f'-name "{file}"' for file in protected_server_files])
            command = f'find {path} -type f ! \\( {exclude_patterns} \\) -delete'
        else:
            command = f'find {path} -type f -delete'
        return command

    def __read_files_from_folder(self, folder_name: str) -> list[str]:
        current_folder_files = []
        for file in os.listdir(folder_name):
            if file in files_to_ignore:
                continue
            new_file_name = f'{folder_name}/{file}'
            if os.path.isdir(new_file_name):
                current_folder_files.append(Folder(folder_name=new_file_name, files=list(self.__read_files_from_folder(new_file_name))))
            else:
                current_folder_files.append(new_file_name)
        return current_folder_files.copy()

    @property
    def files_amount(self):
        ans = [0]
        self.__count_files(ans)
        return ans[0]

    def __count_files(self, amount: list[int], files: list[str | Folder] = None) -> None:
        if files is None:
            files = self.files
        amount[0] += len([file for file in files if type(file) is str])
        for folder in [file for file in files if isinstance(file, Folder)]:
            self.__count_files(amount, folder.files)

    def debug_print_files(self, files: list[str | Folder] = None, indent='') -> None:
        if files is None:
            files = self.files
        for file in files:
            if isinstance(file, Folder):
                print(f'{indent}{file.folder_name}')
                self.debug_print_files(file.files, f'{indent}\t')
            else:
                print(f'{indent}- {file}')


file_uploader = FileUploader(files_to_upload)
file_uploader.upload_files_to_server()
