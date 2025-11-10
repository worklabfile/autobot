"""
Обработчики команд и сообщений для телеграм бота
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
import keyboards
import database
from utils import safe_edit_message_text

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Логируем информацию о пользователе (полезно для получения ID админа)
    logger.info(f"Пользователь {user.first_name} (@{user.username or 'no_username'}) запустил бота. ID: {user.id}")

    await update.message.reply_text(
        f"Добро пожаловать, {user.first_name}!\n\nВыберите раздел:",
        reply_markup=keyboards.get_main_menu()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Вы попали в чат-бот автохауса А7 хаус!\n\n Здесь вы можете ознакомиться с каталогом авто по нужным вам параметрам и оставить заявку. Здесь все очень легко 😉\nЕсли есть вопросы - звоните по номеру телефона +375296667994",
        reply_markup=keyboards.get_main_menu()
    )

async def show_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    text = "Каталог автомобилей\n\nВыберите способ поиска:"
    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(text, reply_markup=keyboards.get_catalog_menu())
    else:
        await update.callback_query.edit_message_text(text, reply_markup=keyboards.get_catalog_menu())

async def show_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = database.load_data()
    contacts = data.get("contacts", {})
    text = f"""Контакты

Телефон: {contacts.get('phone', 'не указан')}
WhatsApp: {contacts.get('whatsapp', 'не указан')}
Email: {contacts.get('email', 'не указан')}

Адрес: {contacts.get('address', 'не указан')}
График работы: {contacts.get('work_hours', 'не указан')}

Свяжитесь с нами или оставьте заявку.

https://yandex.by/maps/-/CLCVjWLW
{contacts.get('address', '')}"""
    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(text, reply_markup=keyboards.get_contacts_keyboard())
    else:
        await update.callback_query.edit_message_text(text, reply_markup=keyboards.get_contacts_keyboard())

async def show_filter_params(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await safe_edit_message_text(query, "Подбор по параметрам\n\nВыберите параметр для фильтрации:", reply_markup=keyboards.get_filters_menu())

async def show_all_cars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cars = database.get_cars()
    if not cars:
        await safe_edit_message_text(query, "На данный момент нет доступных автомобилей.")
        return
    context.user_data['current_cars'] = cars
    context.user_data['current_index'] = 0
    await show_car(query, context, 0)

async def filter_brand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await safe_edit_message_text(query, "Выберите марку автомобиля:", reply_markup=keyboards.get_brands_keyboard())

async def filter_body(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await safe_edit_message_text(query, "Выберите тип кузова:", reply_markup=keyboards.get_body_types_keyboard())

async def filter_engine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await safe_edit_message_text(query, "Выберите тип двигателя:", reply_markup=keyboards.get_engine_types_keyboard())

async def filter_transmission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await safe_edit_message_text(query, "Выберите коробку передач:", reply_markup=keyboards.get_transmission_keyboard())

async def filter_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await safe_edit_message_text(query, "Выберите ценовой диапазон:", reply_markup=keyboards.get_price_ranges_keyboard())

async def handle_filter_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if 'filters' not in context.user_data:
        context.user_data['filters'] = {}
    if data.startswith('select_brand_'):
        context.user_data['filters']['brand'] = data.replace('select_brand_', '')
        text = f"Марка: {context.user_data['filters']['brand']}\n\nВыберите следующий параметр или проверьте наличие:"
    elif data.startswith('select_body_'):
        context.user_data['filters']['body_type'] = data.replace('select_body_', '')
        text = f"Кузов: {context.user_data['filters']['body_type']}\n\nВыберите следующий параметр или проверьте наличие:"
    elif data.startswith('select_engine_'):
        context.user_data['filters']['engine_type'] = data.replace('select_engine_', '')
        text = f"Двигатель: {context.user_data['filters']['engine_type']}\n\nВыберите следующий параметр или проверьте наличие:"
    elif data.startswith('select_transmission_'):
        context.user_data['filters']['transmission'] = data.replace('select_transmission_', '')
        text = f"КПП: {context.user_data['filters']['transmission']}\n\nВыберите следующий параметр или проверьте наличие:"
    elif data.startswith('select_price_'):
        context.user_data['filters']['price_range'] = data.replace('select_price_', '')
        text = f"Цена: {context.user_data['filters']['price_range']}\n\nВыберите следующий параметр или проверьте наличие:"
    else:
        return
    await safe_edit_message_text(query, text, reply_markup=keyboards.get_filters_menu())

async def check_availability(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    filters = context.user_data.get('filters', {})
    count = len(database.get_cars(filters))
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
    await safe_edit_message_text(query, f"Проверка наличия\n\n{filters_text}\nДоступно {count} авто", reply_markup=keyboards.get_availability_keyboard(count))

async def view_available_cars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    filters = context.user_data.get('filters', {})
    cars = database.get_cars(filters)
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
    await safe_edit_message_text(query, "Новый поиск\n\nВыберите параметр для фильтрации:", reply_markup=keyboards.get_filters_menu())

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

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_text("Главное меню:", reply_markup=keyboards.get_main_menu())
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
            reply_markup=keyboards.get_main_menu()
        )

async def back_to_main_from_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_text("Главное меню:", reply_markup=keyboards.get_main_menu())
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
            reply_markup=keyboards.get_main_menu()
        )

async def back_to_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await safe_edit_message_text(query, "Подбор по параметрам\n\nВыберите параметр для фильтрации:", reply_markup=keyboards.get_filters_menu())

async def show_car(update, context: ContextTypes.DEFAULT_TYPE, index: int, photo_index: int = 0):
    from config import ADMIN_IDS, PHOTOS_DIR
    import os
    from telegram import InputMediaPhoto

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
    
    caption = f"""*{car['brand']} {car['model']}*

