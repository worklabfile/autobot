"""
Административные функции для телеграм бота
"""
import copy
import logging
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
import keyboards
import database
from utils import ensure_photos_dir, is_admin, safe_edit_message_text

logger = logging.getLogger(__name__)

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
        reply_markup=keyboards.get_admin_menu()
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
        data = database.load_data()
        cars = data.get("cars", [])
        if not cars:
            await safe_edit_message_text(query, "📋 Список пуст.", reply_markup=keyboards.get_admin_menu())
            return

        text = "📋 *Список автомобилей:*\n\n"
        for car in cars[:10]:  # Показываем первые 10
            status = "✅" if car.get("is_available", True) else "❌"
            text += f"{status} *{car.get('id')}.* {car.get('brand')} {car.get('model')} - {car.get('price', 0):,} $\n"

        if len(cars) > 10:
            text += f"\n... и еще {len(cars) - 10} автомобилей"

        await safe_edit_message_text(query, text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboards.get_admin_menu())

    elif query.data == "admin_delete_car":
        data = database.load_data()
        cars = data.get("cars", [])
        if not cars:
            await safe_edit_message_text(query, "📋 Список пуст.", reply_markup=keyboards.get_admin_menu())
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
        data = database.load_data()
        cars = data.get("cars", [])
        if not cars:
            await safe_edit_message_text(query, "📋 Список пуст.", reply_markup=keyboards.get_admin_menu())
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
        await safe_edit_message_text(query, "✅ Выход из админ-панели.", reply_markup=keyboards.get_main_menu())

    elif query.data == "admin_back":
        await safe_edit_message_text(
            query,
            "🔐 *Админ-панель*\n\nВыберите действие:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboards.get_admin_menu()
        )

async def admin_delete_car_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление автомобиля"""
    query = update.callback_query
    await query.answer()

    if not query.data.startswith("admin_delete_"):
        return

    car_id = int(query.data.replace("admin_delete_", ""))
    data = database.load_data()
    cars = data.get("cars", [])

    # Удаляем фотографии
    car_to_delete = next((c for c in cars if c.get("id") == car_id), None)
    if car_to_delete:
        from config import PHOTOS_DIR
        for photo in car_to_delete.get("photos", []):
            if not photo.startswith("http"):
                photo_path = os.path.join(PHOTOS_DIR, photo)
                try:
                    if os.path.exists(photo_path):
                        os.remove(photo_path)
                except:
                    pass

    data["cars"] = [c for c in cars if c.get("id") != car_id]
    database.save_data(data)

    await query.edit_message_text(
        f"✅ Автомобиль с ID {car_id} удален.",
        reply_markup=keyboards.get_admin_menu()
    )

async def admin_photos_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Управление фотографиями автомобиля"""
    query = update.callback_query
    await query.answer()

    if not query.data.startswith("admin_photos_"):
        return

    car_id = int(query.data.replace("admin_photos_", ""))
    data = database.load_data()
    car = next((c for c in data.get("cars", []) if c.get("id") == car_id), None)

    if not car:
        await query.edit_message_text("❌ Автомобиль не найден.", reply_markup=keyboards.get_admin_menu())
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

