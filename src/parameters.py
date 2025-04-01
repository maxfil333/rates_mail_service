import os
import sys
import msvcrt


if getattr(sys, 'frozen', False):  # в сборке
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    with open(os.path.join(BASE_DIR, 'config_files', "crypto.key"), 'r') as f:
        CRYPTO_KEY = f.read()
except FileNotFoundError as e:
    print(e)
    print('Не найден crypto.key')
    if getattr(sys, 'frozen', False):
        msvcrt.getch()
        sys.exit()

CRYPTO_ENV = os.path.join(BASE_DIR, 'config_files', "encrypted.env")


# ----------------------------------------------------------------------------------------------------------------------

SERVICES1C = [
    "Фрахт",
    "Транспортно-Экспедиторское обслуживание",
    "Организация ЖД перевозки",
    "Организация автовывоза"
]

_SERVICES_KEYWORDS = {
    "Фрахт": ['фрахт', 'организация морской перевозки'],
    "Транспортно-Экспедиторское обслуживание": ['транспортно-экспедиторское обслуживание'],
    "Организация ЖД перевозки": ['организация жд перевозки', "жд", "ржд"],
    "Организация автовывоза": ['организация автовывоза', 'автовывоз', 'организация автоперевозки', 'автоперевозка', "организация автомобильной перевозки"]
}

SERVICES_KEYWORDS = {}
for name1C, key_words_list in _SERVICES_KEYWORDS.items():
    for key_word in key_words_list:
        SERVICES_KEYWORDS[key_word.lower()] = name1C
