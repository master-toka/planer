import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///family_bot.db')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
    
    # Настройки для AI
    AI_MODEL = "gpt-3.5-turbo"  # или "yandexgpt"
    AI_TEMPERATURE = 0.7
    AI_MAX_TOKENS = 500
    
    # Часовой пояс
    TIMEZONE = 'Europe/Moscow'
    
config = Config()