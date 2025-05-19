import re
import traceback

import smtplib
import chardet
import pandas as pd
from uuid import uuid4
from typing import Literal
from bs4 import BeautifulSoup
from typing import List, Optional, Tuple, Union

import imaplib
from email.message import Message
from email.header import decode_header
from email.mime.text import MIMEText

from src.parameters import SERVICES_KEYWORDS, FIELDS_ALIAS, FIELDS_ALIAS_REVERSED


# ---------------------------------------------------------------------------------------------------------------- email

def connect_to_imap(email_user: str, email_pass: str, imap_server: str,
                    imap_port: int = 993) -> Optional[imaplib.IMAP4_SSL]:
    """Устанавливает соединение с IMAP сервером и выполняет авторизацию"""
    try:
        mail = imaplib.IMAP4_SSL(imap_server, imap_port)  # Создание SSL соединения
        mail.login(email_user, email_pass)  # Авторизация
        mail.select("inbox")  # Выбор папки "Входящие"
        return mail
    except Exception as e:
        raise Exception(f"Ошибка подключения к IMAP: {str(e)}")


def get_unseen_messages(mail: imaplib.IMAP4_SSL) -> List[bytes]:
    """Возвращает список ID непрочитанных писем"""
    status, messages = mail.search(None, 'UNSEEN')  # Поиск непрочитанных писем
    if status != 'OK':
        print("Ошибка при поиске писем")
        return []
    message_ids: List[bytes] = messages[0].split()  # Разделение строки ID на список
    return message_ids


def detect_encoding(body: bytes) -> str:
    """Определяет кодировку для переданных байтов"""

    # 1. Определяем через chardet
    detection = chardet.detect(body)
    encoding = detection['encoding'] if detection['confidence'] > 0.7 else None
    if encoding:
        try:
            body.decode(encoding)  # Проверяем, работает ли
            return encoding
        except UnicodeDecodeError:
            pass

    # 2. Fallback-кодировки
    for fallback_encoding in ('utf-8', 'windows-1251', 'iso-8859-1'):
        try:
            body.decode(fallback_encoding)  # Проверяем
            return fallback_encoding
        except UnicodeDecodeError:
            continue

    # 3. Если ничего не подошло, возвращаем utf-8
    return 'utf-8'


def decode_subject(subject: Optional[str]) -> str:
    """Декодирует тему письма из закодированного формата"""
    if not subject:
        return "(Без темы)"
    decoded: List[Tuple[Union[bytes, str], Optional[str]]] = decode_header(subject)
    subject_text: str = ""
    for text, encoding in decoded:
        if isinstance(text, bytes):
            subject_text += text.decode(encoding or 'utf-8', errors='ignore')
        else:
            subject_text += text
    return subject_text


def extract_text_content(email_message: Message) -> Optional[str]:
    """Извлекает текстовую часть письма"""
    if email_message.is_multipart():  # True, если письмо состоит из нескольких частей (текст + HTML + вложения + ..)
        for part in email_message.walk():  # part: <class 'email.message.Message'>
            if part.get_content_type() == "text/plain":  # text/plain - обычный текст письма
                body: bytes = part.get_payload(decode=True)
                if body:
                    encoding = detect_encoding(body)
                    decoded: str = body.decode(encoding, errors='ignore')
                    return decoded
    else:
        body = email_message.get_payload(decode=True)
        if body:
            encoding = detect_encoding(body)
            return body.decode(encoding, errors='ignore')
    return None


def extract_html_content(email_message: Message) -> Optional[str]:
    """Извлекает HTML часть письма"""
    html_content: Optional[bytes] = None
    if email_message.is_multipart():
        for part in email_message.walk():
            if part.get_content_type() == "text/html":
                html_content: bytes = part.get_payload(decode=True)
                break
    elif email_message.get_content_type() == "text/html":
        html_content: bytes = email_message.get_payload(decode=True)

    if html_content:
        encoding = detect_encoding(html_content)
        html_decoded: str = html_content.decode(encoding, errors='ignore')
        return html_decoded
    return None


