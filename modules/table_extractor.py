import re
import pandas as pd
from typing import List, Dict

class TableExtractor:
    def __init__(self):
        # Паттерны для поиска артикулов, наименований и количества
        self.patterns = {
            'article': [
                r'[A-Za-z0-9]{1,3}[-_]?\d{2,4}[-_]?[A-Za-z]{0,5}',  # A001-2024, B152-ST
                r'[A-Z]\d{2,4}',  # A001, B152
                r'\d{3,6}[-_][A-Za-z]{2,6}',  # 001-PRO
                r'[A-Za-z]{1,2}\d{3,4}[-_]?[A-Za-z]*'  # AB123-XX
            ],
            'quantity': [
                r'\d+\s*шт\.?',
                r'\d+\s*штук',
                r'\d+\s*единиц?',
                r'\d+\s*[мкгт]г',
                r'\d+\s*л',
                r'\d+\s*кг',
                r'\d+\s*м'
            ]
        }
    
    def extract_from_text(self, text):
        """Извлекает структурированные данные из неструктурированного текста"""
        results = []
        
        # Разбиваем текст на строки
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 3:
                continue
            
            # Пропускаем строки с заголовками
            if any(word in line.lower() for word in ['артикул', 'наименование', 'количество', 'товар', 'позиция']):
                continue
                
            # Ищем паттерны в строке
            article = self._extract_article(line)
            quantity = self._extract_quantity(line)
            
            # Если найден хотя бы артикул или количество
            if article or quantity or self._looks_like_product_line(line):
                # Определяем наименование (все, что не артикул и не количество)
                name = self._extract_name(line, article, quantity)
                
                # Добавляем только если есть содержательная информация
                if article or (name and len(name) > 2):
                    results.append({
                        'Артикул': article,
                        'Наименование': name,
                        'Количество': quantity
                    })
        
        return results
    
    def _looks_like_product_line(self, line):
        """Проверяет, похожа ли строка на описание товара"""
        # Ищем характерные слова для товаров
        product_keywords = [
            'болт', 'гайка', 'винт', 'шайба', 'дюбель', 'саморез', 'скоба',
            'крепеж', 'метиз', 'деталь', 'запчасть', 'изделие'
        ]
        
        line_lower = line.lower()
        return any(keyword in line_lower for keyword in product_keywords)
    
    def _extract_article(self, text):
        """Извлекает артикул из текста"""
        for pattern in self.patterns['article']:
            match = re.search(pattern, text)
            if match:
                candidate = match.group().strip()
                # Проверяем, что это не просто число (год, размер и т.д.)
                if len(candidate) >= 3 and not candidate.isdigit():
                    return candidate
        return ''
    
    def _extract_quantity(self, text):
        """Извлекает количество из текста"""
        for pattern in self.patterns['quantity']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group().strip()
        
        # Дополнительный поиск просто чисел в конце строки
        number_at_end = re.search(r'\b\d+\s*$', text)
        if number_at_end:
            return number_at_end.group().strip() + ' шт'
            
        return ''
    
    def _extract_name(self, text, article='', quantity=''):
        """Извлекает наименование из текста"""
        name = text
        
        # Удаляем артикул и количество из текста
        if article:
            name = name.replace(article, '')
        
        if quantity:
            name = name.replace(quantity, '')
        
        # Убираем лишние пробелы и символы
        name = re.sub(r'\s+', ' ', name).strip()
        name = name.strip('.,;:-_|')
        
        # Убираем начальные цифры (номера строк)
        name = re.sub(r'^\d+\s*\.?\s*', '', name)
        
        # Убираем очень короткие наименования
        if len(name) < 3:
            return ''
            
        return name
    
    def extract_from_table(self, table):
        """Извлекает данные из таблицы (список списков)"""
        results = []
        
        if not table or len(table) < 2:
            return results
        
        # Ищем заголовки
        header_row = self._find_header_row(table)
        if header_row is None:
            header_row = 0
        
        # Определяем индексы колонок
        col_indices = self._find_column_indices(table[header_row])
        
        # Извлекаем данные из строк
        for i in range(header_row + 1, len(table)):
            row = table[i]
            if not row or all(cell is None or str(cell).strip() == '' for cell in row):
                continue
                
            row_data = self._extract_row_data(row, col_indices)
            if row_data:
                results.append(row_data)
        
        return results
    
    def _find_header_row(self, table):
        """Находит строку с заголовками"""
        keywords = ['артикул', 'наименование', 'количество', 'код', 'название', 'кол-во', 'товар']
        
        for i, row in enumerate(table):
            if not row:
                continue
                
            row_text = ' '.join(str(cell).lower() for cell in row if cell)
            
            matches = sum(1 for keyword in keywords if keyword in row_text)
            if matches >= 2:
                return i
        
        return 0  # Если не найдено, используем первую строку
    
    def _find_column_indices(self, header_row):
        """Определяет индексы колонок"""
        indices = {'article': -1, 'name': -1, 'quantity': -1}
        
        for i, cell in enumerate(header_row):
            if not cell:
                continue
                
            cell_lower = str(cell).lower()
            
            if any(word in cell_lower for word in ['артикул', 'код']):
                indices['article'] = i
            elif any(word in cell_lower for word in ['наименование', 'название', 'товар']):
                indices['name'] = i
            elif any(word in cell_lower for word in ['количество', 'кол-во', 'штук']):
                indices['quantity'] = i
        
        return indices
    
    def _extract_row_data(self, row, col_indices):
        """Извлекает данные из строки таблицы"""
        if not row:
            return None
        
        # Получаем значения по индексам
        article = ''
        name = ''
        quantity = ''
        
        if col_indices['article'] >= 0 and col_indices['article'] < len(row):
            article = str(row[col_indices['article']] or '').strip()
            
        if col_indices['name'] >= 0 and col_indices['name'] < len(row):
            name = str(row[col_indices['name']] or '').strip()
            
        if col_indices['quantity'] >= 0 and col_indices['quantity'] < len(row):
            quantity = str(row[col_indices['quantity']] or '').strip()
        
        # Если индексы не найдены, пытаемся извлечь из всей строки
        if not article:
            article = self._extract_article(' '.join(str(cell) for cell in row if cell))
        
        if not name and article:
            full_text = ' '.join(str(cell) for cell in row if cell)
            name = self._extract_name(full_text, article, quantity)
        
        if not quantity:
            quantity = self._extract_quantity(' '.join(str(cell) for cell in row if cell))
        
        if article or name:
            return {
                'Артикул': article,
                'Наименование': name,
                'Количество': quantity
            }
        
        return None
