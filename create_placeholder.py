"""
Создание placeholder изображения для автомобилей без фото
"""
from PIL import Image, ImageDraw, ImageFont
import os

def create_placeholder_image():
    """Создает placeholder изображение"""
    # Создаем изображение 800x600
    width, height = 800, 600
    img = Image.new('RGB', (width, height), color='#2c3e50')
    
    draw = ImageDraw.Draw(img)
    
    # Рисуем иконку автомобиля (простой прямоугольник с колесами)
    car_color = '#34495e'
    # Кузов
    draw.rectangle([200, 250, 600, 400], fill=car_color)
    # Крыша
    draw.rectangle([280, 180, 520, 250], fill=car_color)
    # Окна
    draw.rectangle([300, 200, 400, 240], fill='#3498db')
    draw.rectangle([420, 200, 500, 240], fill='#3498db')
    # Колеса
    draw.ellipse([220, 380, 300, 460], fill='#1a1a1a')
    draw.ellipse([500, 380, 580, 460], fill='#1a1a1a')
    draw.ellipse([240, 400, 280, 440], fill='#7f8c8d')
    draw.ellipse([520, 400, 560, 440], fill='#7f8c8d')
    
    # Добавляем текст
    try:
        # Пытаемся использовать системный шрифт
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
    except:
        # Если не получилось, используем стандартный
        font = ImageFont.load_default()
    
    text = "Фото отсутствует"
    # Получаем размер текста
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Центрируем текст
    x = (width - text_width) // 2
    y = 480
    
    draw.text((x, y), text, fill='#ecf0f1', font=font)
    
    # Сохраняем
    os.makedirs('data/photos', exist_ok=True)
    img.save('data/photos/placeholder.jpg', 'JPEG', quality=85)
    print("✅ Placeholder изображение создано: data/photos/placeholder.jpg")

if __name__ == "__main__":
    create_placeholder_image()
