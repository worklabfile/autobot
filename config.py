import os
from dotenv import load_dotenv

load_dotenv()

# ВАЖНО: Замените на ваш реальный токен от @BotFather
# Получите токен: напишите @BotFather в Telegram -> /newbot или /token
BOT_TOKEN = os.getenv("BOT_TOKEN", "8300492583:AAEmIN3CdfyUsasn92UcgW9aW5y7pxQaHuw")
ADMIN_ID = os.getenv("ADMIN_ID", "911971063")

BRANDS = ["Toyota", "BMW", "Mercedes", "Audi", "Volkswagen", "Hyundai", "Kia", "Nissan"]
BODY_TYPES = ["Седан", "Внедорожник", "Хэтчбек", "Универсал", "Купе", "Минивэн", "Пикап"]
ENGINE_TYPES = ["Бензин", "Дизель", "Электро", "Гибрид"]
TRANSMISSIONS = ["Автомат", "Механика", "Вариатор", "Робот"]
PRICE_RANGES = [
    "До 5000 BYN",
    "5000 - 10000 BYN",
    "10000 - 20000 BYN",
    "20000 - 50000 BYN",
    "Свыше 50000 BYN"
]
