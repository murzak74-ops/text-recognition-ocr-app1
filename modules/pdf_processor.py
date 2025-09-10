import pdfplumber
import pytesseract
import fitz  # PyMuPDF
from PIL import Image
import io
import numpy as np
from modules.table_extractor import TableExtractor

class PDFProcessor:
    def __init__(self):
        self.table_extractor = TableExtractor()

    def extract_data(self, pdf_path):
        """
        Извлекает данные из PDF файла.
        Пытается сначала получить таблицы и текст напрямую с помощью pdfplumber.
        Если данных мало, конвертирует страницы в изображения и запускает OCR (pytesseract).
        В итоге возвращает список словарей с ключами: Артикул, Наименование, Количество.
        """
        results = []

        # Попытка прямого извлечения таблиц и текста
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        table_data = self.table_extractor.extract_from_table(table)
                        results.extend(table_data)

                    # Если на странице нет таблиц, пытаемся извлечь текст и распарсить
                    if not tables:
                        text = page.extract_text() or ''
                        text_data = self.table_extractor.extract_from_text(text)
                        results.extend(text_data)
        except Exception as e:
            print(f"Ошибка при извлечении с помощью pdfplumber: {e}")

        # Если данных мало, используем OCR
        if len(results) < 3:
            ocr_results = self._extract_with_ocr(pdf_path)
            results.extend(ocr_results)

        return results

    def _extract_with_ocr(self, pdf_path):
        """
        Конвертирует каждую страницу PDF в изображение и выполняет OCR с pytesseract,
        затем извлекает структурированные данные из распознанного текста.
        """
        results = []
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(doc.page_count):
                page = doc[page_num]
                # Масштабируем для улучшения качества OCR
                zoom = 2.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_bytes))

                # Выполняем OCR (русский+английский)
                text = pytesseract.image_to_string(image, lang='rus+eng', config='--psm 6')
                page_results = self.table_extractor.extract_from_text(text)
                results.extend(page_results)

            doc.close()
        except Exception as e:
            print(f"Ошибка OCR при обработке PDF: {e}")

        return results