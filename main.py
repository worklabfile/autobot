"""
Telegram бот для автосалона
Все в одном файле для простоты
"""
import json
import os
import logging
import copy
import requests
from io import BytesIO
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler, ContextTypes
from telegram.constants import ParseMode
from config import BOT_TOKEN, ADMIN_ID, BRANDS, BODY_TYPES, ENGINE_TYPES, TRANSMISSIONS, PRICE_RANGES

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# База данных
CARS_FILE = "data/datacars.json"
PHOTOS_DIR = "data/photos"

def ensure_photos_dir():
    """Создает папку для фотографий если её нет"""
    if not os.path.exists(PHOTOS_DIR):
        os.makedirs(PHOTOS_DIR)

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

def get_next_car_id():
    """Получение следующего ID для автомобиля"""
    data = load_data()
    cars = data.get("cars", [])
    if not cars:
        return 1
    return max(car.get("id", 0) for car in cars) + 1

def download_image_from_url(url, car_id, photo_index):
    """Скачивает изображение по URL и сохраняет локально"""
    try:
        ensure_photos_dir()
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Определяем расширение файла
        content_type = response.headers.get('content-type', '')
        if 'jpeg' in content_type or 'jpg' in content_type:
            ext = '.jpg'
        elif 'png' in content_type:
            ext = '.png'
        elif 'webp' in content_type:
            ext = '.webp'
        else:
            ext = '.jpg'  # По умолчанию
        
        filename = f"car_{car_id}_{photo_index}{ext}"
        filepath = os.path.join(PHOTOS_DIR, filename)
        
        # Сохраняем файл
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"Изображение скачано: {url} -> {filepath}")
        return filename
    except Exception as e:
        logger.error(f"Ошибка скачивания изображения {url}: {e}")
        return None

async def safe_edit_message_text(query, text, reply_markup=None, parse_mode=None):
    """Безопасное редактирование сообщения с обработкой медиа"""
    try:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        # Если не получилось отредактировать (например, сообщение с медиа), удаляем и отправляем новое
        logger.warning(f"Не удалось отредактировать сообщение, отправляем новое: {e}")
        try:
            await query.message.delete()
        except:
            pass
        # Получаем bot из query
        bot = query.message.get_bot()
        await bot.send_message(
            chat_id=query.message.chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )

def is_admin(user_id, username=None):
    """Проверка, является ли пользователь админом"""
    if isinstance(ADMIN_ID, str) and ADMIN_ID.startswith("@"):
        # Если ADMIN_ID это username
        return username and username.lower() == ADMIN_ID[1:].lower()
    try:
        admin_id_int = int(ADMIN_ID) if isinstance(ADMIN_ID, str) else ADMIN_ID
        return user_id == admin_id_int
    except:
        return False

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
            if pr == "До 5000 BYN" and price > 5000:
                match = False
            elif pr == "5000 - 10000 BYN" and (price < 5000 or price > 10000):
                match = False
            elif pr == "10000 - 20000 BYN" and (price < 10000 or price > 20000):
                match = False
            elif pr == "20000 - 50000 BYN" and (price < 20000 or price > 50000):
                match = False
            elif pr == "Свыше 50000 BYN" and price < 50000:
                match = False
        if match:
            filtered.append(car)
    return filtered

# Клавиатуры
def get_main_menu():
    return ReplyKeyboardMarkup([["🚗 Каталог авто"], ["📞 Контакты", "🆘 Помощь"]], resize_keyboard=True)

def get_catalog_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎛 Подбор по параметрам", callback_data="filter_params")],
        [InlineKeyboardButton("📋 Смотреть все авто", callback_data="show_all")],
        [InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="back_to_main_from_catalog")]
    ])

def get_filters_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏷 Марка", callback_data="filter_brand")],
        [InlineKeyboardButton("🚙 Тип кузова", callback_data="filter_body")],
        [InlineKeyboardButton("⚙️ Тип двигателя", callback_data="filter_engine")],
        [InlineKeyboardButton("🔧 Коробка передач", callback_data="filter_transmission")],
        [InlineKeyboardButton("💰 Цена", callback_data="filter_price")],
        [InlineKeyboardButton("📊 Смотреть наличие", callback_data="check_availability")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_catalog")]
    ])

def get_brands_keyboard():
    """Динамическая клавиатура с марками из доступных автомобилей"""
    data = load_data()
    cars = [c for c in data.get("cars", []) if c.get("is_available", True)]
    
    # Получаем уникальные марки из доступных автомобилей
    available_brands = sorted(set(c.get('brand', '') for c in cars if c.get('brand')))
    
    if not available_brands:
        available_brands = BRANDS  # Fallback на все марки если нет авто
    
    kb = [[InlineKeyboardButton(b, callback_data=f"select_brand_{b}")] for b in available_brands]
    kb.append([InlineKeyboardButton("📊 Смотреть наличие", callback_data="check_availability")])
    kb.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_filters")])
    return InlineKeyboardMarkup(kb)

def get_body_types_keyboard():
    """Динамическая клавиатура с типами кузова из доступных автомобилей"""
    data = load_data()
    cars = [c for c in data.get("cars", []) if c.get("is_available", True)]
    
    # Получаем уникальные типы кузова из доступных автомобилей
    available_bodies = sorted(set(c.get('body_type', '') for c in cars if c.get('body_type')))
    
    if not available_bodies:
        available_bodies = BODY_TYPES  # Fallback
    
    kb = [[InlineKeyboardButton(b, callback_data=f"select_body_{b}")] for b in available_bodies]
    kb.append([InlineKeyboardButton("📊 Смотреть наличие", callback_data="check_availability")])
    kb.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_filters")])
    return InlineKeyboardMarkup(kb)

def get_engine_types_keyboard():
    """Динамическая клавиатура с типами двигателя из доступных автомобилей"""
    data = load_data()
    cars = [c for c in data.get("cars", []) if c.get("is_available", True)]
    
    # Получаем уникальные типы двигателя из доступных автомобилей
    available_engines = sorted(set(c.get('engine_type', '') for c in cars if c.get('engine_type')))
    
    if not available_engines:
        available_engines = ENGINE_TYPES  # Fallback
    
    kb = [[InlineKeyboardButton(e, callback_data=f"select_engine_{e}")] for e in available_engines]
    kb.append([InlineKeyboardButton("📊 Смотреть наличие", callback_data="check_availability")])
    kb.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_filters")])
    return InlineKeyboardMarkup(kb)

