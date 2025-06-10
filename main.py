import os.path

import vk_api
from data import USER_TOKEN, GROUP_ID
from data import MY_USER_TOKEN, MY_ID
import schedule
from time import sleep
import logging
from datetime import date
import requests

CONGRATULATIONS_AMOUNT = 32
PHOTOS_AMOUNT = 41

session = vk_api.VkApi(token=USER_TOKEN)
vk = session.get_api()


def post_congratulation():
    newborns = get_newborns()
    if not newborns:
        logging.info("Люди, рожденные в этот день, не найдены")
        return

    logging.info(''.join([f'\n{x["first_name"]} {x["last_name"]} id{x["id"]}' for x in newborns]))
    congratulation_path, photo_path, congrat_no, photo_no = get_congratulation_and_photo_paths()
    logging.info(f'(congrat, photo) - ({congrat_no}, {photo_no})')
    congratulation, attachment = None, None
    for _ in range(10):
        try:
            congratulation, attachment = get_text_and_attachment(congratulation_path, photo_path)
            break
        except:
            if _ == 9:
                requests.get(f'https://api.vk.com/method/messages.send?user_id={MY_ID}&message=Не получилось выгрузить фотку на сервер, программу завершаю ((&random_id=0&access_token={MY_USER_TOKEN}&v=5.131')
                exit(0)
            logging.info('Не получилось выгрузить фотку на сервер вк, ждем 30 секунд и пробуем еще...')
            sleep(30)
    newborn_links = ', '.join([f'[id{x["id"]}|{x["first_name"]} {x["last_name"]}]' for x in newborns if x['first_name'] != 'DELETED'])
    message = f'🎉🎉🎉 Поздравляем с Днём рождения наших сегодняшних именинников:\n\n{newborn_links}\n\n{congratulation}'
    message += f'\nВаш ГАЛОМЕД 💎\n\n{get_static_text()}'

    result = None
    for _ in range(10):
        try:
            result = vk.wall.post(owner_id=-GROUP_ID, message=message, attachments=attachment, from_group=1)
            break
        except:
            if _ == 9:
                requests.get(f'https://api.vk.com/method/messages.send?user_id={MY_ID}&message=Не получилось опубликовать пост, программу завершаю ((&random_id=0&access_token={MY_USER_TOKEN}&v=5.131')
                exit(0)
            logging.info('Не получилось опубликовать пост, ждем 30 секунд и пробуем еще...')
            sleep(30)
    logging.info(f'Пост успешно опубликован! - https://vk.com/wall-{GROUP_ID}_{result["post_id"]}\n')


def get_newborns():
    offset = 0
    group_members = []
    while True:
        result = vk.groups.getMembers(group_id=GROUP_ID, fields=['bdate'], offset=offset)
        group_members.extend(result['items'])
        offset += 1000
        if result['count'] <= offset:
            break
    group_members = list(filter(lambda x: 'bdate' in x and birthday_is_today(x['bdate']), group_members))
    return group_members


def get_text_and_attachment(message_path: str, photo_path: str):
    with open(message_path, encoding="utf-8") as file:
        message = file.read()
    upload_url = vk.photos.getWallUploadServer(peer_id=GROUP_ID)['upload_url']
    to_save = requests.post(upload_url, files={'photo': open(photo_path, "rb")}).json()
    pic = vk.photos.saveWallPhoto(photo=to_save['photo'], server=to_save['server'], hash=to_save['hash'])[0]
    return message, f'photo{pic["owner_id"]}_{pic["id"]}_{pic["access_key"]}'


def get_congratulation_and_photo_paths():
    congratulations_no_path = 'congratulations/no.txt'
    photos_no_path = 'photos/no.txt'
    if not os.path.exists(congratulations_no_path):
        with open(congratulations_no_path, 'w') as file:
            file.write('1')
    if not os.path.exists(photos_no_path):
        with open(photos_no_path, 'w') as file:
            file.write('1')
    with open(congratulations_no_path) as file:
        prev_congratulation_no = int(file.read())
    with open(photos_no_path) as file:
        prev_photo_no = int(file.read())
    congratulation_path = f'congratulations/congratulation{prev_congratulation_no}.txt'
    photo_path = f'photos/ДР{prev_photo_no}.jpg'
    congratulation_no = prev_congratulation_no + 1
    if congratulation_no > CONGRATULATIONS_AMOUNT:
        congratulation_no = 1
    photo_no = prev_photo_no + 1
    if photo_no > PHOTOS_AMOUNT:
        photo_no = 1
    with open(congratulations_no_path, 'w') as file:
        file.write(str(congratulation_no))
    with open(photos_no_path, 'w') as file:
        file.write(str(photo_no))
    return congratulation_path, photo_path, prev_congratulation_no, prev_photo_no


def get_static_text():
    with open("static_text.txt", encoding="utf-8") as file:
        static_text = file.read()
    return static_text


def birthday_is_today(bdate: str) -> bool:
    if bdate.count('.') == 2:
        bdate = bdate[:bdate.rfind('.')]
    bdate_month = int(bdate[bdate.find('.') + 1:])
    bdate_day = int(bdate[:bdate.find('.')])
    today = date.today()
    if today.month == bdate_month and today.day == bdate_day:
        return True
    return False


def start_schedule():
    schedule.every().day.at("10:00", "Europe/Moscow").do(post_congratulation)
    while True:
        schedule.run_pending()
        sleep(60)


if __name__ == '__main__':
    print('Script is running...')
    logging.basicConfig(
        format="%(asctime)s - %(message)s",
        filename='info.log',
        filemode='w',
        level=logging.INFO
    )
    start_schedule()