import vk_api
from data import USER_TOKEN, GROUP_ID
# from data import MY_USER_TOKEN as USER_TOKEN, MY_GROUP_ID as GROUP_ID
import schedule
from time import sleep
import logging
from datetime import date
import requests

CONGRATULATIONS_AMOUNT = 32
PHOTOS_AMOUNT = 43

session = vk_api.VkApi(token=USER_TOKEN)
vk = session.get_api()


def post_congratulation():
    newborns = get_newborns()
    if not newborns:
        logging.info("Люди, рожденные в этот день, не найдены")
        return

    logging.info('\n'.join([f'{x["first_name"]} {x["last_name"]} id{x["id"]}' for x in newborns]))
    congratulation_text, attachment = get_text_and_attachment()
    newborn_links = ', '.join([f'[id{x["id"]}|{x["first_name"]} {x["last_name"]}]' for x in newborns])
    message = f'🎉🎉🎉 Поздравляем с Днём рождения наших сегодняшних именинников:\n\n{newborn_links}\n\n{congratulation_text}'
    message += f'\nВаш ГАЛОМЕД 💎\n\n{get_static_text()}'

    result = vk.wall.post(owner_id=-GROUP_ID, message=message, attachments=attachment, from_group=1)
    logging.info(f'Пост успешно опубликован! - https://vk.com/club{GROUP_ID}?w=wall-{GROUP_ID}_{result["post_id"]}')


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


def get_text_and_attachment():
    message_path, photo_path = get_congratulation_and_photo_paths()
    with open(message_path, encoding="utf-8") as file:
        message = file.read()
    upload_url = vk.photos.getWallUploadServer(peer_id=GROUP_ID)['upload_url']
    to_save = requests.post(upload_url, files={'photo': open(photo_path, "rb")}).json()
    pic = vk.photos.saveWallPhoto(photo=to_save['photo'], server=to_save['server'], hash=to_save['hash'])[0]
    return message, f'photo{pic["owner_id"]}_{pic["id"]}_{pic["access_key"]}'


def get_congratulation_and_photo_paths():
    with open(f'congratulations/no.txt') as file:
        congratulation_no = int(file.read())
    with open(f'photos/no.txt') as file:
        photo_no = int(file.read())
    congratulation_path = f'congratulations/congratulation{congratulation_no}.txt'
    photo_path = f'photos/ДР{photo_no}.jpg'
    congratulation_no += 1
    if congratulation_no > CONGRATULATIONS_AMOUNT:
        congratulation_no = 1
    photo_no += 1
    if photo_no > PHOTOS_AMOUNT:
        photo_no = 1
    with open(f'congratulations/no.txt', 'w') as file:
        file.write(str(congratulation_no))
    with open(f'photos/no.txt', 'w') as file:
        file.write(str(photo_no))
    return congratulation_path, photo_path


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
        level=logging.INFO
    )
    start_schedule()