import os
import time
import requests
from dotenv import load_dotenv


def main():
    load_dotenv(".env")
    dvmn_token = os.getenv("DVMN_TOKEN")
    
    headers = {"Authorization": f"Token {dvmn_token}"}
    url = "https://dvmn.org/api/long_polling/"
    
    params = {}

    print("Бот успешно запущен и ожидает проверок...")

    while True:
        try:
            response = requests.get(url, headers=headers, params=params, timeout=5)
            response.raise_for_status()
            
            review_data = response.json()
            
            if review_data["status"] == "timeout":
                print("Новых проверок нет. Перезапускаем ожидание.")
                params["timestamp"] = review_data["timestamp_to_request"]
                
            elif review_data["status"] == "found":
                print("Найдена новая проверка!")
                params["timestamp"] = review_data["last_attempt_timestamp"]
                
                for attempt in review_data["new_attempts"]:
                    lesson_title = attempt["lesson_title"]
                    lesson_url = attempt["lesson_url"]
                    is_negative = attempt["is_negative"]
                    
                    if is_negative:
                        verdict = "К сожалению, в работе нашлись ошибки. Нужно исправить."
                    else:
                        verdict = "Преподавателю всё понравилось, урок принят!"
                        
                    print(f"Проверена работа: «{lesson_title}»\nСсылка: {lesson_url}\nВердикт: {verdict}\n")
                    print(review_data)
                    # ТУТ в будущем будет отправка сообщения в Telegram

        except requests.exceptions.ReadTimeout:
            print("Сервер Devman не ответил за 5 секунд. Ждем 10 секунд перед повторным запросом...")
            time.sleep(10)
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError):
            print("Проблемы с сетью или сервером. Повторная попытка через 10 секунд...")
            time.sleep(10)
        except Exception as e:
            print(f"Произошла ошибка: {e}")
            time.sleep(5)
        except KeyboardInterrupt:
            print("\nБот остановлен пользователем.")
            break


if __name__ == "__main__":
    main()
