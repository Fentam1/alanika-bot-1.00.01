import gspread
from google.oauth2.service_account import Credentials

# Подключаемся к Google Sheets
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_file('creds.json', scopes=scopes)
gc = gspread.authorize(creds)

# Открываем таблицу и лист
sheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/1UcxQORwPy4AiYL4a9qrrhPI78OOB0mxMOjJXX-PfLZ4/edit")
worksheet = sheet.worksheet("stock1")  # <- название листа

def get_products():
    records = worksheet.get_all_records()
    products = []
    for row in records:
        product = {
            "code": str(row.get("Код", "")).strip(),
            "name": row.get("Наименование", ""),
            "stock": row.get("Остаток", 0),
            "expiry": row.get("Срок годности", ""),
            "price_no_vat": str(row.get("Цена без НДС", "")).replace(",", "."),
            "price_with_vat": str(row.get("Цена с НДС", "")).replace(",", ".")
        }
        products.append(product)
    return products

def find_product_by_code_ending(code_ending):
    print(f"Ищем товар по коду: '{code_ending}'")
    products = get_products()
    for product in products:
        print(f"Проверяем товар с кодом: '{product['code']}'")
        if product["code"].endswith(code_ending):
            print("Товар найден")
            return product
    print("Товар не найден в базе")
    return None
