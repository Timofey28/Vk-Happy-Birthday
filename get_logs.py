import pysftp
from data import my_Hostname, my_Username, my_Password

try:
    with pysftp.Connection(host=my_Hostname, username=my_Username, password=my_Password) as sftp:
        print("Connection succesfully established ... ")
        sftp.get('/root/Vk-Happy-Birthday/info.log', 'info.log')
        sftp.get('/root/Vk-Happy-Birthday/congratulations/no.txt', 'no_congratulation.txt')
        sftp.get('/root/Vk-Happy-Birthday/photos/no.txt', 'no_photos.txt')
    print("*** Файлы на базе! ***")
except Exception as e:
    print(str(e))