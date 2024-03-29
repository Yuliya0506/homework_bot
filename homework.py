import sys
import time
import logging
from http import HTTPStatus

import requests
import telegram
from telegram.error import TelegramError

from exceptions import GetApiUnavailable, SendMessageFail
from config import (
    ENDPOINT, HEADERS, HOMEWORK_STATUSES, PRACTICUM_TOKEN, RETRY_TIME,
    TELEGRAM_CHAT_ID, TELEGRAM_TOKEN,
)


def send_message(bot, message):
    """Отправляем сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info('Сообщение успешно отправлено')
    except TelegramError as error:
        logging.error('Cбой при отправке сообщения')
        raise SendMessageFail(error)


def get_api_answer(current_timestamp):
    """Делаем запрос к API для получения данных сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    homework_statuses = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if homework_statuses.status_code != HTTPStatus.OK:
        logging.error('Сбой при запросе к API')
        raise GetApiUnavailable('Сбой при запросе к API')
    return homework_statuses.json()


def check_response(response):
    """Проверяем ответ API на корректность."""
    if not isinstance(response, dict):
        message = 'Получен некорректный тип данных в ответе API.'
        logging.error(message)
        raise TypeError(message)
    if not isinstance(response['homeworks'], list):
        message = 'В ответе сервиса API список домашних работ пуст.'
        logging.error(message)
        raise TypeError(message)
    homeworks_list = response['homeworks']
    return homeworks_list


# c ValueError тоже не проходят тесты
def parse_status(homework):
    """Получаем статус домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status is None:
        logging.debug('Ошибка homework_status')
        raise KeyError('Отсутствие в ответе новых статусов')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if verdict is None:
        logging.error('Недокументированный статус домашней работы')
        raise KeyError('Недокументированный статус домашней работы')
    logging.info('Статус домашней работы возвращен корректно')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяем доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        logging.critical('Отсутствует обязательная переменная окружения')
        sys.exit('Программа принудительно остановлена')
    else:
        logging.info('Проверка доступности переменных'
                     'окружения пройдена успешно')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot, message)
            current_timestamp = response.get('current_date', current_timestamp)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(error)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s',
        handlers=[logging.StreamHandler(stream=sys.stdout)],
    )
    try:
        main()
    except KeyboardInterrupt:
        logging.info('Программа была прервана пользователем')
