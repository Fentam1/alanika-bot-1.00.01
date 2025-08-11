import gspread

gc = gspread.service_account(filename="creds.json")
sh = gc.open_by_url("https://docs.google.com/spreadsheets/d/1UcxQORwPy4AiYL4a9qrrhPI78OOB0mxMOjJXX-PfLZ4/edit")
for ws in sh.worksheets():
    print(f"- Найден лист: '{ws.title}'")


# Подключаемся к Google Sheets по сервисному аккаунту
gc = gspread.service_account(filename='creds.json')

# Открываем таблицу по URL или по имени (лучше — по URL)
sheet = gc.open_by_url('https://docs.google.com/spreadsheets/d/1UcxQORwPy4AiYL4a9qrrhPI78OOB0mxMOjJXX-PfLZ4/edit?usp=sharing')

# Печатаем все названия листов в таблице
worksheet_list = sheet.worksheets()
for ws in worksheet_list:
    print(f"Лист найден: '{ws.title}'")

