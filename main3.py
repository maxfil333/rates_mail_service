import os
import sys
import glob
import time
import traceback
import extract_msg
from typing import Optional

from src.models import EmailData
from src.utils import decode_subject
from src.logger import logger


def main(file_path: str) -> list[EmailData]:
    """ Мониторит и обрабатывает все .msg файлы в директории выше и сохраняет результат в .csv/.xml + .log """

    result = []
    msg = None

    try:
        logger.print("Чтение .msg файла с помощью extract-msg")
        msg = extract_msg.Message(file_path)
        email_data = EmailData()

        logger.print("Извлечение основных данных")
        subject: str = decode_subject(msg.subject)
        sender: str = msg.sender or "Неизвестный отправитель"
        date: str = msg.date or "Дата неизвестна"
        email_data.subject = subject
        email_data.sender = sender
        email_data.date = date

        logger.print("Извлечение текстовой части")
        text_content: Optional[str] = msg.body
        if text_content:
            email_data.text = text_content

        logger.print("Извлечение html части")
        html_content: Optional[str] = msg.htmlBody
        if html_content:
            email_data.html = html_content
            logger.print("Вычисление таблиц ставок")
            email_data.rate_tables_processor()

        result.append(email_data)

        logger.print("Запись csv / xml")
        folder = os.path.dirname(os.path.abspath(file_path))
        filename = os.path.splitext(os.path.basename(file_path))[0]
        email_data.rate_tables_export(
            extension='xml',
            folder=folder,
            filename=filename,
        )

        logger.print("Завершение работы программы.")

        logfile = os.path.join(folder, f'{filename}.log')
        logger.save(log_folder='', logfile_name=logfile)
        logger.clear()
        msg.close()
        os.remove(file_path)

        return result

    except Exception:
        logger.print(traceback.format_exc())
        if msg:
            msg.close()
        return []


if __name__ == "__main__":
    if getattr(sys, 'frozen', False):  # в сборке
        program_path = os.path.dirname(sys.executable)
    else:
        program_path = os.path.dirname(os.path.abspath(__file__))
    folder_with_messages = os.path.dirname(program_path)
    print(folder_with_messages)

    while True:
        for msg_file_path in glob.glob(os.path.join(folder_with_messages, '*.msg')):
            if not os.path.exists(msg_file_path):
                print(f"Файл {msg_file_path} не существует")
                sys.exit(1)
            result = main(msg_file_path)
            print(result)
        time.sleep(1)