def send_email(email_text: str,
               email_format: Literal['plain', 'html'],
               recipient_email: str,
               subject: str,
               email_user: str,
               email_pass: str,
               smtp_server: str = "smtp.gmail.com",
               smtp_port: int = 587) -> bool:
    """
    Отправляет email с заданным текстом на указанный адрес

    Args:
        email_text: Текст письма
        email_format: Тип письма plain / html
        recipient_email: Адрес получателя
        subject: Тема письма
        email_user: Адрес отправителя/логин
        email_pass: Пароль отправителя
        smtp_server: SMTP сервер (по умолчанию Gmail)
        smtp_port: SMTP порт (по умолчанию 587)

    Returns:
        bool: Успешность отправки
    """
    try:
        # Создаем объект письма
        msg = MIMEText(email_text, email_format, 'utf-8')
        msg['Subject'] = subject
        msg['From'] = email_user
        msg['To'] = recipient_email

        # Устанавливаем соединение с SMTP сервером
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Запускаем шифрование
            server.login(email_user, email_pass)  # Авторизуемся
            server.send_message(msg)  # Отправляем письмо

        return True

    except Exception:
        print(traceback.format_exc())
        return False


# --------------------------------------------------------------------------------------------------------------- tables

def find_tables_positions(soup: BeautifulSoup) -> list:
    """Извлекает из html-структуры (soup) список таблиц (контент, позиция начала, позиция конца) """

    start = 0
    tables_info = []
    soup_tables = soup.find_all('table')
    for table in soup_tables:
        table_html = str(table)
        find_ = str(soup).find(table_html, start)
        if find_ != -1:
            start = find_
            end = find_ + len(table_html) - 1

            # исключаем вложенные таблицы
            end_of_last_table = tables_info[-1]['end'] if tables_info else 0
            if end_of_last_table <= start:
                tables_info.append({'table': table_html, 'start': start, 'end': end})

    return tables_info


def replace_tables_with_uuid(soup: BeautifulSoup, tables_info: list) -> tuple[list, str]:
    """
    Заменяет контент таблицы в html-структуре (soup) на UUID;
    Принимает на вход soup-объект и tables_info (результат функции find_tables_positions);
    Добавляет в tables_info ключ "_id"
    """

    text = str(soup)
    last_end = 0
    replacement = ''
    for i, table in enumerate(tables_info):
        table['_id'] = str(uuid4())
        replacement += text[last_end:table['start']] + '\n' + table['_id'] + '\n'
        last_end = table['end'] + 1
        if i == len(tables_info) - 1:
            replacement += text[table['end'] + 1:]

    return tables_info, replacement


def replace_uuid_with_tables(replacement: str, tables_info: list):
    """
    Обратная функция replace_tables_with_uuid;
    Принимает на вход replacement и tables_info (результат функции replace_tables_with_uuid);
    Восстанавливает исходный html до замены таблиц на id
    """

    _ids = [t['_id'] for t in tables_info]
    original_tables = [t['table'] for t in tables_info]
    for _id, original_table in zip(_ids, original_tables):
        replacement = replacement.replace(_id, original_table)
    return replacement


def html_table_to_df(html_table: str) -> pd.DataFrame:
    """ Замена стандартной pd.read_html. Разделяет построчно параграфы (в тегах <p>) """

    soup = BeautifulSoup(html_table, 'html.parser')
    table = soup.find('table')

    rows = []
    for tr in table.find_all('tr'):
        cells = []
        for td in tr.find_all('td'):
            # Извлекаем текст из всех тегов <p>
            paragraphs = [p.get_text() for p in td.find_all('p')]
            # Если найдено более одного абзаца, объединяем с переносами строк
            if len(paragraphs) > 1:
                cell_text = "\n".join(paragraphs)
            elif paragraphs:
                cell_text = paragraphs[0]
            else:
                cell_text = td.get_text(strip=True)
            cells.append(cell_text)
        rows.append(cells)

    # raw[0] -> Header
    df = pd.DataFrame(rows)
    df.columns = df.iloc[0]
    df = df.drop(df.index[0])
    return df


def extract_outer_html_tables(html_content: str) -> List[pd.DataFrame]:
    """Извлекает только верхнеуровневые таблицы из HTML"""

    if not html_content:
        print('No html_content in extract_outer_html_tables')
        return []

    try:
        soup = BeautifulSoup(html_content, "html.parser")
        top_level_tables: list[str] = []

        # Смотрим только таблицы, у которых нет родительской <table>
        for table in soup.find_all("table"):
            if not table.find_parent("table"):
                top_level_tables.append(str(table))  # Преобразуем обратно в HTML

        # Преобразуем верхнеуровневые таблицы в DataFrame
        return [html_table_to_df(table) for table in top_level_tables]

    except Exception as e:
        print(f"Ошибка при извлечении таблиц из HTML: {str(e)}")
        return []


