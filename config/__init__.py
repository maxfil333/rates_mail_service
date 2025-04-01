import os
import sys
import msvcrt
from io import StringIO
from dotenv import load_dotenv
from cryptography.fernet import Fernet


try:
    with open(os.path.join(os.path.dirname(__file__), "crypto.key"), 'r') as f:
        CRYPTO_KEY = f.read()
except FileNotFoundError as e:
    print(e)
    print(f'Не найден crypto.key в текущей папке {__name__}')
    if getattr(sys, 'frozen', False):
        msvcrt.getch()
        sys.exit()


CRYPTO_ENV = os.path.join(os.path.dirname(__file__), "encrypted.env")


def get_stream_dotenv():
    """ uses crypto.key to decrypt encrypted environment.
    returns StringIO (for load_dotenv(stream=...)"""

    f = Fernet(CRYPTO_KEY)
    try:
        with open(CRYPTO_ENV, 'rb') as file:
            encrypted_data = file.read()
    except FileNotFoundError:
        print(f'Файл {CRYPTO_ENV} не найден.')
        if getattr(sys, 'frozen', False):
            msvcrt.getch()
            sys.exit()
        else:
            raise
    decrypted_data = f.decrypt(encrypted_data)  # bytes
    decrypted_data_str = decrypted_data.decode('utf-8')  # string
    string_stream = StringIO(decrypted_data_str)
    return string_stream


load_dotenv(stream=get_stream_dotenv())

EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
