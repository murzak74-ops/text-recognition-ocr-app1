import streamlit as st
import pandas as pd
import tempfile
import os
from PIL import Image
import pytesseract
import cv2
import numpy as np
import re
from io import BytesIO
from modules.table_extractor import TableExtractor
from modules.excel_exporter import ExcelExporter

# Настройка страницы
st.set_page_config(
    page_title="OCR приложение",
    page_icon="📄",
    layout="wide"
)

class SimpleOCR:
    def __init__(self):
        self.table_extractor = TableExtractor()
    
    def extract_text_from_image(self, image):
        """Извлекает текст из изображения"""
        try:
            # Конвертируем в numpy array
            img_array = np.array(image)
            
            # Конвертируем в градации серого
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Улучшаем контраст
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            
            # OCR с русским языком
            text = pytesseract.image_to_string(enhanced, lang='rus+eng')
            return text
        except Exception as e:
            st.error(f"Ошибка OCR: {e}")
            return ""
    
    def process_image(self, image):
        """Обрабатывает изображение и возвращает структурированные данные"""
        text = self.extract_text_from_image(image)
        if text.strip():
            return self.table_extractor.extract_from_text(text)
        return []

def resize_image_if_needed(image, max_size=(2000, 2000)):
    """Уменьшает размер изображения если необходимо"""
    if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
    return image

def main():
    st.title("📄 Приложение для распознавания текста")
    st.markdown("Извлечение данных из изображений и PDF с помощью OCR")
    
    # Инициализация OCR
    if 'ocr' not in st.session_state:
        st.session_state.ocr = SimpleOCR()
    
    # Боковая панель
    with st.sidebar:
        st.header("⚙️ Настройки")
        st.info("Поддерживаемые форматы: PNG, JPG, JPEG")
        
        # Показываем примеры паттернов
        with st.expander("Примеры распознаваемых данных"):
            st.write("**Артикулы:**")
            st.code("A001-2024, B152-ST, C003")
            st.write("**Количество:**")
            st.code("50 шт, 100 штук, 25 единиц")
            
        # Примеры результатов
        with st.expander("Пример результата"):
            sample_df = pd.DataFrame([
                {"Артикул": "A001-2024", "Наименование": "Болт крепёжный М8х40", "Количество": "50 шт"},
                {"Артикул": "B152-ST", "Наименование": "Гайка шестигранная М10", "Количество": "100 шт"}
            ])
            st.dataframe(sample_df, use_container_width=True)
    
    # Основная область
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📁 Загрузка изображений")
        uploaded_files = st.file_uploader(
            "Выберите изображения",
            accept_multiple_files=True,
            type=['png', 'jpg', 'jpeg'],
            help="Поддерживаются изображения размером до 5MB"
        )
        
        if uploaded_files:
            st.success(f"Загружено файлов: {len(uploaded_files)}")
            
            # Показываем превью
            for i, file in enumerate(uploaded_files[:3]):  # Показываем только первые 3
                image = Image.open(file)
                st.image(image, caption=file.name, width=200)
                if i == 2 and len(uploaded_files) > 3:
                    st.info(f"И еще {len(uploaded_files) - 3} файл(ов)...")
    
    with col2:
        st.header("🔍 Обработка")
        
        if uploaded_files and st.button("🚀 Начать обработку", type="primary"):
            all_results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"Обрабатывается {uploaded_file.name}...")
                
                try:
                    # Открываем и оптимизируем изображение
                    image = Image.open(uploaded_file)
                    image = resize_image_if_needed(image)
                    
                    # Обрабатываем изображение
                    results = st.session_state.ocr.process_image(image)
                    all_results.extend(results)
                
                except Exception as e:
                    st.error(f"Ошибка при обработке {uploaded_file.name}: {e}")
                
                progress_bar.progress((i + 1) / len(uploaded_files))
            
            status_text.text("Обработка завершена!")
            
            # Показываем результаты
            if all_results:
                st.success(f"Найдено позиций: {len(all_results)}")
                
                # Создаем DataFrame
                df = pd.DataFrame(all_results)
                
                # Статистика
                st.header("📊 Статистика")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Всего позиций", len(df))
                with col2:
                    unique_articles = len(df[df['Артикул'] != '']['Артикул'].unique())
                    st.metric("Уникальных артикулов", unique_articles)
                with col3:
                    filled_names = len(df[df['Наименование'] != ''])
                    st.metric("С наименованиями", filled_names)
                
                # Таблица результатов
                st.header("📋 Результаты")
                edited_df = st.data_editor(
                    df,
                    num_rows="dynamic",
                    use_container_width=True,
                    column_config={
                        "Артикул": st.column_config.TextColumn(
                            "Артикул",
                            help="Код товара",
                            max_chars=20,
                        ),
                        "Наименование": st.column_config.TextColumn(
                            "Наименование",
                            help="Название товара",
                            max_chars=100,
                        ),
                        "Количество": st.column_config.TextColumn(
                            "Количество",
                            help="Количество единиц",
                            max_chars=20,
                        )
                    }
                )
                
                # Экспорт в Excel
                if st.button("💾 Подготовить Excel"):
                    try:
                        exporter = ExcelExporter()
                        excel_file = exporter.create_excel_download(edited_df)
                        
                        st.download_button(
                            label="📥 Скачать файл Excel",
                            data=excel_file,
                            file_name="extracted_data.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        st.success("Excel файл готов к скачиванию!")
                    except Exception as e:
                        st.error(f"Ошибка создания Excel: {e}")
            else:
                st.warning("Данные не найдены. Попробуйте изображения лучшего качества с четким текстом.")

if __name__ == "__main__":
    main()