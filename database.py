"""
Функции для работы с базой данных автомобилей
"""
import json
import os
from config import CARS_FILE

def load_data():
    """Загрузка данных из JSON"""
    if os.path.exists(CARS_FILE):
        try:
            with open(CARS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"cars": [], "contacts": {}}
    return {"cars": [], "contacts": {}}

def save_data(data):
    """Сохранение данных в JSON"""
    with open(CARS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_cars(filters=None):
    """Получение автомобилей с фильтрацией"""
    data = load_data()
    cars = [car for car in data["cars"] if car.get("is_available", True)]

    if not filters:
        return cars

    filtered = []
    for car in cars:
        match = True
        if filters.get('brand') and car.get('brand') != filters['brand']:
            match = False
        if filters.get('body_type') and car.get('body_type') != filters['body_type']:
            match = False
        if filters.get('engine_type') and car.get('engine_type') != filters['engine_type']:
            match = False
        if filters.get('transmission') and car.get('transmission') != filters['transmission']:
            match = False
        if filters.get('price_range'):
            price = car.get('price', 0)
            pr = filters['price_range']
            if pr == "До 5000 $" and price > 5000:
                match = False
            elif pr == "5000 - 10000 $" and (price < 5000 or price > 10000):
                match = False
            elif pr == "10000 - 20000 $" and (price < 10000 or price > 20000):
                match = False
            elif pr == "20000 - 50000 $" and (price < 20000 or price > 50000):
                match = False
            elif pr == "Свыше 50000 $" and price < 50000:
                match = False
        if match:
            filtered.append(car)
    return filtered
