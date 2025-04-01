import time
import email
import imaplib
import traceback
from typing import Optional
from email.message import Message

import config
from src.models import EmailData
from src.utils import (connect_to_imap, get_unseen_messages, decode_subject, extract_text_content, extract_html_content,
                       send_email, format_csv_to_table)


def main(email_user: str, email_pass: str, imap_server: str, imap_port: int = 993) -> list[EmailData]:
    """Проверяет и обрабатывает новые письма"""

    result = []

    # Подключение к серверу
    mail: imaplib.IMAP4_SSL = connect_to_imap(email_user, email_pass, imap_server, imap_port)
    if not mail:
        return result

    try:
        # Получение новых писем
        message_ids: list[bytes] = get_unseen_messages(mail)
        if not message_ids:
            print("Новых писем нет")
            return result

        print(f"Найдено новых писем: {len(message_ids)}")

        # Обработка каждого письма
        for msg_id in message_ids:

            email_data = EmailData()

            # Получение письма без отметки как прочитанное
            status, msg_data = mail.fetch(msg_id.decode('utf-8'), 'BODY.PEEK[]')
            if status != 'OK':
                continue

            # Парсинг письма
            email_message: Message = email.message_from_bytes(msg_data[0][1])

            # Извлечение основных данных
            subject: str = decode_subject(email_message["Subject"])
            sender: str = email_message.get("From", "Неизвестный отправитель")
            date: str = email_message.get("Date", "Дата неизвестна")
            email_data.subject = subject
            email_data.sender = sender
            email_data.date = date

            # Извлечение текстовой части
            text_content: Optional[str] = extract_text_content(email_message)
            if text_content:
                email_data.text = text_content

            # Извлечение html части
            html_content: Optional[str] = extract_html_content(email_message)
            if html_content:
                email_data.html = html_content

            result.append(email_data)

            # Запись csv
            # email_data.rate_tables_to_csv(path='CSVs')

            # Отметить как прочитанное
            mail.store(msg_id.decode('utf-8'), '+FLAGS', '\\Seen')

            # Отправка ответного письма
            if html_content:
                email_text = "\n+\n".join(map(format_csv_to_table, email_data.rate_tables_csv))
                send_email(email_text=email_text,
                           email_format='html',
                           recipient_email=email_data.sender_address,
                           subject=f'Автоответ от {email_user}',
                           email_user=email_user,
                           email_pass=email_pass,
                           )

        return result

    except Exception:
        print(traceback.format_exc())
        return []

    finally:
        print("Закрытие соединения...")
        mail.close()
        mail.logout()


if __name__ == "__main__":

    IMAP_SERVER: str = "imap.gmail.com"

    while True:
        result = main(email_user=config.EMAIL_ADDRESS,
                      email_pass=config.EMAIL_PASSWORD,
                      imap_server=IMAP_SERVER)
        print(result)
        time.sleep(30)
