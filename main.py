import os
import time
import logging
import requests
import telegram
import argparse
from dotenv import load_dotenv


logger = logging.getLogger(__name__)


def configure_logging():
    """Настраивает базовую конфигурацию логирования для приложения."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def get_cli_arguments():
    """Создает парсер и возвращает аргументы командной строки."""
    parser = argparse.ArgumentParser(
        description="Бот для уведомлений о провероках работ на Devman."
    )
    parser.add_argument(
        "--chat_id",
        default=os.getenv("TG_CHAT_ID"),
        help="Telegram Chat ID пользователя для отправки уведомлений"
    )
    return parser.parse_args()


def format_message(attempt):
    """Форматирует сообщение об проверке работы."""
    lesson_title = attempt["lesson_title"]
    lesson_url = attempt["lesson_url"]
    is_negative = attempt["is_negative"]

    if is_negative:
        verdict = (
            "К сожалению, в работе нашлись ошибки. "
            "Нужно исправить."
        )
    else:
        verdict = (
            "Преподавателю всё понравилось, "
            "урок принят!"
        )

    return (
        f"У вас проверили работу «{lesson_title}».\n\n"
        f"{verdict}\n\n"
        f"Ссылка на урок: {lesson_url}"
    )


def main():
    load_dotenv(".env")

    configure_logging()

    args = get_cli_arguments()

    dvmn_token = os.getenv("DVMN_TOKEN")
    tg_token = os.getenv("TELEGRAM_TOKEN")

    if not args.chat_id:
        logger.error(
            "Не указан TG_CHAT_ID ни в .env, "
            "ни через аргументы командной строки!"
        )
        return

    bot = telegram.Bot(token=tg_token)

    headers = {"Authorization": f"Token {dvmn_token}"}
    url = "https://dvmn.org/api/long_polling/"

    params = {}

    logger.info(
        "Бот успешно запущен для Chat ID: %s и ожидает проверок...",
        args.chat_id
    )

    while True:
        try:
            response = requests.get(
                url, headers=headers, params=params, timeout=5
            )
            response.raise_for_status()

            review_data = response.json()

            if review_data["status"] == "timeout":
                logger.info("Новых проверок нет. Перезапускаем ожидание.")
                params["timestamp"] = review_data["timestamp_to_request"]

            elif review_data["status"] == "found":
                logger.info("Найдена новая проверка!")
                params["timestamp"] = review_data[
                    "last_attempt_timestamp"
                ]

                for attempt in review_data["new_attempts"]:
                    message = format_message(attempt)
                    bot.send_message(
                        chat_id=args.chat_id, text=message
                    )

        except requests.exceptions.ReadTimeout:
            logger.warning(
                "Сервер Devman не ответил за 5 секунд. "
                "Ждем 10 секунд перед повторным запросом..."
            )
            time.sleep(10)

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.HTTPError
        ):
            logger.warning(
                "Проблемы с сетью или сервером. "
                "Повторная попытка через 10 секунд..."
            )
            time.sleep(10)

        except KeyboardInterrupt:
            logger.info("Бот остановлен пользователем.")
            break

        except Exception as err:
            logger.error(
                "Произошла непредвиденная ошибка: %s",
                err, exc_info=True
            )
            time.sleep(5)


if __name__ == "__main__":
    main()
