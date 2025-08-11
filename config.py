# config.py



GOOGLE_SHEETS_INVENTORY_ID = "1UcxQORwPy4AiYL4a9qrrhPI78OOB0mxMOjJXX-PfLZ4"
GOOGLE_SHEETS_ARCHIVE_ID = "1vKSD0RtZaqm9xOSQV-lrp6yvbO04L5Mp9uTJHlYGGB4"

ARCHIVE_SHEET_NAME = "Архив заказов"
INVENTORY_SHEET_NAME = "Склад"

import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT")

# Проверка, что все переменные подгрузились
if not all([BOT_TOKEN, EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENT]):
    raise ValueError("Не все переменные окружения найдены. Проверь .env файл.")



# Позже добавим SMTP и другие параметры
