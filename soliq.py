import os
import sys
import subprocess

def main():
    # Проверяем, установлены ли зависимости
    try:
        import streamlit
        import pandas
        import httpx
        import beautifulsoup4
    except ImportError:
        print("Устанавливаем необходимые пакеты...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Установка завершена!")

    # Запускаем приложение
    print("Запускаем Soliq Checkmate...")
    os.system(f"{sys.executable} -m streamlit run src/app.py") 