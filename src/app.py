import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from urllib.parse import parse_qs, urlparse
from io import BytesIO

def get_check_number(url):
    """
    Извлекает номер чека из URL
    """
    parsed_url = urlparse(url)
    params = parse_qs(parsed_url.query)
    
    # Собираем параметры чека
    check_parts = []
    if 't' in params:
        check_parts.append(params['t'][0])
    if 'r' in params:
        check_parts.append(params['r'][0])
    if 'c' in params:
        check_parts.append(params['c'][0])
    
    # Если параметры найдены, создаем имя файла, иначе используем дефолтное
    if check_parts:
        return '_'.join(check_parts)
    return 'receipt'

def fetch_receipt_data(url):
    """
    Получает данные чека по URL
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        st.error(f"Ошибка при получении данных: {str(e)}")
        return None

def parse_receipt_html(html_content):
    """
    Парсит HTML-страницу и извлекает данные чека
    """
    if not html_content:
        return None
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Список для хранения данных товаров
    items_data = []
    
    # Находим все строки с товарами
    product_rows = soup.find_all('tr', class_='products-row')
    
    for row in product_rows:
        # Получаем все td элементы в строке
        cells = row.find_all('td')
        
        # Базовые данные товара
        item_data = {
            'Nomi': cells[0].text.strip(),
            'Soni': cells[1].text.strip(),
            'Narxi': cells[2].text.strip().replace(',', ''),  # Удаляем запятые из чисел
            'Chegirma': '',
            'Shtrix kodi': '',
            'MXIK-kod': '',
            'MXIK nomi': '',
            'Markirovka kodi': ''
        }
        
        # Находим все следующие строки до следующего products-row
        next_element = row.find_next_sibling('tr')
        while next_element and 'products-row' not in next_element.get('class', []):
            if 'code-row' in next_element.get('class', []):
                label_cell = next_element.find('td')
                value_cell = next_element.find_all('td')[-1]
                
                if label_cell and value_cell:
                    label = label_cell.text.strip()
                    value = value_cell.text.strip()
                    
                    if 'Chegirma' in label:
                        item_data['Chegirma'] = value
                    elif 'Shtrix kodi' in label:
                        # Очищаем штрих-код от всех символов кроме цифр
                        cleaned_value = ''.join(filter(str.isdigit, value))
                        item_data['Shtrix kodi'] = cleaned_value
                    elif 'MXIK kodi' in label:
                        # Очищаем MXIK-код от всех символов кроме цифр
                        cleaned_value = ''.join(filter(str.isdigit, value))
                        item_data['MXIK-kod'] = cleaned_value
                    elif 'MXIK nomi' in label:
                        item_data['MXIK nomi'] = value
                    elif 'Markirovka kodi' in label:
                        item_data['Markirovka kodi'] = value
            
            next_element = next_element.find_next_sibling('tr')
        
        items_data.append(item_data)
    
    # Создаем DataFrame
    df = pd.DataFrame(items_data)
    
    # Очищаем значения от лишних пробелов
    for col in df.columns:
        df[col] = df[col].str.strip()
    
    # Преобразуем типы данных
    df['Soni'] = pd.to_numeric(df['Soni'], errors='coerce')
    df['Narxi'] = pd.to_numeric(df['Narxi'], errors='coerce')
    df['Shtrix kodi'] = pd.to_numeric(df['Shtrix kodi'], errors='coerce')
    df['MXIK-kod'] = pd.to_numeric(df['MXIK-kod'], errors='coerce')
    
    # Форматируем числовые колонки
    df['Narxi'] = df['Narxi'].round(2)  # Округляем до 2 знаков после запятой
    
    return df

def main():
    st.title("🧾 Soliq Checkmate")
    
    # Добавляем описание
    st.markdown("""
    Простое и удобное приложение для извлечения данных из фискальных чеко по URL.
    
    ### Как использовать:
    1. Вставьте ссылку на онлайн фискальный чек в поле ввода.
    2. Нажмите «Получить данные».
    3. Просмотрите результаты и скачайте их в формате Excel.
    4. Откройте скачанный файл — и таблица готова!
    """)
    
    # Поле для ввода URL
    receipt_url = st.text_input("Введите URL фискального чека:", 
                               placeholder="https://ofd.soliq.uz/check?t=...")
    
    if st.button("Получить данные"):
        if receipt_url:
            with st.spinner("Загрузка данных..."):
                # Получаем HTML-контент
                html_content = fetch_receipt_data(receipt_url)
                
                if html_content:
                    # Парсим данные
                    df = parse_receipt_html(html_content)
                    
                    if df is not None and not df.empty:
                        st.success("Данные успешно получены!")
                        
                        # Отображаем таблицу
                        st.dataframe(df)
                        
                        # Получаем номер чека для имени файла
                        check_number = get_check_number(receipt_url)
                        
                        # Создаем Excel файл в памяти
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            df.to_excel(writer, index=False, sheet_name='Чек')
                            # Получаем workbook и worksheet
                            workbook = writer.book
                            worksheet = writer.sheets['Чек']
                            
                            # Автоматически подгоняем ширину столбцов
                            for i, col in enumerate(df.columns):
                                max_length = max(
                                    df[col].astype(str).apply(len).max(),
                                    len(col)
                                ) + 2
                                worksheet.set_column(i, i, max_length)
                        
                        # Подготавливаем файл для скачивания
                        output.seek(0)
                        
                        # Кнопка для скачивания Excel
                        st.download_button(
                            label="Скачать данные (Excel)",
                            data=output,
                            file_name=f"check_{check_number}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        st.error("Не удалось найти данные в чеке")
        else:
            st.warning("Пожалуйста, введите URL чека")

if __name__ == "__main__":
    main() 