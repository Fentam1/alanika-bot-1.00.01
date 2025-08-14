import gspread
from google.oauth2.service_account import Credentials

# Подключаемся к Google Sheets
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

# Используем правильное имя файла ключа
creds = Credentials.from_service_account_file('google_credentials.json', scopes=scopes)
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
            "extra_code": str(row.get("Товар", "")).strip(),
            "name": row.get("Наименование", ""),
            "stock": row.get("Остаток", 0),
            "expiry": row.get("Срок годности", ""),
            "price_no_vat": str(row.get("Цена без НДС", "")).replace(",", "."),
            "price_with_vat": str(row.get("Цена с НДС", "")).replace(",", ".")
        }
        products.append(product)
    return products

def find_product_by_code_ending(code_ending):
    products = get_products()
    matches = []
    for product in products:
        if product["code"].endswith(code_ending):
            matches.append(product)
    return matches  # возвращаем список всех совпадений

