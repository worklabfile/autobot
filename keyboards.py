"""
Клавиатуры и меню для телеграм бота
"""
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
import database
from config import BRANDS, BODY_TYPES, ENGINE_TYPES, TRANSMISSIONS, PRICE_RANGES

def get_main_menu():
    return ReplyKeyboardMarkup([["Каталог авто"], ["Контакты", "Помощь"]], resize_keyboard=True)

def get_catalog_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Подбор по параметрам", callback_data="filter_params")],
        [InlineKeyboardButton("Смотреть все авто", callback_data="show_all")],
        [InlineKeyboardButton("Назад в главное меню", callback_data="back_to_main_from_catalog")]
    ])

def get_filters_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Марка", callback_data="filter_brand")],
        [InlineKeyboardButton("Тип кузова", callback_data="filter_body")],
        [InlineKeyboardButton("Тип двигателя", callback_data="filter_engine")],
        [InlineKeyboardButton("Коробка передач", callback_data="filter_transmission")],
        [InlineKeyboardButton("Цена", callback_data="filter_price")],
        [InlineKeyboardButton("Смотреть наличие", callback_data="check_availability")],
        [InlineKeyboardButton("Назад", callback_data="back_to_catalog")]
    ])

def get_brands_keyboard():
    """Динамическая клавиатура с марками из доступных автомобилей"""
    data = database.load_data()
    cars = [c for c in data.get("cars", []) if c.get("is_available", True)]

    # Получаем уникальные марки из доступных автомобилей
    available_brands = sorted(set(c.get('brand', '') for c in cars if c.get('brand')))

    if not available_brands:
        available_brands = BRANDS  # Fallback на все марки если нет авто

    kb = [[InlineKeyboardButton(b, callback_data=f"select_brand_{b}")] for b in available_brands]
    kb.append([InlineKeyboardButton("Смотреть наличие", callback_data="check_availability")])
    kb.append([InlineKeyboardButton("Назад", callback_data="back_to_filters")])
    return InlineKeyboardMarkup(kb)

def get_body_types_keyboard():
    """Динамическая клавиатура с типами кузова из доступных автомобилей"""
    data = database.load_data()
    cars = [c for c in data.get("cars", []) if c.get("is_available", True)]

    # Получаем уникальные типы кузова из доступных автомобилей
    available_bodies = sorted(set(c.get('body_type', '') for c in cars if c.get('body_type')))

    if not available_bodies:
        available_bodies = BODY_TYPES  # Fallback

    kb = [[InlineKeyboardButton(b, callback_data=f"select_body_{b}")] for b in available_bodies]
    kb.append([InlineKeyboardButton("Смотреть наличие", callback_data="check_availability")])
    kb.append([InlineKeyboardButton("Назад", callback_data="back_to_filters")])
    return InlineKeyboardMarkup(kb)

def get_engine_types_keyboard():
    """Динамическая клавиатура с типами двигателя из доступных автомобилей"""
    data = database.load_data()
    cars = [c for c in data.get("cars", []) if c.get("is_available", True)]

    # Получаем уникальные типы двигателя из доступных автомобилей
    available_engines = sorted(set(c.get('engine_type', '') for c in cars if c.get('engine_type')))

    if not available_engines:
        available_engines = ENGINE_TYPES  # Fallback

    kb = [[InlineKeyboardButton(e, callback_data=f"select_engine_{e}")] for e in available_engines]
    kb.append([InlineKeyboardButton("Смотреть наличие", callback_data="check_availability")])
    kb.append([InlineKeyboardButton("Назад", callback_data="back_to_filters")])
    return InlineKeyboardMarkup(kb)

def get_transmission_keyboard():
    """Динамическая клавиатура с типами КПП из доступных автомобилей"""
    data = database.load_data()
    cars = [c for c in data.get("cars", []) if c.get("is_available", True)]

    # Получаем уникальные типы КПП из доступных автомобилей
    available_transmissions = sorted(set(c.get('transmission', '') for c in cars if c.get('transmission')))

    if not available_transmissions:
        available_transmissions = TRANSMISSIONS  # Fallback

    kb = [[InlineKeyboardButton(t, callback_data=f"select_transmission_{t}")] for t in available_transmissions]
    kb.append([InlineKeyboardButton("Смотреть наличие", callback_data="check_availability")])
    kb.append([InlineKeyboardButton("Назад", callback_data="back_to_filters")])
    return InlineKeyboardMarkup(kb)

