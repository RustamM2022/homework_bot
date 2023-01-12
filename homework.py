from http import HTTPStatus
import logging
import sys
import time
import requests
import os
import telegram
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)
logger = logging.getLogger(__name__)


def check_tokens():
    """Проверка доступности переменных окружения."""
    env_var = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for var in env_var:
        if not var:
            logger.critical(f'Отсутствует токен {var}')
            return False
        return True


def send_message(bot, message):
    """Отправляем сообщения в телеграм."""
    try:
        logger.debug(f'Бот должен отправить {message}')
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
    except Exception as error:
        logger.error(f'Бот не смог отправить сообщение. Ошибка - {error}')
    else:
        logger.debug(f'Бот успешно отправил {message}')


def get_api_answer(timestamp):
    """Отправим запрос к API-домашка."""
    class CustomError(Exception):
        """Применим кастомные исключения."""

    payload = {'from_date': timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != HTTPStatus.OK:
            logger.error(
                f'API-сервер не доступен: {response.status_code}')
            raise requests.RequestException(
                f'API-сервер не доступен: {response.status_code}')
        else:
            return response.json()
    except requests.RequestException as error:
        raise CustomError(f'Возникла ошибка - {error}')


def check_response(response):
    """Проверка ответа API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError(
            'Ответ от api-сервера не содержит запрашиваемый тип данных')
    if 'current_date' not in response or 'homeworks' not in response:
        raise KeyError(
            'Ответ от api-сервера не содержит нужные ключи')
    if not isinstance(response.get('homeworks'), list):
        raise TypeError(
            'Ответ от api-сервера не содержит запрашиваемый тип данных')
    homeworks = response.get('homeworks')
    return homeworks


def parse_status(homework):
    """Извлекаем информацию о конкретной.
    домашней работе, статус этой работы.
    """
    class CustomError(Exception):
        """Применим кастомные исключения."""

    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ: homework_name')
    if 'status' not in homework:
        raise KeyError('Отсутствует ключ: status')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        logger.error('Cтатус проверки задания не изменился')
        raise CustomError('Некорректный статус проверки задания')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствуют обязательные переменные окружения')
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0
    old_message = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            homework = homeworks[0]
            message = parse_status(homework)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(f'Сбой в работе программы: {error}')

        finally:
            if message != old_message:
                send_message(bot, message)
                old_message = message
                logger.debug('Бот успешно отправил {message}')

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
