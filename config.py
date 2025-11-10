import os
from dotenv import load_dotenv

load_dotenv()

# ВАЖНО: Замените на ваш реальный токен от @BotFather
# Получите токен: напишите @BotFather в Telegram -> /newbot или /token
BOT_TOKEN = os.getenv("BOT_TOKEN", "8531805942:AAH17N3mmpYnABgzQV266NRKHMx6eLfBro4")
ADMIN_ID = os.getenv("ADMIN_ID", "911971063")

# Пути к файлам
CARS_FILE = "data/datacars.json"
PHOTOS_DIR = "data/photos"

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