Год: {car['year']}
Цена: *{car['price']:,} BYN*
Цвет: {car.get('color', 'не указан')}
Пробег: {car.get('mileage', 0):,} км
Двигатель: {car['engine_type']}, {car.get('engine_volume', 0)} л
КПП: {car['transmission']}
Кузов: {car['body_type']}

*{car.get('description', 'Описание отсутствует')}*

Особенности:
{chr(10).join(['• ' + f for f in car.get('features', [])])}"""
    
    # Определяем, является ли update callback_query
    query = update if hasattr(update, 'edit_message_media') else None
    
    if valid_photos and photo_index < len(valid_photos):
        photo_path = valid_photos[photo_index]
        
        # Проверяем, это локальный файл или URL
        if photo_path.startswith('http'):
            # Это URL - скачиваем и сохраняем локально
            logger.info(f"Обнаружен URL фото: {photo_path}, скачиваем...")
            from utils import download_image_from_url
            downloaded_filename = download_image_from_url(photo_path, car['id'], 1)
            
            if downloaded_filename:
                # Обновляем данные в JSON
                data = database.load_data()
                for c in data.get("cars", []):
                    if c.get("id") == car['id']:
                        if isinstance(c.get('photos'), list):
                            # Заменяем URL на локальный файл
                            for i, p in enumerate(c['photos']):
                                if p == photo_path:
                                    c['photos'][i] = downloaded_filename
                                    break
                        database.save_data(data)
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
            # Всегда отправляем новое сообщение с фото
            if cached_file_id:
                # Используем кэшированный file_id для быстрой отправки
                result = await context.bot.send_photo(
                    chat_id=query.message.chat_id if query else update.message.chat_id,
                    photo=cached_file_id,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboards.get_car_navigation_keyboard(index, len(cars), photo_index, total_photos)
                )
            else:
                # Открываем файл и отправляем
                with open(photo_source, 'rb') as photo_file:
                    result = await (query.message.reply_photo if query else update.message.reply_photo)(
                        photo=photo_file,
                        caption=caption,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=keyboards.get_car_navigation_keyboard(index, len(cars), photo_index, total_photos)
                    )
                    # Сохраняем file_id для будущего использования
                    if result.photo:
                        context.bot_data[photo_cache_key] = result.photo[-1].file_id
        except Exception as e:
            # Если отправка фото не удалась, отправляем текст
            logger.error(f"Ошибка отправки фото {photo_source}: {e}")
            text_message = await (query.message.reply_text if query else update.message.reply_text)(
                caption, 
                parse_mode=ParseMode.MARKDOWN, 
                reply_markup=keyboards.get_car_navigation_keyboard(index, len(cars), photo_index, total_photos)
            )
    else:
        # Если фото нет, используем placeholder для плавного переключения
        logger.info(f"У автомобиля {car['id']} нет фото, используем placeholder")
        photo_source = os.path.join(PHOTOS_DIR, "placeholder.jpg")
        photo_cache_key = f"photo_placeholder"
        cached_file_id = context.bot_data.get(photo_cache_key)
        
        try:
            # Всегда отправляем новое сообщение с placeholder
            if cached_file_id:
                result = await context.bot.send_photo(
                    chat_id=query.message.chat_id if query else update.message.chat_id,
                    photo=cached_file_id,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboards.get_car_navigation_keyboard(index, len(cars), 0, 0)
                )
            else:
                with open(photo_source, 'rb') as photo_file:
                    result = await (query.message.reply_photo if query else update.message.reply_photo)(
                        photo=photo_file,
                        caption=caption,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=keyboards.get_car_navigation_keyboard(index, len(cars), 0, 0)
                    )
                    if result.photo:
                        context.bot_data[photo_cache_key] = result.photo[-1].file_id
        except Exception as e:
            # Если отправка фото не удалась, отправляем текст
            logger.error(f"Ошибка отправки placeholder: {e}")
            await (query.message.reply_text if query else update.message.reply_text)(
                caption, 
                parse_mode=ParseMode.MARKDOWN, 
                reply_markup=keyboards.get_car_navigation_keyboard(index, len(cars), 0, 0)
            )

# Состояния для заявок
NAME, PHONE, PREFERENCES = range(3)

async def start_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Проверяем, есть ли информация о выбранном автомобиле
    if query.data.startswith('create_application_'):
        car_index = int(query.data.split('_')[2])
        cars = context.user_data.get('current_cars', [])
        if cars and car_index < len(cars):
            context.user_data['selected_car'] = cars[car_index]

    await safe_edit_message_text(query, "Оставить заявку\n\nПожалуйста, укажите ваше имя:", reply_markup=keyboards.get_application_cancel())
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    context.user_data['application_name'] = name
    logger.info(f"Получено имя клиента: {name}")
    await update.message.reply_text("Теперь укажите ваш номер телефона:", reply_markup=keyboards.get_application_cancel())
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text
    context.user_data['application_phone'] = phone
    logger.info(f"Получен телефон клиента: {phone}")
    await update.message.reply_text("Укажите ваши предпочтения по автомобилю или имеющиеся вопросы:", reply_markup=keyboards.get_application_skip())
    return PREFERENCES

async def send_application_to_admin(bot, user, app_data):
    """Отправка заявки всем админам"""
    # Формируем сообщение для админа
    preferences = app_data.get('application_preferences', 'не указано')

    application_text = f"""Новая заявка от клиента

