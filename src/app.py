import streamlit as st
import httpx
from bs4 import BeautifulSoup
import pandas as pd
import re
from urllib.parse import parse_qs, urlparse
from io import BytesIO
import sys

# Определяем заголовки запроса как глобальную переменную
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0'
}

# Настройки клиента httpx
CLIENT_SETTINGS = {
    'timeout': 15.0,  # Общий таймаут
    'follow_redirects': True,
    'http2': True,
    'verify': True,
    'limits': httpx.Limits(
        max_keepalive_connections=5,
        max_connections=10,
        keepalive_expiry=5
    )
}

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
    Получает данные чека по URL используя httpx
    """
    try:
        st.write("Отправка запроса к", url)
        
        # Создаем клиент с retry механизмом
        transport = httpx.HTTPTransport(retries=3)
        
        with httpx.Client(transport=transport, **CLIENT_SETTINGS) as client:
            response = client.get(url, headers=HEADERS)
            
            st.write(f"Статус ответа: {response.status_code}")
            st.write(f"Заголовки ответа: {dict(response.headers)}")
            
            response.raise_for_status()
            return response.text
            
    except httpx.TimeoutException:
        st.error("Превышено время ожидания ответа от сервера (15 сек). Пожалуйста, попробуйте позже.")
        return None
    except httpx.ConnectError as e:
        st.error(f"Не удалось подключиться к серверу. Ошибка: {str(e)}")
        st.write("Детали ошибки подключения:", str(e))
        return None
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            st.error("Чек не найден. Проверьте правильность ссылки.")
        else:
            st.error(f"Ошибка сервера: {e.response.status_code}")
            st.write("Тело ответа:", e.response.text[:500])
        return None
    except Exception as e:
        st.error(f"Произошла непредвиденная ошибка: {str(e)}")
        st.write("Тип ошибки:", type(e).__name__)
        st.write("Детали ошибки:", str(e))
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
    st.set_page_config(
        page_title="Soliq Checkmate",
        page_icon="🧾",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Показываем информацию о среде выполнения (только при отладке)
    with st.expander("Отладочная информация"):
        st.write("Python версия:", sys.version)
        st.write("Streamlit версия:", st.__version__)
        st.write("httpx версия:", httpx.__version__)
        st.write("User Agent:", HEADERS['User-Agent'])  # Используем глобальные заголовки
    
    # Центрируем заголовок и подпись
    st.markdown("<h1 style='text-align: center;'>🧾 Soliq Checkmate</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 11px; margin-top: -15px; color: #9DB2BF;'>made with 🩵 by <a href='https://tdigroup.uz' style='color: #9DB2BF;'>tdigroup.uz</a></p>", unsafe_allow_html=True)
    
    # Добавляем описание (центрированное)
    st.markdown("""
    <div style='text-align: center;'>
    <h3>Как использовать:</h3>
    1. Вставьте ссылку на онлайн фискальный чек<br>
    2. Нажмите «Получить данные»<br>
    3. Просмотрите результаты<br>
    4. Скачайте в формате Excel
    </div>
    """, unsafe_allow_html=True)
    
    # Добавляем отступ перед полем ввода
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Создаем три колонки для центрирования
    left_col, center_col, right_col = st.columns([1, 2, 1])
    
    # Поле для ввода URL в центральной колонке
    with center_col:
        # Центрируем label для поля ввода
        st.markdown("<p style='text-align: center;'>Введите URL фискального чека:</p>", unsafe_allow_html=True)
        receipt_url = st.text_input(
            "",  # Убираем label, так как он уже добавлен выше
            placeholder="https://ofd.soliq.uz/check?t=...",
            label_visibility="collapsed"  # Скрываем пустой label
        )
        
        # Центрируем кнопку
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            submit_button = st.button("Получить данные", type="primary", use_container_width=True)
        
        if submit_button:
            if not receipt_url:
                st.warning("Пожалуйста, введите URL чека")
                return
            
            if not receipt_url.startswith("https://ofd.soliq.uz/check"):
                st.error("Неверный формат ссылки. Ссылка должна начинаться с 'https://ofd.soliq.uz/check'")
                return
            
            with st.spinner("Загрузка данных..."):
                html_content = fetch_receipt_data(receipt_url)
                
                if html_content:
                    df = parse_receipt_html(html_content)
                    
                    if df is not None and not df.empty:
                        st.success("Данные успешно получены!")
                        
                        # Отображаем таблицу
                        st.dataframe(
                            df,
                            hide_index=True,
                            use_container_width=True
                        )
                        
                        # Получаем номер чека для имени файла
                        check_number = get_check_number(receipt_url)
                        
                        # Создаем Excel файл в памяти
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            df.to_excel(writer, index=False, sheet_name='Чек')
                            workbook = writer.book
                            worksheet = writer.sheets['Чек']
                            
                            # Автоматически подгоняем ширину столбцов
                            for i, col in enumerate(df.columns):
                                max_length = max(
                                    df[col].astype(str).apply(len).max(),
                                    len(col)
                                ) + 2
                                worksheet.set_column(i, i, max_length)
                        
                        output.seek(0)
                        
                        st.download_button(
                            label="💾 Скачать Excel",
                            data=output,
                            file_name=f"check_{check_number}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        st.error("Не удалось найти данные в чеке. Проверьте правильность ссылки.")

if __name__ == "__main__":
    main() 