async def admin_delete_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик удаления фото"""
    query = update.callback_query
    await query.answer()

    car_id = context.user_data.get('admin_photo_car_id')
    if not car_id:
        await query.edit_message_text("❌ Ошибка. Начните заново.", reply_markup=keyboards.get_admin_menu())
        return

    data = database.load_data()
    car = next((c for c in data.get("cars", []) if c.get("id") == car_id), None)
    if not car:
        await query.edit_message_text("❌ Автомобиль не найден.", reply_markup=keyboards.get_admin_menu())
        return

    photos = car.get("photos", [])
    if not photos:
        await query.edit_message_text("❌ У автомобиля нет фотографий.", reply_markup=keyboards.get_admin_menu())
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

    data = database.load_data()
    car = next((c for c in data.get("cars", []) if c.get("id") == car_id), None)
    if not car:
        await query.edit_message_text("❌ Автомобиль не найден.", reply_markup=keyboards.get_admin_menu())
        return

    photos = car.get("photos", [])
    if photo_idx >= len(photos):
        await query.edit_message_text("❌ Фотография не найдена.", reply_markup=keyboards.get_admin_menu())
        return

    # Удаляем файл
    photo_filename = photos[photo_idx]
    if not photo_filename.startswith("http"):
        from config import PHOTOS_DIR
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
    database.save_data(data)

    await query.edit_message_text(
        f"✅ Фотография удалена!",
        reply_markup=keyboards.get_admin_menu()
    )
    context.user_data.pop('admin_photo_car_id', None)

async def admin_add_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик добавления фото"""
    query = update.callback_query
    await query.answer()

    car_id = context.user_data.get('admin_photo_car_id')
    if not car_id:
        await query.edit_message_text("❌ Ошибка. Начните заново.", reply_markup=keyboards.get_admin_menu())
        return ConversationHandler.END

    data = database.load_data()
    car = next((c for c in data.get("cars", []) if c.get("id") == car_id), None)
    if not car:
        await query.edit_message_text("❌ Автомобиль не найден.", reply_markup=keyboards.get_admin_menu())
        return ConversationHandler.END

    # Считаем только локальные файлы (не URL)
    photos = car.get("photos", [])
    local_photos = [p for p in photos if not (isinstance(p, str) and p.startswith("http"))]
    photo_count = len(local_photos)

    if photo_count >= 5:
        await query.edit_message_text(
            "❌ Максимальное количество фотографий (5) уже достигнуто.",
            reply_markup=keyboards.get_admin_menu()
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
        await update.message.reply_text("❌ Ошибка. Начните заново.", reply_markup=keyboards.get_admin_menu())
        return ConversationHandler.END

    ensure_photos_dir()
    data = database.load_data()
    cars = data.get("cars", [])
    car = None
    car_index = -1
    for i, c in enumerate(cars):
        if c.get("id") == car_id:
            car = c
            car_index = i
            break

    if not car:
        await update.message.reply_text("❌ Автомобиль не найден.", reply_markup=keyboards.get_admin_menu())
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
        from config import PHOTOS_DIR
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
        database.save_data(data)

        # Перезагружаем данные для проверки
        data_check = database.load_data()
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
                reply_markup=keyboards.get_admin_menu()
            )
            context.user_data.pop('admin_photo_mode', None)
            context.user_data.pop('admin_photo_car_id', None)
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"Ошибка при добавлении фото: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Ошибка при добавлении фотографии: {str(e)}")
        return ADMIN_PHOTO

# Состояния для добавления автомобиля (нужно для ConversationHandler)
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

        from config import BODY_TYPES
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

    from config import ENGINE_TYPES
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

        from config import TRANSMISSIONS
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
    from utils import get_next_car_id
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
            reply_markup=keyboards.get_admin_menu()
        )
        context.user_data.pop('new_car', None)
        context.user_data.pop('admin_mode', None)
        return ConversationHandler.END

    data = database.load_data()
    data["cars"].append(new_car)
    database.save_data(data)

    # Проверяем сохранение
    data_check = database.load_data()
    saved_car = next((c for c in data_check.get("cars", []) if c.get("id") == new_car['id']), None)

    if not saved_car:
        logger.error(f"❌ Автомобиль не был сохранен в базу данных!")
        await update.message.reply_text(
            "❌ Ошибка при сохранении автомобиля. Попробуйте еще раз.",
            reply_markup=keyboards.get_admin_menu()
        )
        return ConversationHandler.END

    # Формируем информацию о добавленном автомобиле
    car_info = f"""✅ *Автомобиль успешно добавлен!*

📋 *Информация:*
• ID: {new_car['id']}
• Марка: {new_car['brand']}
• Модель: {new_car['model']}
• Год: {new_car['year']}
• Цена: {new_car['price']:,} $
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
        reply_markup=keyboards.get_main_menu()
    )

    logger.info(f"✅ Автомобиль добавлен: {new_car['brand']} {new_car['model']} (ID: {new_car['id']})")

    context.user_data.pop('new_car', None)
    context.user_data.pop('admin_mode', None)
    return ConversationHandler.END

async def admin_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена добавления автомобиля"""
    if hasattr(update, 'callback_query') and update.callback_query:
        query = update.callback_query
        if query:
            await query.answer()
            await query.edit_message_text("❌ Отменено.", reply_markup=keyboards.get_admin_menu())
    else:
        await update.message.reply_text("❌ Отменено.", reply_markup=keyboards.get_admin_menu())

    context.user_data.pop('new_car', None)
    context.user_data.pop('admin_mode', None)
    return ConversationHandler.END
