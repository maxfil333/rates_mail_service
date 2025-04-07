import os
import sys
import argparse
import traceback
import extract_msg
from typing import Optional

from src.models import EmailData
from src.utils import decode_subject


def main(file_path: str) -> list[EmailData]:
    """ Обрабатывает указанный .msg файл и сохраняет результат в .csv/.xml """

    result = []

    try:
        # Чтение .msg файла с помощью extract-msg
        msg = extract_msg.Message(file_path)
        email_data = EmailData()

        # Извлечение основных данных
        subject: str = decode_subject(msg.subject)
        sender: str = msg.sender or "Неизвестный отправитель"
        date: str = msg.date or "Дата неизвестна"
        email_data.subject = subject
        email_data.sender = sender
        email_data.date = date

        # Извлечение текстовой части
        text_content: Optional[str] = msg.body
        if text_content:
            email_data.text = text_content

        # Извлечение html части
        html_content: Optional[str] = msg.htmlBody
        if html_content:
            email_data.html = html_content
            # Вычисление таблиц ставок
            email_data.rate_tables_processor()

        result.append(email_data)

        # Запись csv / xml
        email_data.rate_tables_export(
            extension='xml',
            folder=os.path.dirname(os.path.abspath(file_path)),
            filename=os.path.splitext(os.path.basename(file_path))[0],
        )

        return result

    except Exception:
        print(traceback.format_exc())
        return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Обработка .msg файла и сохранение результата в .csv")
    parser.add_argument("msg_file_path", type=str, help="Путь к .msg файлу для обработки")
    args = parser.parse_args()
    msg_file_path = args.msg_file_path
    if not os.path.exists(msg_file_path):
        print(f"Файл {msg_file_path} не существует")
        sys.exit(1)
    result = main(msg_file_path)
    print(result)
