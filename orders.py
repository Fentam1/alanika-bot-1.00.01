# orders.py
import json
from datetime import datetime
from typing import Dict, Any
from config import EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENT
from email_module import send_email_with_pdf
from fpdf import FPDF

pdf = FPDF()
pdf.add_page()

pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
pdf.set_font('DejaVu', '', 14)

pdf.cell(40, 10, 'Текст на русском и английском')

pdf.output('order.pdf')


_orders = {}

def init_order(user_id):
    _orders[str(user_id)] = {
        "manager": "",
        "client": "",
        "products": [],
        "note": "",
        "delivery_date": "",
        "delivery_address": ""
    }

def update_order(user_id, key, value):
    user_key = str(user_id)
    if user_key not in _orders:
        init_order(user_id)
    _orders[user_key][key] = value

def get_order(user_id):
    return _orders.get(str(user_id), {})

def save_user_order_state(user_id, order):
    """Сохраняет заказ конкретного пользователя в файл ORDERS_FILE."""
    orders = load_orders()
    orders[str(user_id)] = order
    save_orders(orders)

def send_order_email(order: Dict[str, Any]):
    """
    Синхронная обёртка — запускаем эту функцию из bot.py в фоне:
        await asyncio.to_thread(send_order_email, order)
    """
    # Защита: если нет получателя или пустой список товаров — бросим исключение
    if not order or not order.get("products"):
        raise ValueError("Order empty or has no products")
    # Вызов реальной функции отправки
    send_email_with_pdf(order, EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENT)

# Архивация
ARCHIVE_FILE = "orders_archive.json"
ORDERS_FILE = "orders_data.json"

def write_order_to_archive(order):
    archive = load_orders_archive()
    order_copy = dict(order)
    order_copy["timestamp"] = datetime.now().isoformat()
    archive.append(order_copy)
    with open(ARCHIVE_FILE, "w", encoding="utf-8") as f:
        json.dump(archive, f, ensure_ascii=False, indent=2)

def load_orders_archive():
    try:
        with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def load_orders():
    try:
        with open(ORDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_orders(orders):
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)


# Примерная функция поиска товара по последним символам кода
def find_product_by_code_ending(code_ending):
    try:
        with open("products.json", "r", encoding="utf-8") as f:
            products = json.load(f)
    except FileNotFoundError:
        return None

    for product in products:
        if product["code"].endswith(code_ending):
            return product
    return None
