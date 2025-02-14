import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

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
            'Narxi': cells[2].text.strip(),
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
                        item_data['Shtrix kodi'] = value
                    elif 'MXIK kodi' in label:
                        item_data['MXIK-kod'] = value
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
    
    return df

def main():
    st.title("🧾 Soliq Checkmate")
    
    # Добавляем описание
    st.markdown("""
    Простое и удобное приложение для извлечения данных из фискальных чеко по URL.
    
    ### Как использовать:
    1. Вставьте ссылку на онлайн фискальный чек в поле ввода.
    2. Нажмите «Получить данные».
    3. Просмотрите результаты и скачайте их в формате CSV.
    4. Откройте Excel, перейдите во вкладку «Данные», выберите «Получить данные» → «Из файла» → «Из текста (CSV)».
    5. Укажите загруженный CSV-файл — и таблица готова!
    
    *Solic Checkmate экономит ваше время и превращает фискальные чеки в удобные таблицы за пару кликов.*
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
                        
                        # Кнопка для скачивания CSV
                        csv = df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Скачать данные (CSV)",
                            data=csv,
                            file_name="receipt_data.csv",
                            mime="text/csv"
                        )
                    else:
                        st.error("Не удалось найти данные в чеке")
        else:
            st.warning("Пожалуйста, введите URL чека")

if __name__ == "__main__":
    main() 