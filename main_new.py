"""
Главный файл телеграм бота для автосалона
Запуск приложения и инициализация обработчиков
"""
import logging
import warnings

# Подавляем PTBUserWarning в самом начале
warnings.simplefilter("ignore")

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ConversationHandler
)
from telegram import error as telegram_error
from telegram.constants import ParseMode

# Импорты из модулей
from config import BOT_TOKEN
from utils import ensure_photos_dir
from handlers import (
    start, help_command, show_catalog, show_contacts,
    filter_brand, filter_body, filter_engine, filter_transmission, filter_price,
    handle_filter_selection, check_availability, view_available_cars, new_search,
    handle_car_navigation, back_to_main, back_to_main_from_catalog, back_to_filters,
    start_application, get_name, get_phone, get_preferences, skip_preferences, cancel_application,
    show_all_cars, show_filter_params, show_car
)
from admin import (
    admin_command, admin_menu_handler, admin_delete_car_handler,
    admin_photos_handler, admin_delete_photo_handler, admin_delete_photo_confirm,
    admin_add_photo_handler, admin_photo_received,
    admin_add_car_brand, admin_add_car_model, admin_add_car_year, admin_add_car_price,
    admin_add_car_body, admin_add_car_engine, admin_add_car_engine_vol,
    admin_add_car_transmission, admin_add_car_color, admin_add_car_mileage,
    admin_add_car_description, admin_add_car_features, admin_cancel,
    ADMIN_BRAND, ADMIN_MODEL, ADMIN_YEAR, ADMIN_PRICE, ADMIN_BODY, ADMIN_ENGINE,
    ADMIN_ENGINE_VOL, ADMIN_TRANSMISSION, ADMIN_COLOR, ADMIN_MILEAGE, ADMIN_DESCRIPTION,
    ADMIN_FEATURES, ADMIN_PHOTO
)

# Импорты состояний для ConversationHandler
from handlers import NAME, PHONE, PREFERENCES

logger = logging.getLogger(__name__)

def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен!")
        return
    app = Application.builder().token(BOT_TOKEN).build()

    # Основные команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Обработчики сообщений
    app.add_handler(MessageHandler(filters.Text("🚗 Каталог авто"), show_catalog))
    app.add_handler(MessageHandler(filters.Text("📞 Контакты"), show_contacts))
    app.add_handler(MessageHandler(filters.Text("🆘 Помощь"), help_command))

    # Обработчики callback-запросов для фильтров
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

    # ConversationHandler для заявок
    app_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_application, pattern="^create_application")],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            PREFERENCES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_preferences),
                CallbackQueryHandler(skip_preferences, pattern="^skip_preferences$")
            ],
        },
        fallbacks=[CallbackQueryHandler(cancel_application, pattern="^cancel_application$")],
        per_message=False
    )
    app.add_handler(app_handler)

    # ConversationHandler для добавления автомобиля
    async def admin_add_car_start(update: Update, context):
        """Начало добавления автомобиля"""
        query = update.callback_query
        await query.answer()
        user = update.effective_user

        from utils import is_admin
        if not is_admin(user.id, user.username):
            from handlers import safe_edit_message_text
            await safe_edit_message_text(query, "❌ У вас нет доступа.")
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
        fallbacks=[CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$")],
        per_message=False
    )
    app.add_handler(admin_car_handler)

    # ConversationHandler для добавления фотографий
    admin_photo_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_add_photo_handler, pattern="^admin_add_photo$")],
        states={
            ADMIN_PHOTO: [MessageHandler(filters.PHOTO, admin_photo_received)],
        },
        fallbacks=[MessageHandler(filters.TEXT & filters.Regex("^/cancel$"), admin_cancel)],
        per_message=False
    )
    app.add_handler(admin_photo_handler)

    # Админ-панель
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(admin_menu_handler, pattern="^admin_(list_cars|delete_car|manage_photos|exit|back)$"))
    app.add_handler(CallbackQueryHandler(admin_delete_car_handler, pattern="^admin_delete_\\d+$"))
    app.add_handler(CallbackQueryHandler(admin_photos_handler, pattern="^admin_photos_\\d+$"))
    app.add_handler(CallbackQueryHandler(admin_delete_photo_handler, pattern="^admin_delete_photo$"))
    app.add_handler(CallbackQueryHandler(admin_delete_photo_confirm, pattern="^admin_del_photo_\\d+$"))

    # Обработчик ошибок
    async def error_handler(update, context):
        """Обработчик ошибок"""
        error = context.error
        if isinstance(error, telegram_error.Conflict):
            logger.error("Обнаружен конфликт: другой экземпляр бота уже запущен!")
            logger.error("Бот останавливается автоматически.")
            try:
                await context.application.stop()
            except RuntimeError:
                logger.info("Приложение уже остановлено")
            return

        logger.error(f"Необработанная ошибка: {error}")
        if update:
            try:
                if hasattr(update, 'message') and update.message:
                    await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
                elif hasattr(update, 'callback_query') and update.callback_query:
                    await update.callback_query.message.reply_text("Произошла ошибка. Попробуйте позже.")
            except:
                pass

    app.add_error_handler(error_handler)

    ensure_photos_dir()
    logger.info("Бот запускается...")
    try:
        app.run_polling()
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")

if __name__ == "__main__":
    main()
