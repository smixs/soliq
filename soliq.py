import os
import sys
import subprocess

def main():
    print("Запуск Soliq Checkmate...")
    print(f"Текущая директория: {os.getcwd()}")
    print(f"Python версия: {sys.version}")
    
    # Проверяем наличие файла app.py
    if not os.path.exists('src/app.py'):
        print("ОШИБКА: Файл src/app.py не найден!")
        print("Убедитесь, что вы запускаете скрипт из корректной папки")
        return

    # Проверяем, установлены ли зависимости
    try:
        print("Проверка зависимостей...")
        import streamlit
        import pandas
        import httpx
        import beautifulsoup4
        print("Все зависимости установлены!")
    except ImportError as e:
        print(f"ОШИБКА: Не установлен пакет {str(e).split()[-1]}")
        print("Устанавливаем необходимые пакеты...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("Установка завершена!")
        except subprocess.CalledProcessError as e:
            print(f"ОШИБКА при установке пакетов: {e}")
            return

    # Запускаем приложение
    print("Запускаем Streamlit...")
    cmd = f"{sys.executable} -m streamlit run src/app.py"
    print(f"Выполняем команду: {cmd}")
    os.system(cmd)

if __name__ == "__main__":
    main() 