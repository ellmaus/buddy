import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
DB_PATH = os.environ.get("DB_PATH", "data/bot.db")

# Длина обычного шага и «крошечного» шага (минуты)
STEP_MINUTES = 10
TINY_MINUTES = 2

# Как часто планировщик проверяет, не пора ли отправить чек-ин (секунды)
SCHEDULER_INTERVAL = 5