def get_transmission_keyboard():
    """Динамическая клавиатура с типами КПП из доступных автомобилей"""
    data = load_data()
    cars = [c for c in data.get("cars", []) if c.get("is_available", True)]
    
    # Получаем уникальные типы КПП из доступных автомобилей
    available_transmissions = sorted(set(c.get('transmission', '') for c in cars if c.get('transmission')))
    
    if not available_transmissions:
        available_transmissions = TRANSMISSIONS  # Fallback
    
    kb = [[InlineKeyboardButton(t, callback_data=f"select_transmission_{t}")] for t in available_transmissions]
    kb.append([InlineKeyboardButton("📊 Смотреть наличие", callback_data="check_availability")])
    kb.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_filters")])
    return InlineKeyboardMarkup(kb)

def get_price_ranges_keyboard():
    """Динамическая клавиатура с ценовыми диапазонами"""
    data = load_data()
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
    
    kb.append([InlineKeyboardButton("📊 Смотреть наличие", callback_data="check_availability")])
    kb.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_filters")])
    return InlineKeyboardMarkup(kb)

def get_availability_keyboard(count):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ Смотреть {count} авто", callback_data="view_available_cars")],
        [InlineKeyboardButton("🔄 Новый поиск", callback_data="new_search")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_filters")]
    ])

def get_car_navigation_keyboard(car_index, total_cars, photo_index=0, total_photos=1):
    kb = []
    
    # Навигация по фотографиям (если их больше одной)
    if total_photos > 1:
        photo_nav = []
        if photo_index > 0:
            photo_nav.append(InlineKeyboardButton("◀️ Фото", callback_data=f"photo_prev_{car_index}_{photo_index-1}"))
        photo_nav.append(InlineKeyboardButton(f"📷 {photo_index+1}/{total_photos}", callback_data="current_photo"))
        if photo_index < total_photos - 1:
            photo_nav.append(InlineKeyboardButton("Фото ▶️", callback_data=f"photo_next_{car_index}_{photo_index+1}"))
        kb.append(photo_nav)
    
    # Навигация по автомобилям
    nav = []
    if car_index > 0:
        nav.append(InlineKeyboardButton("⬅️ Пред.", callback_data=f"prev_{car_index-1}"))
    nav.append(InlineKeyboardButton(f"🚗 {car_index+1}/{total_cars}", callback_data="current"))
    if car_index < total_cars - 1:
        nav.append(InlineKeyboardButton("След. ➡️", callback_data=f"next_{car_index+1}"))
    if nav:
        kb.append(nav)
    
    kb.extend([
        [InlineKeyboardButton("📞 Оставить заявку", callback_data="create_application")],
        [InlineKeyboardButton("⬅️ Назад к каталогу", callback_data="back_to_catalog")]
    ])
    return InlineKeyboardMarkup(kb)

def get_contacts_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📞 Оставить заявку", callback_data="create_application")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
    ])

def get_application_cancel():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="cancel_application")]])

# Обработчики
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Добро пожаловать, {user.first_name}!\n\n🚗 Добро пожаловать в автосалон AutoHouse!\n\nВыберите нужный раздел:",
        reply_markup=get_main_menu()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 Помощь\n\n• 🚗 Каталог авто - подбор автомобиля по параметрам\n• 📞 Контакты - свяжитесь с нами\n\nДля начала работы нажмите «🚗 Каталог авто»",
        reply_markup=get_main_menu()
    )

async def show_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    text = "🚗 Каталог автомобилей\n\nВыберите способ поиска:"
    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(text, reply_markup=get_catalog_menu())
    else:
        await update.callback_query.edit_message_text(text, reply_markup=get_catalog_menu())

async def show_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    contacts = data.get("contacts", {})
    text = f"""📞 Контакты автосалона

📱 Телефон: {contacts.get('phone', 'не указан')}
💬 WhatsApp: {contacts.get('whatsapp', 'не указан')}
📧 Email: {contacts.get('email', 'не указан')}

🏢 Адрес: {contacts.get('address', 'не указан')}
🕒 График работы: {contacts.get('work_hours', 'не указан')}

Свяжитесь с нами или оставьте заявку! 🚗"""
    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(text, reply_markup=get_contacts_keyboard())
    else:
        await update.callback_query.edit_message_text(text, reply_markup=get_contacts_keyboard())

