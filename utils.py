"""
Вспомогательные функции для телеграм бота
"""
import os
import requests
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_IDS

logger = logging.getLogger(__name__)

def ensure_photos_dir():
    """Создает папку для фотографий если её нет"""
    from config import PHOTOS_DIR
    if not os.path.exists(PHOTOS_DIR):
        os.makedirs(PHOTOS_DIR)

def download_image_from_url(url, car_id, photo_index):
    """Скачивает изображение по URL и сохраняет локально"""
    from config import PHOTOS_DIR
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
        logger.warning(f"Не удалось отредактировать сообщение, отправляем новое: {e}")
        try:
            await query.message.delete()
        except Exception as delete_error:
            logger.debug(f"Не удалось удалить старое сообщение: {delete_error}")
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
    for admin in ADMIN_IDS:
        admin = admin.strip()
        if isinstance(admin, str) and admin.startswith("@"):
            # Если ADMIN_ID это username
            if username and username.lower() == admin[1:].lower():
                return True
        else:
            try:
                admin_id_int = int(admin)
                if user_id == admin_id_int:
                    return True
            except:
                continue
    return False

def get_next_car_id():
    """Получение следующего ID для автомобиля"""
    import database
    data = database.load_data()
    cars = data.get("cars", [])
    if not cars:
        return 1
    return max(car.get("id", 0) for car in cars) + 1
