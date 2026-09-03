import os
import time
import logging
import requests
import telegram
from dotenv import load_dotenv


logger = logging.getLogger(__name__)


def configure_logging():
    """Настраивает базовую конфигурацию логирования для приложения."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


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

    dvmn_token = os.getenv("DVMN_TOKEN")
    tg_token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")

    if not chat_id:
        logger.error("Не указан TG_CHAT_ID в .env!")
        return

    bot = telegram.Bot(token=tg_token)

    headers = {"Authorization": f"Token {dvmn_token}"}
    url = "https://dvmn.org/api/long_polling/"

    params = {}

    logger.info(
        "Бот успешно запущен для Chat ID: %s и ожидает проверок...",
        chat_id
    )

    while True:
        try:
            response = requests.get(
                url, headers=headers, params=params, timeout=95
            )
            response.raise_for_status()

            review_data = response.json()

            if review_data["status"] == "timeout":
                params["timestamp"] = review_data["timestamp_to_request"]

            elif review_data["status"] == "found":
                logger.info("Найдена новая проверка!")
                params["timestamp"] = review_data[
                    "last_attempt_timestamp"
                ]

                for attempt in review_data["new_attempts"]:
                    message = format_message(attempt)
                    bot.send_message(
                        chat_id=chat_id, text=message
                    )

        except requests.exceptions.ReadTimeout:
            continue

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
