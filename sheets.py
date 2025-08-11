import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from datetime import datetime

# Загружаем .env
load_dotenv()

# Читаем путь к файлу с ключами из .env
GOOGLE_KEY_FILE = os.getenv("GOOGLE_KEY_FILE")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
TEMP_ORDERS_SHEET = os.getenv("TEMP_ORDERS_SHEET", "TempOrders")

# Авторизация в Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_KEY_FILE, scope)
client = gspread.authorize(creds)


def get_temp_orders_worksheet():
    """Открываем лист TempOrders"""
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    return spreadsheet.worksheet(TEMP_ORDERS_SHEET)


def save_user_order_state(user_id, order_data):
    """
    Сохраняем заказ в красивом виде в TempOrders:
    Дата | UserID | Клиент | Код товара | Наименование | Кол-во | Цена | Комментарий
    """
    ws = get_temp_orders_worksheet()

    # Заголовки
    header = ["Дата", "UserID", "Клиент", "Код товара", "Наименование", "Кол-во", "Цена", "Комментарий"]
    all_data = ws.get_all_values()

    # Если шапка пустая — создаём её
    if not all_data or all_data[0] != header:
        if all_data:
            ws.insert_row(header, 1)
        else:
            ws.append_row(header)

    # Удаляем старые строки этого пользователя (начиная со 2-й)
    all_data = ws.get_all_values()
    rows_to_delete = [idx for idx, row in enumerate(all_data, start=1) if idx > 1 and row and row[1] == str(user_id)]
    for idx in reversed(rows_to_delete):
        ws.delete_rows(idx)

    # Записываем новые строки
    for product in order_data.get("products", []):
        ws.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            str(user_id),
            order_data.get("client", ""),
            product.get("code", ""),
            product.get("name", ""),
            product.get("qty", ""),
            product.get("price", ""),
            order_data.get("note", "")
        ])


def load_user_order_state(user_id):
    """Читаем заказ из TempOrders и собираем в структуру Python"""
    ws = get_temp_orders_worksheet()
    all_data = ws.get_all_values()

    products = []
    client = None
    note = None

    for row in all_data[1:]:  # пропускаем шапку
        if row and row[1] == str(user_id):
            products.append({
                "code": row[3],
                "name": row[4],
                "qty": int(row[5]) if row[5].isdigit() else row[5],
                "price": float(row[6]) if row[6].replace('.', '', 1).isdigit() else row[6]
            })
            client = row[2]
            note = row[7]

    if not products:
        return None

    return {
        "products": products,
        "client": client,
        "note": note
    }


def delete_user_order_state(user_id):
    """Удаляем все строки пользователя из TempOrders"""
    ws = get_temp_orders_worksheet()
    all_data = ws.get_all_values()

    rows_to_delete = [idx for idx, row in enumerate(all_data, start=1) if idx > 1 and row and row[1] == str(user_id)]
    for idx in reversed(rows_to_delete):
        ws.delete_rows(idx)