async def show_filter_params(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await safe_edit_message_text(query, "🎛 Подбор по параметрам\n\nВыберите параметр для фильтрации:", reply_markup=get_filters_menu())

async def show_all_cars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cars = get_cars()
    if not cars:
        await safe_edit_message_text(query, "На данный момент нет доступных автомобилей.")
        return
    context.user_data['current_cars'] = cars
    context.user_data['current_index'] = 0
    await show_car(query, context, 0)

async def show_car(update, context: ContextTypes.DEFAULT_TYPE, index: int, photo_index: int = 0):
    cars = context.user_data.get('current_cars', [])
    if not cars or index >= len(cars):
        if hasattr(update, 'edit_message_text'):
            await update.edit_message_text("Автомобиль не найден")
        return
    car = cars[index]
    
    # Получаем список фотографий
    photos = car.get('photos', [])
    if isinstance(photos, str):
        photos = [photos]
    
    # Фильтруем только существующие фотографии
    valid_photos = []
    for photo in photos:
        if isinstance(photo, str):
            valid_photos.append(photo)
    
    total_photos = len(valid_photos)
    
    # Проверяем корректность индекса фотографии
    if photo_index >= total_photos:
        photo_index = 0
    
    caption = f"""🚗 *{car['brand']} {car['model']}*

📅 Год: {car['year']}
💰 Цена: *{car['price']:,} BYN*
🎨 Цвет: {car.get('color', 'не указан')}
📏 Пробег: {car.get('mileage', 0):,} км
⚙️ Двигатель: {car['engine_type']}, {car.get('engine_volume', 0)} л
🔧 КПП: {car['transmission']}
🏷 Кузов: {car['body_type']}

📝 *{car.get('description', 'Описание отсутствует')}*

🎯 *Особенности:*
{chr(10).join(['• ' + f for f in car.get('features', [])])}"""
    
    # Определяем, является ли update callback_query
    query = update if hasattr(update, 'edit_message_media') else None
    
    if valid_photos and photo_index < len(valid_photos):
        photo_path = valid_photos[photo_index]
        
        # Проверяем, это локальный файл или URL
        if photo_path.startswith('http'):
            # Это URL - скачиваем и сохраняем локально
            logger.info(f"Обнаружен URL фото: {photo_path}, скачиваем...")
            downloaded_filename = download_image_from_url(photo_path, car['id'], 1)
            
            if downloaded_filename:
                # Обновляем данные в JSON
                data = load_data()
                for c in data.get("cars", []):
                    if c.get("id") == car['id']:
                        if isinstance(c.get('photos'), list):
                            # Заменяем URL на локальный файл
                            for i, p in enumerate(c['photos']):
                                if p == photo_path:
                                    c['photos'][i] = downloaded_filename
                                    break
                        save_data(data)
                        logger.info(f"Обновлен JSON: URL заменен на {downloaded_filename}")
                        break
                
                photo_source = os.path.join(PHOTOS_DIR, downloaded_filename)
            else:
                # Не удалось скачать, используем placeholder
                logger.warning(f"Не удалось скачать изображение по URL: {photo_path}, используем placeholder")
                photo_source = os.path.join(PHOTOS_DIR, "placeholder.jpg")
                # Продолжаем с placeholder вместо возврата
        else:
            # Это локальный файл
            photo_source = os.path.join(PHOTOS_DIR, photo_path) if not os.path.isabs(photo_path) else photo_path
            if not os.path.exists(photo_source):
                logger.warning(f"Файл не найден: {photo_source}, используем placeholder")
                photo_source = os.path.join(PHOTOS_DIR, "placeholder.jpg")
                # Продолжаем с placeholder
        
        logger.info(f"Отправка фото для автомобиля {car['id']}: {photo_source}")
        
        # Проверяем, есть ли сохраненный file_id для этого фото
        photo_cache_key = f"photo_{car['id']}_{photo_index}"
        cached_file_id = context.bot_data.get(photo_cache_key)
        
        try:
            if query:
                # Пытаемся отредактировать медиа (если предыдущее сообщение было медиа)
                if cached_file_id:
                    # Используем кэшированный file_id для быстрой отправки
                    media = InputMediaPhoto(media=cached_file_id, caption=caption, parse_mode=ParseMode.MARKDOWN)
                    await query.edit_message_media(media=media, reply_markup=get_car_navigation_keyboard(index, len(cars), photo_index, total_photos))
                else:
                    # Открываем файл и отправляем
                    with open(photo_source, 'rb') as photo_file:
                        media = InputMediaPhoto(media=photo_file, caption=caption, parse_mode=ParseMode.MARKDOWN)
                        result = await query.edit_message_media(media=media, reply_markup=get_car_navigation_keyboard(index, len(cars), photo_index, total_photos))
                        # Сохраняем file_id для будущего использования
                        if result.photo:
                            context.bot_data[photo_cache_key] = result.photo[-1].file_id
            else:
                # Если это не callback_query, отправляем новое сообщение с фото
                with open(photo_source, 'rb') as photo_file:
                    result = await update.message.reply_photo(
                        photo=photo_file,
                        caption=caption,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=get_car_navigation_keyboard(index, len(cars), photo_index, total_photos)
                    )
                    # Сохраняем file_id
                    if result.photo:
                        context.bot_data[photo_cache_key] = result.photo[-1].file_id
        except Exception as e:
            # Если edit_message_media не работает (например, предыдущее сообщение было текстовым),
            # отправляем новое сообщение с фото
            logger.warning(f"Не удалось отредактировать медиа, пробуем отправить новое сообщение: {e}")
            try:
                if query:
                    # Отправляем новое сообщение с фото
                    chat_id = query.message.chat_id
                    bot = context.bot
                    
                    if cached_file_id:
                        # Используем кэш
                        result = await bot.send_photo(
                            chat_id=chat_id,
                            photo=cached_file_id,
                            caption=caption,
                            parse_mode=ParseMode.MARKDOWN,
                            reply_markup=get_car_navigation_keyboard(index, len(cars), photo_index, total_photos)
                        )
                    else:
                        # Загружаем файл
                        with open(photo_source, 'rb') as photo_file:
                            result = await bot.send_photo(
                                chat_id=chat_id,
                                photo=photo_file,
                                caption=caption,
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=get_car_navigation_keyboard(index, len(cars), photo_index, total_photos)
                            )
                            # Сохраняем file_id
                            if result.photo:
                                context.bot_data[photo_cache_key] = result.photo[-1].file_id
                    
                    # Пытаемся удалить старое сообщение (если возможно)
                    try:
                        await query.message.delete()
                    except:
                        pass  # Игнорируем ошибку удаления
                else:
                    with open(photo_source, 'rb') as photo_file:
                        result = await update.message.reply_photo(
                            photo=photo_file,
                            caption=caption,
                            parse_mode=ParseMode.MARKDOWN,
                            reply_markup=get_car_navigation_keyboard(index, len(cars), photo_index, total_photos)
                        )
                        # Сохраняем file_id
                        if result.photo:
                            context.bot_data[photo_cache_key] = result.photo[-1].file_id
            except Exception as e2:
                # Если и это не сработало, отправляем текст
                logger.error(f"Ошибка отправки фото {photo_source}: {e2}")
                if query:
                    # Удаляем старое сообщение и отправляем новое
                    try:
                        await query.message.delete()
                    except:
                        pass
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=caption,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=get_car_navigation_keyboard(index, len(cars), photo_index, total_photos)
                    )
                else:
                    await update.message.reply_text(caption, parse_mode=ParseMode.MARKDOWN, reply_markup=get_car_navigation_keyboard(index, len(cars), photo_index, total_photos))
    else:
        # Если фото нет, используем placeholder для плавного переключения
        logger.info(f"У автомобиля {car['id']} нет фото, используем placeholder")
        photo_source = os.path.join(PHOTOS_DIR, "placeholder.jpg")
        photo_cache_key = f"photo_placeholder"
        cached_file_id = context.bot_data.get(photo_cache_key)
        
        try:
            if query:
                # Пытаемся отредактировать медиа
                if cached_file_id:
                    media = InputMediaPhoto(media=cached_file_id, caption=caption, parse_mode=ParseMode.MARKDOWN)
                    await query.edit_message_media(media=media, reply_markup=get_car_navigation_keyboard(index, len(cars), 0, 0))
                else:
                    with open(photo_source, 'rb') as photo_file:
                        media = InputMediaPhoto(media=photo_file, caption=caption, parse_mode=ParseMode.MARKDOWN)
                        result = await query.edit_message_media(media=media, reply_markup=get_car_navigation_keyboard(index, len(cars), 0, 0))
                        if result.photo:
                            context.bot_data[photo_cache_key] = result.photo[-1].file_id
            else:
                with open(photo_source, 'rb') as photo_file:
                    result = await update.message.reply_photo(
                        photo=photo_file,
                        caption=caption,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=get_car_navigation_keyboard(index, len(cars), 0, 0)
                    )
                    if result.photo:
                        context.bot_data[photo_cache_key] = result.photo[-1].file_id
        except Exception as e:
            # Если не получилось с placeholder, отправляем текст
            logger.error(f"Ошибка отправки placeholder: {e}")
            if query:
                try:
                    await query.message.delete()
                except:
                    pass
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=caption,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=get_car_navigation_keyboard(index, len(cars), 0, 0)
                )
            else:
                await update.message.reply_text(caption, parse_mode=ParseMode.MARKDOWN, reply_markup=get_car_navigation_keyboard(index, len(cars), 0, 0))

