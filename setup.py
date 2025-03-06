import setuptools
import sys
import os.path


# Функция для чтения requirements.txt
def read_requirements():
    with open("requirements.txt", "r") as f:
        return [line.strip() for line in f if line.strip()]


# Функция для чтения README.md
def read_readme():
    with open("README.md", "r", encoding="utf-8") as f:
        return f.read()


# Проверка существования requirements.txt
if not os.path.exists("requirements.txt"):
    raise FileNotFoundError(
        "Файл requirements.txt не найден. Создайте его с помощью: pip freeze > requirements.txt"
    )

setuptools.setup(
    name="hosts_checker",  # Имя пакета
    version="1.0.0",  # Версия
    author="whiter",  # Ваше имя
    author_email="andr0804@mail.ru",  # Ваша почта
    description="Программа для мониторинга хостов по ICMP (ping)",  # Описание
    long_description=read_readme(),  # Подробное описание из README.md
    long_description_content_type="text/markdown",
    url="https://github.com/hripit/hosts_checker.git",  # Ссылка на репозиторий (можно указать позже)
    packages=setuptools.find_packages(),  # Автоматическое нахождение пакетов
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",  # Лицензия (можно изменить)
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",  # Требуемая версия Python
    install_requires=read_requirements(),  # Зависимости из requirements.txt
    entry_points={  # Точка входа для скрипта
        "console_scripts": [
            "hosts_checker=main:main",  # Замените "main" на ваш основной модуль
        ],
    },
    include_package_data=True,  # Включить непитоновские файлы (например, иконки)
    data_files=[  # Дополнительные файлы (если есть)
        ("templates", ["templates/example.csv"]),
    ] if os.path.exists("templates") else [],
)
