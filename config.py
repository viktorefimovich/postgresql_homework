import os
from configparser import ConfigParser


def config(filename="database.ini", section="postgresql"):
    """Функция чтения данных из файла конфигурации"""

    if not os.path.exists(filename):
        raise FileNotFoundError(f"Файл конфигурации {filename} не найден.")

    parser = ConfigParser()

    try:
        parser.read(filename)
    except Exception as e:
        raise Exception(f"Ошибка при чтении файла {filename}: {e}")

    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception(f'Section {section} is not found in the {filename} file.')
    return db