async def filter_brand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await safe_edit_message_text(query, "🏷 Выберите марку автомобиля:", reply_markup=get_brands_keyboard())

async def filter_body(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await safe_edit_message_text(query, "🚙 Выберите тип кузова:", reply_markup=get_body_types_keyboard())

async def filter_engine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await safe_edit_message_text(query, "⚙️ Выберите тип двигателя:", reply_markup=get_engine_types_keyboard())

async def filter_transmission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await safe_edit_message_text(query, "🔧 Выберите коробку передач:", reply_markup=get_transmission_keyboard())

async def filter_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await safe_edit_message_text(query, "💰 Выберите ценовой диапазон:", reply_markup=get_price_ranges_keyboard())

async def handle_filter_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if 'filters' not in context.user_data:
        context.user_data['filters'] = {}
    if data.startswith('select_brand_'):
        context.user_data['filters']['brand'] = data.replace('select_brand_', '')
        text = f"✅ Выбрана марка: {context.user_data['filters']['brand']}\n\nВыберите следующий параметр или проверьте наличие:"
    elif data.startswith('select_body_'):
        context.user_data['filters']['body_type'] = data.replace('select_body_', '')
        text = f"✅ Выбран кузов: {context.user_data['filters']['body_type']}\n\nВыберите следующий параметр или проверьте наличие:"
    elif data.startswith('select_engine_'):
        context.user_data['filters']['engine_type'] = data.replace('select_engine_', '')
        text = f"✅ Выбран двигатель: {context.user_data['filters']['engine_type']}\n\nВыберите следующий параметр или проверьте наличие:"
    elif data.startswith('select_transmission_'):
        context.user_data['filters']['transmission'] = data.replace('select_transmission_', '')
        text = f"✅ Выбрана КПП: {context.user_data['filters']['transmission']}\n\nВыберите следующий параметр или проверьте наличие:"
    elif data.startswith('select_price_'):
        context.user_data['filters']['price_range'] = data.replace('select_price_', '')
        text = f"✅ Выбран ценовой диапазон: {context.user_data['filters']['price_range']}\n\nВыберите следующий параметр или проверьте наличие:"
    else:
        return
    await safe_edit_message_text(query, text, reply_markup=get_filters_menu())

async def check_availability(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    filters = context.user_data.get('filters', {})
    count = len(get_cars(filters))
    filters_text = "Текущие фильтры:\n"
    if filters.get('brand'):
        filters_text += f"• Марка: {filters['brand']}\n"
    if filters.get('body_type'):
        filters_text += f"• Кузов: {filters['body_type']}\n"
    if filters.get('engine_type'):
        filters_text += f"• Двигатель: {filters['engine_type']}\n"
    if filters.get('transmission'):
        filters_text += f"• КПП: {filters['transmission']}\n"
    if filters.get('price_range'):
        filters_text += f"• Цена: {filters['price_range']}\n"
    if not filters:
        filters_text = "Фильтры не установлены\n"
    await safe_edit_message_text(query, f"📊 Проверка наличия\n\n{filters_text}\n✅ Доступно {count} авто", reply_markup=get_availability_keyboard(count))

async def view_available_cars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    filters = context.user_data.get('filters', {})
    cars = get_cars(filters)
    if not cars:
        await safe_edit_message_text(query, "По вашим параметрам не найдено доступных автомобилей.")
        return
    context.user_data['current_cars'] = cars
    context.user_data['current_index'] = 0
    await show_car(query, context, 0)

async def new_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['filters'] = {}
    await safe_edit_message_text(query, "🔄 Новый поиск\n\nВыберите параметр для фильтрации:", reply_markup=get_filters_menu())

async def handle_car_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith('prev_'):
        await show_car(query, context, int(query.data.split('_')[1]), 0)
    elif query.data.startswith('next_'):
        await show_car(query, context, int(query.data.split('_')[1]), 0)
    elif query.data.startswith('photo_prev_'):
        parts = query.data.split('_')
        car_index = int(parts[2])
        photo_index = int(parts[3])
        await show_car(query, context, car_index, photo_index)
    elif query.data.startswith('photo_next_'):
        parts = query.data.split('_')
        car_index = int(parts[2])
        photo_index = int(parts[3])
        await show_car(query, context, car_index, photo_index)
    elif query.data == 'back_to_catalog':
        await show_catalog(query, context)

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_text("Главное меню:", reply_markup=get_main_menu())
    except Exception as e:
        # Если не получилось отредактировать (например, сообщение с медиа), удаляем и отправляем новое
        logger.warning(f"Не удалось отредактировать сообщение: {e}")
        try:
            await query.message.delete()
        except:
            pass
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Главное меню:",
            reply_markup=get_main_menu()
        )

async def back_to_main_from_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_text("Главное меню:", reply_markup=get_main_menu())
    except Exception as e:
        # Если не получилось отредактировать (например, сообщение с медиа), удаляем и отправляем новое
        logger.warning(f"Не удалось отредактировать сообщение: {e}")
        try:
            await query.message.delete()
        except:
            pass
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Главное меню:",
            reply_markup=get_main_menu()
        )

async def back_to_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await show_filter_params(update, context)

NAME, PHONE, PREFERENCES = range(3)

async def start_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await safe_edit_message_text(query, "📋 Оставить заявку\n\nПожалуйста, укажите ваше имя:", reply_markup=get_application_cancel())
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['application_name'] = update.message.text
    await update.message.reply_text("📞 Теперь укажите ваш номер телефона:", reply_markup=get_application_cancel())
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['application_phone'] = update.message.text
    await update.message.reply_text("💭 Укажите ваши предпочтения по автомобилю или имеющиеся вопросы:", reply_markup=get_application_cancel())
    return PREFERENCES