Имя клиента: {app_data['application_name']}
Телефон: {app_data['application_phone']}
Комментарий: {preferences}

━━━━━━━━━━━━━━━━━━━━
Telegram профиль:
• Имя: {user.first_name} {user.last_name or ''}
• Username: @{user.username or 'не указан'}
• ID: `{user.id}`"""

    # Добавляем информацию о выбранном автомобиле, если есть
    selected_car = app_data.get('selected_car')
    if selected_car:
        application_text += f"""

━━━━━━━━━━━━━━━━━━━━
Интересующий автомобиль:
• Марка/Модель: {selected_car.get('brand')} {selected_car.get('model')}
• Год: {selected_car.get('year')}
• Цена: {selected_car.get('price', 0):,} BYN
• Кузов: {selected_car.get('body_type')}
• Двигатель: {selected_car.get('engine_type')}, {selected_car.get('engine_volume')} л
• КПП: {selected_car.get('transmission')}
• Цвет: {selected_car.get('color', 'не указан')}
• Пробег: {selected_car.get('mileage', 0):,} км"""

    # Отправляем уведомление всем админам
    success_count = 0
    for admin_id in ADMIN_IDS:
        admin_id = admin_id.strip()
        try:
            admin_id_int = int(admin_id)
            await bot.send_message(
                chat_id=admin_id_int,
                text=application_text,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info(f"Заявка успешно отправлена админу {admin_id_int}")
            success_count += 1
        except Exception as e:
            logger.error(f"Ошибка отправки заявки админу {admin_id}: {e}")

    if success_count > 0:
        return True
    else:
        logger.info(f"ЗАЯВКА (не доставлена): {application_text}")
        return False

async def get_preferences(update: Update, context: ContextTypes.DEFAULT_TYPE):
    preferences = update.message.text
    context.user_data['application_preferences'] = preferences
    logger.info(f"Получены предпочтения клиента: {preferences}")

    user = update.effective_user
    app_data = context.user_data

    # Отправляем заявку админу
    await send_application_to_admin(context.bot, user, app_data)

    # Отправляем подтверждение клиенту
    await update.message.reply_text(
        "Спасибо за вашу заявку!\n\n"
        "Наш менеджер свяжется с вами в ближайшее время для уточнения деталей.\n\n"
        "Хорошего дня!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboards.get_main_menu()
    )

    # Очищаем данные
    context.user_data.pop('application_name', None)
    context.user_data.pop('application_phone', None)
    context.user_data.pop('application_preferences', None)
    context.user_data.pop('selected_car', None)
    return ConversationHandler.END

async def skip_preferences(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик пропуска комментария"""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    app_data = context.user_data

    # Устанавливаем пустое значение для предпочтений
    context.user_data['application_preferences'] = 'не указано'
    logger.info(f"Клиент {user.first_name} пропустил комментарий")

    # Отправляем заявку админу
    await send_application_to_admin(context.bot, user, app_data)

    # Отправляем подтверждение клиенту
    await query.message.reply_text(
        "Спасибо за вашу заявку!\n\n"
        "Наш менеджер свяжется с вами в ближайшее время для уточнения деталей.\n\n"
        "Хорошего дня!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboards.get_main_menu()
    )

    # Очищаем данные
    context.user_data.pop('application_name', None)
    context.user_data.pop('application_phone', None)
    context.user_data.pop('application_preferences', None)
    context.user_data.pop('selected_car', None)
    return ConversationHandler.END

async def cancel_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.pop('application_name', None)
    context.user_data.pop('application_phone', None)
    context.user_data.pop('application_preferences', None)
    context.user_data.pop('selected_car', None)
    await safe_edit_message_text(query, "Заявка отменена.", reply_markup=keyboards.get_main_menu())
    return ConversationHandler.END
