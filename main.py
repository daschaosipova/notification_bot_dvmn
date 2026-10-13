import os
import time
import logging
import requests
import telegram
from dotenv import load_dotenv


def configure_logging(tg_bot, chat_id):
    """Настраивает базовую конфигурацию логирования для приложения."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    tg_handler = TelegramLogsHandler(tg_bot=tg_bot, chat_id=chat_id)
    tg_handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(tg_handler)

def format_message(attempt):
    """Форматирует сообщение об проверке работы."""
    lesson_title = attempt["lesson_title"]
    lesson_url = attempt["lesson_url"]
    is_negative = attempt["is_negative"]

    if is_negative:
        verdict = "К сожалению, в работе нашлись ошибки. Нужно исправить."
    else:
        verdict = "Преподавателю всё понравилось, урок принят!"

    return (
        f"У вас проверили работу «{lesson_title}».\n\n"
        f"{verdict}\n\n"
        f"Ссылка на урок: {lesson_url}"
    )

class TelegramLogsHandler(logging.Handler):
    def __init__(self, tg_bot, chat_id):
        super().__init__()
        self.tg_bot = tg_bot
        self.chat_id = chat_id

    def emit(self, record):
        log_entry = self.format(record)
        if record.name.startswith('telegram'):
            return
        self.tg_bot.send_message(chat_id=self.chat_id, text=log_entry)

def main():
    load_dotenv(".env") 

    dvmn_token = os.getenv("DVMN_TOKEN")
    tg_token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")

    if not chat_id:
        return

    bot = telegram.Bot(token=tg_token)
    configure_logging(bot, chat_id)
    logging.info("bot started")
    
    headers = {"Authorization": f"Token {dvmn_token}"}
    url = "https://dvmn.org"
    params = {}

    while True:
        try:
            response = requests.get(url, headers=headers, params=params, timeout=95)
            response.raise_for_status()
            review_data = response.json()

            if review_data["status"] == "timeout":
                params["timestamp"] = review_data["timestamp_to_request"]

            elif review_data["status"] == "found":
                logging.info("found new review")
                params["timestamp"] = review_data["last_attempt_timestamp"]

                for attempt in review_data["new_attempts"]:
                    message = format_message(attempt)
                    bot.send_message(chat_id=chat_id, text=message)

        except requests.exceptions.ReadTimeout:
            continue
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError):
            time.sleep(10)
            continue
        except KeyboardInterrupt:
            break
        except Exception as err:
            logging.error("error occurred: %s", err, exc_info=True)
            time.sleep(5)

if __name__ == "__main__":
    main()

