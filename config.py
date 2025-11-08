import os
from dotenv import load_dotenv

load_dotenv()

# ВАЖНО: Замените на ваш реальный токен от @BotFather
# Получите токен: напишите @BotFather в Telegram -> /newbot или /token
BOT_TOKEN = os.getenv("BOT_TOKEN", "8567302531:AAGflI3fzD3FCA__8DvNl3O-3r8Iyu1Gf6I")
ADMIN_ID = os.getenv("ADMIN_ID", "@vsfilippov")

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
