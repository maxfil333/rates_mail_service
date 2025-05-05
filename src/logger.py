import os


class Logger:
    def __init__(self):
        self.data = []

    def print(self, *args, **kwargs):
        # Извлекаем параметры sep и end из kwargs, если они есть, или задаем значения по умолчанию
        sep = kwargs.pop('sep', ' ')
        end = kwargs.pop('end', '\n')
        # Формируем сообщение
        message = sep.join(map(str, args)) + end
        # Выводим сообщение в консоль
        print(message, **kwargs, end='')
        # Сохраняем сообщение в data
        self.data.append(message)

    def write(self, string_):
        self.data.append(string_ + '\n')

    def save(self, log_folder, logfile_name):
        # Записываем логи в файл
        log_file = os.path.join(log_folder, logfile_name)
        with open(log_file, 'w', encoding='utf-8') as file:
            file.writelines(self.data)

    def clear(self):
        self.data = []


logger = Logger()