# ------------------------------------------------------------------------------------------------------- postprocessing

def split_html(html_content: str) -> list[str]:
    regex = (r'(?:.*sent:.*$\s)(?:.*to:.*$\s)(?:.*cc:.*$\s)?(?:.*subject:.*$)'
             r'|'
             r'(?:.*отправлено:.*$\s)(?:.*кому:.*$\s)(?:.*копия:.*$\s)?(?:.*тема:.*$)')

    parts = re.split(regex, html_content, flags=re.IGNORECASE | re.MULTILINE)

    return parts


# ---------------------------------------------------------------------------------------------------- postprocessing df

def dataframe_is_table_rates(df: pd.DataFrame) -> bool:
    """
    Проверяет, является ли DataFrame валидным по следующим критериям:
    1) Состоит из 3 столбцов
    2) Имена столбцов == FIELDS_ALIAS
    """

    if df.shape[1] != 3:
        return False

    return compare_fields_names(fields_alias=FIELDS_ALIAS,
                                extracted_fields=list(df.columns))


def compare_fields_names(fields_alias: dict, extracted_fields: list) -> bool:
    extracted_fields = [x.lower().strip() for x in extracted_fields]
    for field_name, aliases in fields_alias.items():
        for alias in aliases:
            alias = alias.lower().strip()
            if alias in extracted_fields:
                extracted_fields.remove(alias)
                break
    return len(extracted_fields) == 0


def postprocess_df(df) -> pd.DataFrame | None:
    try:
        df.columns = [c.lower().strip() for c in df.columns]
        df.columns = [FIELDS_ALIAS_REVERSED[x] for x in df.columns]  # приводим алиасы полей к изначальным наименованиям

        df['ставка'] = df['ставка'].apply(extract_first_number)
        df['вход'] = df['вход'].apply(extract_number_from_entry)
        df['наименование'] = df['наименование'].apply(lambda x: service_replace_by_service1C(x, SERVICES_KEYWORDS))
        df = remove_false_name_rows(df)
        return df

    except Exception:
        print(traceback.format_exc())


def extract_first_number(text: str) -> float | None:
    regex = r'^.*?(\d+(?:\.\d+)?).*$'
    text = re.sub(r'[^\S\n]', '', text)  # удаление всех пробельных символов кроме \n
    matches = re.findall(regex, text, flags=re.MULTILINE)
    if matches:
        return float(matches[0])


def cut_text_before_last_equal(text: str) -> str:
    last_equal = list(re.finditer(r'=', text))[-1]
    return text[last_equal.start():]


def extract_number_from_entry(text: str) -> float | None:
    if '=' in text:
        text = cut_text_before_last_equal(text)
    return extract_first_number(text)


def service_replace_by_service1C(service: str, keyword_dict: dict) -> str:
    service_lower = service.lower()
    for key_word, name1C in keyword_dict.items():
        if key_word in service_lower:
            return name1C
    return ''


def remove_false_name_rows(df):
    """ Удаляет из DataFrame строки с пустым полем 'Наименование' """
    return df[df['наименование'].apply(bool)]


# ---------------------------------------------------------------------------------------------------------------- other

def format_csv_to_table(csv_text):
    lines = csv_text.strip().split('\n')
    rows = [line.split(',') for line in lines]

    html = ['<table border="1" style="border-collapse: collapse; padding: 5px;">']
    for i, row in enumerate(rows):
        html.append('<tr>')
        for cell in row:
            tag = 'th' if i == 0 else 'td'
            html.append(f'  <{tag}>{cell.strip()}</{tag}>')
        html.append('</tr>')
    html.append('</table>')

    return '\n'.join(html)


if __name__ == "__main__":
    # print(compare_fields_names(FIELDS_ALIAS, ['Услуги', 'ВХОД', 'ставка']))
    print(compare_fields_names(FIELDS_ALIAS, ['Наименование', 'ВХоД', 'ставка', '1']))
    print(compare_fields_names(FIELDS_ALIAS, ['Услуги', 'ВХОД', 'ставка']))
