import os
import pandas as pd
from bs4 import BeautifulSoup

from email.utils import parseaddr
from src.utils import (find_tables_positions, replace_tables_with_uuid, replace_uuid_with_tables,
                       split_html, extract_outer_html_tables, dataframe_is_table_rates, postprocess_df)


class EmailData:
    def __init__(self):
        self.text = None
        self.html = None
        self._soup = None
        self.subject = None
        self._sender = None
        self.sender_address = None
        self.date = None

        self.tables_info = []
        self.replacement = ""
        self.restored = ""
        self.parts = []
        self.raw_rate_tables = []
        self.rate_tables = []
        self.rate_tables_csv = []

    def rate_tables_processor(self) -> None:
        """ Вычисление таблиц ставок """

        self._soup = BeautifulSoup(self.html, 'html.parser')
        tables_info = find_tables_positions(self._soup)
        tables_info, replacement = replace_tables_with_uuid(self._soup, tables_info)

        self.tables_info = tables_info
        self.replacement = replacement
        self.restored = replace_uuid_with_tables(self.replacement, self.tables_info)

        self.parts = split_html(self.replacement)
        if self.parts:
            last_message_with_ids = self.parts[0]
            last_message: str = replace_uuid_with_tables(last_message_with_ids, self.tables_info)
            last_message_outer_tables: list[pd.DataFrame] = extract_outer_html_tables(last_message)
            self.raw_rate_tables = [df for df in last_message_outer_tables if dataframe_is_table_rates(df)]
            self.rate_tables = [postprocess_df(df) for df in self.raw_rate_tables]

            # если хотя бы одну таблицу не удалось обработать, пропускается все письмо
            if any([x is None for x in self.rate_tables]):
                self.rate_tables = []

            self.rate_tables_csv = [df.to_csv(index=False) for df in self.rate_tables]

    def rate_tables_to_csv(self, folder, filename='result'):
        if not hasattr(self, 'rate_tables_csv'):
            print('Rate tables processing has not been performed yet.')
            return 0
        elif not self.rate_tables_csv:
            print('No rate tables were extracted to CSV.')
            return 0
        else:
            os.makedirs(folder, exist_ok=True)
            for i, csv in enumerate(self.rate_tables_csv):
                file_path = os.path.join(folder, f'{filename}_{i}.csv')
                try:
                    with open(file_path, 'w', encoding="utf-8") as f:
                        f.write(csv)
                except IOError as e:
                    print(f'Error writing file {file_path}: {e}')

    @property
    def sender(self):
        """Геттер для получения значения"""
        return self._sender

    @sender.setter
    def sender(self, value):
        """Сеттер для установки значения и авто-вычисления отправителя"""
        self._sender = value
        _, email = parseaddr(self._sender)
        self.sender_address = email if email else None


if __name__ == '__main__':
    e = EmailData()

    print(e.text)
    print(e.html)
    print(e.tables_info)
    print(e.replacement)

    e.html = '1'
    print('=============')

    print(e.text)
    print(e.html)
    print(e.tables_info)
    print(e.replacement)
