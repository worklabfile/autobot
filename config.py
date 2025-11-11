import os
from dotenv import load_dotenv

load_dotenv()

# ВАЖНО: Замените на ваш реальный токен от @BotFather
# Получите токен: напишите @BotFather в Telegram -> /newbot или /token
BOT_TOKEN = os.getenv("BOT_TOKEN", "8531805942:AAH17N3mmpYnABgzQV266NRKHMx6eLfBro4")
ADMIN_IDS = os.getenv("ADMIN_IDS", "911971063,1289170350").split(",")

# Пути к файлам
CARS_FILE = "data/datacars.json"
PHOTOS_DIR = "data/photos"

BRANDS = ["Toyota", "BMW", "Mercedes", "Audi", "Volkswagen", "Hyundai", "Kia", "Nissan"]
BODY_TYPES = ["Седан", "Внедорожник", "Хэтчбек", "Универсал", "Купе", "Минивэн", "Пикап"]
ENGINE_TYPES = ["Бензин", "Дизель", "Электро", "Гибрид"]
TRANSMISSIONS = ["Автомат", "Механика", "Вариатор", "Робот"]
PRICE_RANGES = [
    "До 5000 $",
    "5000 - 10000 $",
    "10000 - 20000 $",
    "20000 - 50000 $",
    "Свыше 50000 $"
]