def get_price_ranges_keyboard():
    """Динамическая клавиатура с ценовыми диапазонами"""
    data = database.load_data()
    cars = [c for c in data.get("cars", []) if c.get("is_available", True)]

    if not cars:
        # Если нет автомобилей, показываем все диапазоны
        kb = [[InlineKeyboardButton(p, callback_data=f"select_price_{p}")] for p in PRICE_RANGES]
    else:
        # Определяем, какие диапазоны актуальны
        prices = [c.get('price', 0) for c in cars if c.get('price')]
        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0

        available_ranges = []
        for price_range in PRICE_RANGES:
            # Парсим диапазон
            if "до" in price_range:
                upper = int(price_range.split()[1].replace(',', ''))
                if min_price <= upper:
                    available_ranges.append(price_range)
            elif "от" in price_range and "до" in price_range:
                parts = price_range.split()
                lower = int(parts[1].replace(',', ''))
                upper = int(parts[3].replace(',', ''))
                if not (max_price < lower or min_price > upper):
                    available_ranges.append(price_range)
            elif "от" in price_range:
                lower = int(price_range.split()[1].replace(',', ''))
                if max_price >= lower:
                    available_ranges.append(price_range)

        if not available_ranges:
            available_ranges = PRICE_RANGES  # Fallback

        kb = [[InlineKeyboardButton(p, callback_data=f"select_price_{p}")] for p in available_ranges]

    kb.append([InlineKeyboardButton("Смотреть наличие", callback_data="check_availability")])
    kb.append([InlineKeyboardButton("Назад", callback_data="back_to_filters")])
    return InlineKeyboardMarkup(kb)

def get_availability_keyboard(count):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Смотреть {count} авто", callback_data="view_available_cars")],
        [InlineKeyboardButton("Новый поиск", callback_data="new_search")],
        [InlineKeyboardButton("Назад", callback_data="back_to_filters")]
    ])

def get_car_navigation_keyboard(car_index, total_cars, photo_index=0, total_photos=1):
    kb = []

    # Навигация по фотографиям (если их больше одной)
    if total_photos > 1:
        photo_nav = []
        if photo_index > 0:
            photo_nav.append(InlineKeyboardButton("◀ Фото", callback_data=f"photo_prev_{car_index}_{photo_index-1}"))
        photo_nav.append(InlineKeyboardButton(f"Фото {photo_index+1}/{total_photos}", callback_data="current_photo"))
        if photo_index < total_photos - 1:
            photo_nav.append(InlineKeyboardButton("Фото ▶", callback_data=f"photo_next_{car_index}_{photo_index+1}"))
        kb.append(photo_nav)

    # Навигация по автомобилям
    nav = []
    if car_index > 0:
        nav.append(InlineKeyboardButton("Пред.", callback_data=f"prev_{car_index-1}"))
    nav.append(InlineKeyboardButton(f"{car_index+1}/{total_cars}", callback_data="current"))
    if car_index < total_cars - 1:
        nav.append(InlineKeyboardButton("След.", callback_data=f"next_{car_index+1}"))
    if nav:
        kb.append(nav)

    kb.extend([
        [InlineKeyboardButton("Оставить заявку", callback_data=f"create_application_{car_index}")]
    ])
    return InlineKeyboardMarkup(kb)

def get_contacts_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Оставить заявку", callback_data="create_application")],
        [InlineKeyboardButton("Назад", callback_data="back_to_main")]
    ])

def get_application_cancel():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Отмена", callback_data="cancel_application")]])

def get_application_skip():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Пропустить", callback_data="skip_preferences")],
        [InlineKeyboardButton("Отмена", callback_data="cancel_application")]
    ])

def get_admin_menu():
    """Меню админ-панели"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Добавить автомобиль", callback_data="admin_add_car")],
        [InlineKeyboardButton("Список автомобилей", callback_data="admin_list_cars")],
        [InlineKeyboardButton("Удалить автомобиль", callback_data="admin_delete_car")],
        [InlineKeyboardButton("Управление фото", callback_data="admin_manage_photos")],
        [InlineKeyboardButton("Выход", callback_data="admin_exit")]
    ])