async def get_preferences(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['application_preferences'] = update.message.text
    user = update.effective_user
    app_data = context.user_data
    application_text = f"""📋 *Новая заявка от пользователя*

👤 *Имя:* {app_data['application_name']}
📞 *Телефон:* {app_data['application_phone']}
💭 *Предпочтения/вопросы:* {app_data['application_preferences']}

👤 *Профиль:* {user.first_name} {user.last_name or ''}
🆔 ID: {user.id}
📱 Username: @{user.username or 'не указан'}"""
    try:
        await update.message.bot.send_message(chat_id=ADMIN_ID, text=application_text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Ошибка отправки заявки: {e}")
    await update.message.reply_text("✅ *Спасибо за ваше обращение!*\n\nВ ближайшее время менеджер с вами свяжется для уточнения деталей.\n\nХорошего дня! 😊", parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_menu())
    context.user_data.pop('application_name', None)
    context.user_data.pop('application_phone', None)
    context.user_data.pop('application_preferences', None)
    return ConversationHandler.END

async def cancel_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.pop('application_name', None)
    context.user_data.pop('application_phone', None)
    context.user_data.pop('application_preferences', None)
    await safe_edit_message_text(query, "Заявка отменена.", reply_markup=get_main_menu())
    return ConversationHandler.END

# ========== АДМИН-ПАНЕЛЬ ==========

def get_admin_menu():
    """Меню админ-панели"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Добавить автомобиль", callback_data="admin_add_car")],
        [InlineKeyboardButton("📋 Список автомобилей", callback_data="admin_list_cars")],
        [InlineKeyboardButton("🗑 Удалить автомобиль", callback_data="admin_delete_car")],
        [InlineKeyboardButton("📸 Управление фото", callback_data="admin_manage_photos")],
        [InlineKeyboardButton("⬅️ Выход", callback_data="admin_exit")]
    ])

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /admin для входа в админ-панель"""
    user = update.effective_user
    if not is_admin(user.id, user.username):
        await update.message.reply_text("❌ У вас нет доступа к админ-панели.")
        return
    
    ensure_photos_dir()
    await update.message.reply_text(
        "🔐 *Админ-панель*\n\nВыберите действие:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_admin_menu()
    )

async def admin_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик админ-меню"""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    
    if not is_admin(user.id, user.username):
        await safe_edit_message_text(query, "❌ У вас нет доступа к админ-панели.")
        return
    
    # admin_add_car обрабатывается через ConversationHandler
    
    elif query.data == "admin_list_cars":
        data = load_data()
        cars = data.get("cars", [])
        if not cars:
            await safe_edit_message_text(query, "📋 Список пуст.", reply_markup=get_admin_menu())
            return
        
        text = "📋 *Список автомобилей:*\n\n"
        for car in cars[:10]:  # Показываем первые 10
            status = "✅" if car.get("is_available", True) else "❌"
            text += f"{status} *{car.get('id')}.* {car.get('brand')} {car.get('model')} - {car.get('price', 0):,} BYN\n"
        
        if len(cars) > 10:
            text += f"\n... и еще {len(cars) - 10} автомобилей"
        
        await safe_edit_message_text(query, text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_admin_menu())
    
    elif query.data == "admin_delete_car":
        data = load_data()
        cars = data.get("cars", [])
        if not cars:
            await safe_edit_message_text(query, "📋 Список пуст.", reply_markup=get_admin_menu())
            return
        
        kb = []
        for car in cars:
            kb.append([InlineKeyboardButton(
                f"🗑 {car.get('brand')} {car.get('model')} (ID: {car.get('id')})",
                callback_data=f"admin_delete_{car.get('id')}"
            )])
        kb.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_back")])
        
        await safe_edit_message_text(
            query,
            "🗑 *Удаление автомобиля*\n\nВыберите автомобиль для удаления:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(kb)
        )
    
    elif query.data == "admin_manage_photos":
        data = load_data()
        cars = data.get("cars", [])
        if not cars:
            await safe_edit_message_text(query, "📋 Список пуст.", reply_markup=get_admin_menu())
            return
        
        kb = []
        for car in cars:
            photo_count = len(car.get('photos', []))
            kb.append([InlineKeyboardButton(
                f"📸 {car.get('brand')} {car.get('model')} ({photo_count} фото)",
                callback_data=f"admin_photos_{car.get('id')}"
            )])
        kb.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_back")])
        
        await safe_edit_message_text(
            query,
            "📸 *Управление фотографиями*\n\nВыберите автомобиль:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(kb)
        )
    
    elif query.data == "admin_exit":
        await safe_edit_message_text(query, "✅ Выход из админ-панели.", reply_markup=get_main_menu())
    
    elif query.data == "admin_back":
        await safe_edit_message_text(
            query,
            "🔐 *Админ-панель*\n\nВыберите действие:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_admin_menu()
        )

async def admin_delete_car_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление автомобиля"""
    query = update.callback_query
    await query.answer()
    
    if not query.data.startswith("admin_delete_"):
        return
    
    car_id = int(query.data.replace("admin_delete_", ""))
    data = load_data()
    cars = data.get("cars", [])
    
    # Удаляем фотографии
    car_to_delete = next((c for c in cars if c.get("id") == car_id), None)
    if car_to_delete:
        for photo in car_to_delete.get("photos", []):
            if not photo.startswith("http"):
                photo_path = os.path.join(PHOTOS_DIR, photo)
                try:
                    if os.path.exists(photo_path):
                        os.remove(photo_path)
                except:
                    pass
    
    data["cars"] = [c for c in cars if c.get("id") != car_id]
    save_data(data)
    
    await query.edit_message_text(
        f"✅ Автомобиль с ID {car_id} удален.",
        reply_markup=get_admin_menu()
    )

async def admin_photos_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Управление фотографиями автомобиля"""
    query = update.callback_query
    await query.answer()
    
    if not query.data.startswith("admin_photos_"):
        return
    
    car_id = int(query.data.replace("admin_photos_", ""))
    data = load_data()
    car = next((c for c in data.get("cars", []) if c.get("id") == car_id), None)
    
    if not car:
        await query.edit_message_text("❌ Автомобиль не найден.", reply_markup=get_admin_menu())
        return
    
    context.user_data['admin_photo_car_id'] = car_id
    photo_count = len(car.get("photos", []))
    
    kb = [
        [InlineKeyboardButton("➕ Добавить фото", callback_data="admin_add_photo")],
        [InlineKeyboardButton("🗑 Удалить фото", callback_data="admin_delete_photo")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin_manage_photos")]
    ]
    
    await query.edit_message_text(
        f"📸 *Фотографии автомобиля*\n\n"
        f"*{car.get('brand')} {car.get('model')}*\n"
        f"Текущее количество фото: {photo_count}/5\n\n"
        f"Выберите действие:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(kb)
    )

# Состояния для добавления автомобиля
ADMIN_BRAND, ADMIN_MODEL, ADMIN_YEAR, ADMIN_PRICE, ADMIN_BODY, ADMIN_ENGINE, ADMIN_ENGINE_VOL, ADMIN_TRANSMISSION, ADMIN_COLOR, ADMIN_MILEAGE, ADMIN_DESCRIPTION, ADMIN_FEATURES, ADMIN_PHOTO = range(13)

async def admin_add_car_brand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение марки автомобиля"""
    context.user_data['new_car']['brand'] = update.message.text
    await update.message.reply_text("Введите модель автомобиля:")
    return ADMIN_MODEL

async def admin_add_car_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение модели автомобиля"""
    context.user_data['new_car']['model'] = update.message.text
    await update.message.reply_text("Введите год выпуска:")
    return ADMIN_YEAR

async def admin_add_car_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение года выпуска"""
    try:
        year = int(update.message.text)
        context.user_data['new_car']['year'] = year
        await update.message.reply_text("Введите цену (только число):")
        return ADMIN_PRICE
    except:
        await update.message.reply_text("❌ Неверный формат. Введите год числом:")
        return ADMIN_YEAR

async def admin_add_car_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение цены"""
    try:
        price = int(update.message.text)
        context.user_data['new_car']['price'] = price
        
        kb = [[InlineKeyboardButton(bt, callback_data=f"admin_body_{bt}")] for bt in BODY_TYPES]
        kb.append([InlineKeyboardButton("❌ Отмена", callback_data="admin_cancel")])
        
        await update.message.reply_text("Выберите тип кузова:", reply_markup=InlineKeyboardMarkup(kb))
        return ADMIN_BODY
    except:
        await update.message.reply_text("❌ Неверный формат. Введите цену числом:")
        return ADMIN_PRICE

async def admin_add_car_body(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение типа кузова"""
    query = update.callback_query
    await query.answer()
    body_type = query.data.replace("admin_body_", "")
    context.user_data['new_car']['body_type'] = body_type
    
    kb = [[InlineKeyboardButton(et, callback_data=f"admin_engine_{et}")] for et in ENGINE_TYPES]
    kb.append([InlineKeyboardButton("❌ Отмена", callback_data="admin_cancel")])
    
    await query.edit_message_text("Выберите тип двигателя:", reply_markup=InlineKeyboardMarkup(kb))
    return ADMIN_ENGINE

async def admin_add_car_engine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение типа двигателя"""
    query = update.callback_query
    await query.answer()
    engine_type = query.data.replace("admin_engine_", "")
    context.user_data['new_car']['engine_type'] = engine_type
    await query.edit_message_text("Введите объем двигателя (например: 1.6):")
    return ADMIN_ENGINE_VOL

async def admin_add_car_engine_vol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение объема двигателя"""
    try:
        vol = float(update.message.text)
        context.user_data['new_car']['engine_volume'] = vol
        
        kb = [[InlineKeyboardButton(t, callback_data=f"admin_trans_{t}")] for t in TRANSMISSIONS]
        kb.append([InlineKeyboardButton("❌ Отмена", callback_data="admin_cancel")])
        
        await update.message.reply_text("Выберите коробку передач:", reply_markup=InlineKeyboardMarkup(kb))
        return ADMIN_TRANSMISSION
    except:
        await update.message.reply_text("❌ Неверный формат. Введите объем числом (например: 1.6):")
        return ADMIN_ENGINE_VOL

async def admin_add_car_transmission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение коробки передач"""
    query = update.callback_query
    await query.answer()
    transmission = query.data.replace("admin_trans_", "")
    context.user_data['new_car']['transmission'] = transmission
    await query.edit_message_text("Введите цвет автомобиля:")
    return ADMIN_COLOR

async def admin_add_car_color(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение цвета"""
    context.user_data['new_car']['color'] = update.message.text
    await update.message.reply_text("Введите пробег (только число, в км):")
    return ADMIN_MILEAGE

async def admin_add_car_mileage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение пробега"""
    try:
        mileage = int(update.message.text)
        context.user_data['new_car']['mileage'] = mileage
        await update.message.reply_text("Введите описание автомобиля:")
        return ADMIN_DESCRIPTION
    except:
        await update.message.reply_text("❌ Неверный формат. Введите пробег числом:")
        return ADMIN_MILEAGE

async def admin_add_car_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение описания"""
    context.user_data['new_car']['description'] = update.message.text
    await update.message.reply_text(
        "Введите особенности через запятую (например: Кондиционер, Кожаный салон, Круиз-контроль):\n"
        "Или отправьте /skip чтобы пропустить"
    )
    return ADMIN_FEATURES

async def admin_add_car_features(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение особенностей и завершение добавления"""
    if update.message.text and update.message.text != "/skip":
        features = [f.strip() for f in update.message.text.split(",")]
        context.user_data['new_car']['features'] = features
    else:
        context.user_data['new_car']['features'] = []
    
    # Завершаем добавление
    new_car = context.user_data['new_car']
    new_car['id'] = get_next_car_id()
    new_car['is_available'] = True
    
    # Проверяем, что все обязательные поля заполнены
    required_fields = ['brand', 'model', 'year', 'price', 'body_type', 'engine_type', 
                       'engine_volume', 'transmission', 'color', 'mileage', 'description']
    missing_fields = [field for field in required_fields if field not in new_car or not new_car[field]]
    
    if missing_fields:
        await update.message.reply_text(
            f"❌ Ошибка: не заполнены обязательные поля: {', '.join(missing_fields)}\n"
            f"Попробуйте добавить автомобиль заново.",
            reply_markup=get_admin_menu()
        )
        context.user_data.pop('new_car', None)
        context.user_data.pop('admin_mode', None)
        return ConversationHandler.END
    
    data = load_data()
    data["cars"].append(new_car)
    save_data(data)
    
    # Проверяем сохранение
    data_check = load_data()
    saved_car = next((c for c in data_check.get("cars", []) if c.get("id") == new_car['id']), None)
    
    if not saved_car:
        logger.error(f"❌ Автомобиль не был сохранен в базу данных!")
        await update.message.reply_text(
            "❌ Ошибка при сохранении автомобиля. Попробуйте еще раз.",
            reply_markup=get_admin_menu()
        )
        return ConversationHandler.END
    
    # Формируем информацию о добавленном автомобиле
    car_info = f"""✅ *Автомобиль успешно добавлен!*

📋 *Информация:*
• ID: {new_car['id']}
• Марка: {new_car['brand']}
• Модель: {new_car['model']}
• Год: {new_car['year']}
• Цена: {new_car['price']:,} BYN
• Кузов: {new_car['body_type']}
• Двигатель: {new_car['engine_type']}, {new_car['engine_volume']} л
• КПП: {new_car['transmission']}
• Цвет: {new_car['color']}
• Пробег: {new_car['mileage']:,} км
• Описание: {new_car['description'][:50]}...
• Особенности: {', '.join(new_car.get('features', [])) if new_car.get('features') else 'нет'}
• Фотографии: {len(new_car.get('photos', []))} шт.

Теперь вы можете добавить фотографии через меню '📸 Управление фото'"""
    
    await update.message.reply_text(
        car_info,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_menu()
    )
    
    logger.info(f"✅ Автомобиль добавлен: {new_car['brand']} {new_car['model']} (ID: {new_car['id']})")
    
    context.user_data.pop('new_car', None)
    context.user_data.pop('admin_mode', None)
    return ConversationHandler.END

async def admin_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена добавления автомобиля"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("❌ Отменено.", reply_markup=get_admin_menu())
    else:
        await update.message.reply_text("❌ Отменено.", reply_markup=get_admin_menu())
    
    context.user_data.pop('new_car', None)
    context.user_data.pop('admin_mode', None)
    return ConversationHandler.END

async def admin_add_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик добавления фото"""
    query = update.callback_query
    await query.answer()
    
    car_id = context.user_data.get('admin_photo_car_id')
    if not car_id:
        await query.edit_message_text("❌ Ошибка. Начните заново.", reply_markup=get_admin_menu())
        return ConversationHandler.END
    
    data = load_data()
    car = next((c for c in data.get("cars", []) if c.get("id") == car_id), None)
    if not car:
        await query.edit_message_text("❌ Автомобиль не найден.", reply_markup=get_admin_menu())
        return ConversationHandler.END
    
    # Считаем только локальные файлы (не URL)
    photos = car.get("photos", [])
    local_photos = [p for p in photos if not isinstance(p, str) or not p.startswith("http")]
    photo_count = len(local_photos)
    
    if photo_count >= 5:
        await query.edit_message_text(
            "❌ Максимальное количество фотографий (5) уже достигнуто.",
            reply_markup=get_admin_menu()
        )
        return
    
    context.user_data['admin_photo_mode'] = 'add'
    await query.edit_message_text(
        f"📸 *Добавление фотографии*\n\n"
        f"Отправьте фотографию (можно до {5 - photo_count} фото).\n"
        f"Или отправьте /cancel для отмены.",
        parse_mode=ParseMode.MARKDOWN
    )
    return ADMIN_PHOTO

async def admin_photo_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение фотографии от админа"""
    if not update.message.photo:
        await update.message.reply_text("❌ Пожалуйста, отправьте фотографию.")
        return ADMIN_PHOTO
    
    car_id = context.user_data.get('admin_photo_car_id')
    if not car_id:
        await update.message.reply_text("❌ Ошибка. Начните заново.", reply_markup=get_admin_menu())
        return ConversationHandler.END
    
    ensure_photos_dir()
    data = load_data()
    cars = data.get("cars", [])
    car = None
    car_index = -1
    for i, c in enumerate(cars):
        if c.get("id") == car_id:
            car = c
            car_index = i
            break
    
    if not car:
        await update.message.reply_text("❌ Автомобиль не найден.", reply_markup=get_admin_menu())
        return ConversationHandler.END
    
    # Получаем текущий список фотографий (может быть пустым)
    if "photos" not in car:
        car["photos"] = []
    
    # Фильтруем только локальные файлы (не URL)
    local_photos = [p for p in car["photos"] if not p.startswith("http")]
    photo_count = len(local_photos)
    
    if photo_count >= 5:
        await update.message.reply_text("❌ Максимальное количество фотографий (5) уже достигнуто.")
        return ConversationHandler.END
    
    try:
        # Скачиваем фото
        photo = update.message.photo[-1]  # Берем фото наибольшего размера
        file = await context.bot.get_file(photo.file_id)
        
        ext = ".jpg"
        filename = f"car_{car_id}_{photo_count + 1}{ext}"
        filepath = os.path.join(PHOTOS_DIR, filename)
        
        logger.info(f"Скачивание фото для автомобиля {car_id} в {filepath}")
        await file.download_to_drive(filepath)
        
        # Проверяем, что файл действительно скачался
        if not os.path.exists(filepath):
            logger.error(f"Файл не был скачан: {filepath}")
            await update.message.reply_text("❌ Ошибка при сохранении фотографии. Попробуйте еще раз.")
            return ADMIN_PHOTO
        
        # Добавляем в данные (создаем новый список, чтобы не изменять оригинал)
        if "photos" not in car:
            car["photos"] = []
        
        # Добавляем новое фото
        car["photos"].append(filename)
        logger.info(f"Фото добавлено в список: {filename}, всего фото: {len(car['photos'])}")
        
        # Обновляем данные в списке (используем глубокую копию)
        cars[car_index] = copy.deepcopy(car)
        data["cars"] = cars
        save_data(data)
        
        # Перезагружаем данные для проверки
        data_check = load_data()
        saved_car = next((c for c in data_check.get("cars", []) if c.get("id") == car_id), None)
        if saved_car:
            saved_photos = saved_car.get("photos", [])
            if filename in saved_photos:
                logger.info(f"✅ Фото успешно сохранено в JSON: {filename}")
                logger.info(f"Всего фото в сохраненных данных: {len(saved_photos)}")
            else:
                logger.error(f"❌ Фото не найдено в сохраненных данных! Ожидалось: {filename}, найдено: {saved_photos}")
        else:
            logger.error(f"❌ Автомобиль не найден после сохранения!")
        
        # Пересчитываем количество локальных фото из сохраненных данных
        if saved_car:
            new_count = len([p for p in saved_car.get("photos", []) if not (isinstance(p, str) and p.startswith("http"))])
        else:
            new_count = photo_count + 1
        
        if new_count < 5:
            await update.message.reply_text(
                f"✅ Фотография добавлена! ({new_count}/5)\n\n"
                f"Отправьте еще фото или /cancel для завершения."
            )
            return ADMIN_PHOTO
        else:
            await update.message.reply_text(
                f"✅ Фотография добавлена! Достигнут максимум (5/5).",
                reply_markup=get_admin_menu()
            )
            context.user_data.pop('admin_photo_mode', None)
            context.user_data.pop('admin_photo_car_id', None)
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"Ошибка при добавлении фото: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Ошибка при добавлении фотографии: {str(e)}")
        return ADMIN_PHOTO

async def admin_delete_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик удаления фото"""
    query = update.callback_query
    await query.answer()
    
    car_id = context.user_data.get('admin_photo_car_id')
    if not car_id:
        await query.edit_message_text("❌ Ошибка. Начните заново.", reply_markup=get_admin_menu())
        return
    
    data = load_data()
    car = next((c for c in data.get("cars", []) if c.get("id") == car_id), None)
    if not car:
        await query.edit_message_text("❌ Автомобиль не найден.", reply_markup=get_admin_menu())
        return
    
    photos = car.get("photos", [])
    if not photos:
        await query.edit_message_text("❌ У автомобиля нет фотографий.", reply_markup=get_admin_menu())
        return
    
    kb = []
    for idx, photo in enumerate(photos):
        kb.append([InlineKeyboardButton(
            f"🗑 Фото {idx + 1}",
            callback_data=f"admin_del_photo_{idx}"
        )])
    kb.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"admin_photos_{car_id}")])
    
    await query.edit_message_text(
        f"🗑 *Удаление фотографии*\n\n"
        f"*{car.get('brand')} {car.get('model')}*\n\n"
        f"Выберите фотографию для удаления:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def admin_delete_photo_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение удаления фото"""
    query = update.callback_query
    await query.answer()
    
    if not query.data.startswith("admin_del_photo_"):
        return
    
    photo_idx = int(query.data.replace("admin_del_photo_", ""))
    car_id = context.user_data.get('admin_photo_car_id')
    
    data = load_data()
    car = next((c for c in data.get("cars", []) if c.get("id") == car_id), None)
    if not car:
        await query.edit_message_text("❌ Автомобиль не найден.", reply_markup=get_admin_menu())
        return
    
    photos = car.get("photos", [])
    if photo_idx >= len(photos):
        await query.edit_message_text("❌ Фотография не найдена.", reply_markup=get_admin_menu())
        return
    
    # Удаляем файл
    photo_filename = photos[photo_idx]
    if not photo_filename.startswith("http"):
        photo_path = os.path.join(PHOTOS_DIR, photo_filename)
        try:
            if os.path.exists(photo_path):
                os.remove(photo_path)
        except:
            pass
    
    # Удаляем из списка
    car["photos"].pop(photo_idx)
    
    # Обновляем данные
    cars = data.get("cars", [])
    for i, c in enumerate(cars):
        if c.get("id") == car_id:
            cars[i] = car
            break
    
    data["cars"] = cars
    save_data(data)
    
    await query.edit_message_text(
        f"✅ Фотография удалена!",
        reply_markup=get_admin_menu()
    )
    context.user_data.pop('admin_photo_car_id', None)

def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен!")
        return
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.Text("🚗 Каталог авто"), show_catalog))
    app.add_handler(MessageHandler(filters.Text("📞 Контакты"), show_contacts))
    app.add_handler(MessageHandler(filters.Text("🆘 Помощь"), help_command))
    app.add_handler(CallbackQueryHandler(show_filter_params, pattern="^filter_params$"))
    app.add_handler(CallbackQueryHandler(show_all_cars, pattern="^show_all$"))
    app.add_handler(CallbackQueryHandler(filter_brand, pattern="^filter_brand$"))
    app.add_handler(CallbackQueryHandler(filter_body, pattern="^filter_body$"))
    app.add_handler(CallbackQueryHandler(filter_engine, pattern="^filter_engine$"))
    app.add_handler(CallbackQueryHandler(filter_transmission, pattern="^filter_transmission$"))
    app.add_handler(CallbackQueryHandler(filter_price, pattern="^filter_price$"))
    app.add_handler(CallbackQueryHandler(handle_filter_selection, pattern="^select_"))
    app.add_handler(CallbackQueryHandler(check_availability, pattern="^check_availability$"))
    app.add_handler(CallbackQueryHandler(view_available_cars, pattern="^view_available_cars$"))
    app.add_handler(CallbackQueryHandler(new_search, pattern="^new_search$"))
    app.add_handler(CallbackQueryHandler(handle_car_navigation, pattern="^(prev_|next_|photo_prev_|photo_next_)"))
    app.add_handler(CallbackQueryHandler(show_catalog, pattern="^back_to_catalog$"))
    app.add_handler(CallbackQueryHandler(back_to_main, pattern="^back_to_main$"))
    app.add_handler(CallbackQueryHandler(back_to_main_from_catalog, pattern="^back_to_main_from_catalog$"))
    app.add_handler(CallbackQueryHandler(back_to_filters, pattern="^back_to_filters$"))
    
    app_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_application, pattern="^create_application$")],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            PREFERENCES: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_preferences)],
        },
        fallbacks=[CallbackQueryHandler(cancel_application, pattern="^cancel_application$")],
        per_message=True
    )
    app.add_handler(app_handler)
    
    # ConversationHandler для добавления автомобиля
    async def admin_add_car_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало добавления автомобиля"""
        query = update.callback_query
        await query.answer()
        user = update.effective_user
        
        if not is_admin(user.id, user.username):
            await query.edit_message_text("❌ У вас нет доступа.")
            return ConversationHandler.END
        
        context.user_data['admin_mode'] = 'add_car'
        context.user_data['new_car'] = {'photos': []}
        await query.edit_message_text(
            "➕ *Добавление автомобиля*\n\nВведите марку автомобиля:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="admin_cancel")]])
        )
        return ADMIN_BRAND
    
    admin_car_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_add_car_start, pattern="^admin_add_car$")],
        states={
            ADMIN_BRAND: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_car_brand)],
            ADMIN_MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_car_model)],
            ADMIN_YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_car_year)],
            ADMIN_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_car_price)],
            ADMIN_BODY: [CallbackQueryHandler(admin_add_car_body, pattern="^admin_body_")],
            ADMIN_ENGINE: [CallbackQueryHandler(admin_add_car_engine, pattern="^admin_engine_")],
            ADMIN_ENGINE_VOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_car_engine_vol)],
            ADMIN_TRANSMISSION: [CallbackQueryHandler(admin_add_car_transmission, pattern="^admin_trans_")],
            ADMIN_COLOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_car_color)],
            ADMIN_MILEAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_car_mileage)],
            ADMIN_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_car_description)],
            ADMIN_FEATURES: [MessageHandler(filters.TEXT, admin_add_car_features)],
        },
        fallbacks=[CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$")]
    )
    app.add_handler(admin_car_handler)
    
    # ConversationHandler для добавления фотографий
    admin_photo_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_add_photo_handler, pattern="^admin_add_photo$")],
        states={
            ADMIN_PHOTO: [MessageHandler(filters.PHOTO, admin_photo_received)],
        },
        fallbacks=[MessageHandler(filters.TEXT & filters.Regex("^/cancel$"), admin_cancel)]
    )
    app.add_handler(admin_photo_handler)
    
    # Админ-панель (обычные обработчики должны быть ПОСЛЕ ConversationHandler)
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(admin_menu_handler, pattern="^admin_(list_cars|delete_car|manage_photos|exit|back)$"))
    app.add_handler(CallbackQueryHandler(admin_delete_car_handler, pattern="^admin_delete_\\d+$"))
    app.add_handler(CallbackQueryHandler(admin_photos_handler, pattern="^admin_photos_\\d+$"))
    app.add_handler(CallbackQueryHandler(admin_delete_photo_handler, pattern="^admin_delete_photo$"))
    app.add_handler(CallbackQueryHandler(admin_delete_photo_confirm, pattern="^admin_del_photo_\\d+$"))
    
    ensure_photos_dir()
    logger.info("Бот запускается...")
    app.run_polling()

if __name__ == "__main__":
    main()
