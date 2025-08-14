from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio
import os
from dotenv import load_dotenv
from orders import find_product_by_code_ending, get_order, save_orders, _orders



# Загружаем переменные из .env
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT")
credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

# Проверка, что все переменные подгрузились
if not all([BOT_TOKEN, EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENT]):
    raise ValueError("Не все переменные окружения найдены. Проверь .env файл.")

from orders import (
    init_order, update_order, get_order, save_user_order_state,
    send_order_email, write_order_to_archive, load_orders, save_orders
)

from products import find_product_by_code_ending

# Создаём экземпляры бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


class OrderState(StatesGroup):
    manager = State()
    client = State()
    product_code = State()
    confirm_product = State()
    product_qty = State()
    note = State()
    delivery_date = State()
    delivery_address = State()
    editing_product_choice = State()
    editing_product_qty = State()
    editing_details_choice = State()
    # флаг editing_mode хранится в state.data (editing_mode: True/False)


# ----------------- START / MANAGER / CLIENT -----------------
@dp.message(Command("start"))
async def start(msg: types.Message, state: FSMContext):
    await msg.answer("Добро пожаловать в Alanika OrderBot!👋🏻\nВведите ваше имя:")
    init_order(msg.from_user.id)
    await state.set_state(OrderState.manager)


@dp.message(OrderState.manager)
async def set_manager(msg: types.Message, state: FSMContext):
    update_order(msg.from_user.id, "manager", msg.text)
    await msg.answer("Введите имя клиента:")
    await state.set_state(OrderState.client)


@dp.message(OrderState.client)
async def set_client(msg: types.Message, state: FSMContext):
    update_order(msg.from_user.id, "client", msg.text)
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="Готово")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await msg.answer(
        "✅ Клиент сохранён.\nВведите последние 4️⃣ цифр кода товара или нажмите 'Готово', если товаров больше нет.",
        reply_markup=keyboard
    )
    await state.set_state(OrderState.product_code)



# ----------------- PRODUCT CODE -> show product card with inline confirm -----------------
# ----------------- PRODUCT CODE -> show product card with inline confirm -----------------
@dp.message(OrderState.product_code)
async def handle_product_code(msg: types.Message, state: FSMContext):
    # Если пользователь нажал "Готово"
    if msg.text.lower() == "готово":
        order = get_order(msg.from_user.id)
        if not order or not order.get("products"):
            await msg.answer("❌ Сначала добавьте хотя бы один товар.")
            return
        await msg.answer(
            "✏️ Укажите примечание для бухгалтера:", 
            reply_markup=types.ReplyKeyboardRemove()
        )
        await state.set_state(OrderState.note)
        return

    text = msg.text.strip()
    if not (text.isdigit() and len(text) == 4):
        await msg.answer("❗ Введите ровно 4️⃣ цифр кода товара.")
        return

    found_products = find_product_by_code_ending(text)
    if not found_products:
        await msg.answer("❌ Товар не найден. Проверьте код и попробуйте снова.")
        return
    elif len(found_products) == 1:
        product = found_products[0]
        await state.update_data(product=product)
        await show_product_card(msg, product, state)
        return

    # Если найдено несколько товаров, формируем inline-кнопки для выбора
    ikb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(
                text=f"{item['name']} (код {item['code']})",
                callback_data=f"select_product_{idx}"
            )] for idx, item in enumerate(found_products)
        ]
    )

    # Сохраняем список найденных товаров в state
    await state.update_data(found_products=found_products)
    await msg.answer("Найдено несколько товаров. Выберите нужный:", reply_markup=ikb)


# ----------------- CALLBACK: выбор товара из списка -----------------
@dp.callback_query(lambda c: c.data.startswith("select_product_"))
async def cb_select_product(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    data = await state.get_data()
    found_products = data.get("found_products", [])

    idx = int(call.data.split("_")[-1])
    if idx >= len(found_products):
        await call.message.answer("❌ Ошибка выбора товара. Попробуйте снова.")
        return

    product = found_products[idx]
    await state.update_data(product=product)
    await call.message.edit_reply_markup(None)  # удаляем кнопки выбора

    # Показ карточки товара с кнопками Добавить/Отменить
    await show_product_card(call.message, product, state)


# ----------------- Функция: показать карточку товара -----------------
async def show_product_card(msg_obj, product, state):
    info = (
        f"🔎 Найден товар:\n"
        f"📦 {product['name']}\n"
        f"📦 Остаток: {product['stock']}\n"
        f"🕐 Срок годности: {product['expiry']}\n"
        f"💶 Цена без НДС: {product['price_no_vat']} €\n"
        f"💶 Цена с НДС: {product['price_with_vat']} €\n\n"
        f"Добавить этот товар?"
    )
    ikb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="✅ Добавить", callback_data="add_product"),
                types.InlineKeyboardButton(text="❌ Отменить товар", callback_data="cancel_product"),
            ]
        ]
    )
    await msg_obj.answer(info, reply_markup=ikb)
    await state.set_state(OrderState.confirm_product)



# ----------------- Inline callbacks for add/cancel product -----------------
@dp.callback_query(lambda c: c.data == "add_product")
async def cb_add_product(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    # удаляем inline-клавиатуру у карточки (если возможно)
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await call.message.answer("Введите количество:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(OrderState.product_qty)


@dp.callback_query(lambda c: c.data == "cancel_product")
async def cb_cancel_product(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="Готово")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await call.message.answer("Товар не добавлен. Введите другой код товара или нажмите 'Готово'.", reply_markup=keyboard)
    await state.set_state(OrderState.product_code)


@dp.message(OrderState.confirm_product)
async def confirm_product_text(msg: types.Message, state: FSMContext):
    text = msg.text.strip().lower()
    if text in ("✅ добавить", "добавить", "да"):
        await msg.answer("Введите количество:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(OrderState.product_qty)
    elif text in ("❌ отменить товар", "отменить", "нет"):
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text="Готово")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await msg.answer("Товар не добавлен. Введите другой код товара или 'Готово'.", reply_markup=keyboard)
        await state.set_state(OrderState.product_code)
    else:
        await msg.answer("Выберите '✅ Добавить' или '❌ Отменить товар' (или нажмите inline-кнопки).")


# ----------------- PRODUCT QTY (adding product) -----------------
@dp.message(OrderState.product_qty)
async def handle_product_qty(msg: types.Message, state: FSMContext):
    if not msg.text.isdigit() or int(msg.text) <= 0:
        await msg.answer("❗ Введите корректное число больше нуля.")
        return

    data = await state.get_data()
    product = data.get("product")
    if not product:
        await msg.answer("❗ Внутренняя ошибка: товар не найден в сессии. Введите код товара заново.")
        await state.set_state(OrderState.product_code)
        return

    qty = int(msg.text)
    product["qty"] = qty
    product["sum_no_vat"] = round(float(product["price_no_vat"]) * qty, 2)
    product["sum_with_vat"] = round(float(product["price_with_vat"]) * qty, 2)
    product["code"] = product.get("code", "N/A")

    user_id = msg.from_user.id
    current = get_order(user_id)
    if not current:
        init_order(user_id)
        current = get_order(user_id)

    if "products" not in current or current["products"] is None:
        current["products"] = []

    # Проверяем, находимся ли мы в режиме редактирования (флаг editing_mode)
    data = await state.get_data()
    editing_mode = data.get("editing_mode", False)

    # Добавляем товар
    current["products"].append(product)
    update_order(user_id, "products", current["products"])

    if editing_mode:
        # Сбросим флаг и покажем предпросмотр (не переводя на note)
        await state.update_data(editing_mode=False)
        await send_order_preview(msg, user_id)
        await state.clear()
        return

    # Обычный рабочий поток — остаёмся в добавлении товаров
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="Готово")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await msg.answer("✅ Товар добавлен. Введите следующий код или нажмите 'Готово'.", reply_markup=keyboard)
    await state.set_state(OrderState.product_code)


# ----------------- NOTE / DELIVERY DATE / ADDRESS -----------------
@dp.message(OrderState.note)
async def handle_note(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    from_details = data.get("from_details_edit", False)

    update_order(msg.from_user.id, "note", msg.text)

    if from_details:
        # очистим флаг и вернём предпросмотр
        await state.update_data(from_details_edit=False)
        await send_order_preview(msg, msg.from_user.id)
        await state.clear()
        return

    await msg.answer("📅 Укажите дату доставки (например, 28.07):", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(OrderState.delivery_date)


@dp.message(OrderState.delivery_date)
async def handle_delivery_date(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    from_details = data.get("from_details_edit", False)

    update_order(msg.from_user.id, "delivery_date", msg.text)

    if from_details:
        await state.update_data(from_details_edit=False)
        await send_order_preview(msg, msg.from_user.id)
        await state.clear()
        return

    await msg.answer("🏢 Укажите адрес доставки:")
    await state.set_state(OrderState.delivery_address)


@dp.message(OrderState.delivery_address)
async def handle_delivery_address(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    from_details = data.get("from_details_edit", False)

    update_order(msg.from_user.id, "delivery_address", msg.text)

    if from_details:
        await state.update_data(from_details_edit=False)
        await send_order_preview(msg, msg.from_user.id)
        await state.clear()
        return

    # После ввода адреса показываем предпросмотр (как раньше)
    await send_order_preview(msg, msg.from_user.id)
    await state.clear()


# ----------------- SEND ORDER PREVIEW (INLINE BUTTONS) -----------------
async def send_order_preview(msg_obj: types.Message | types.CallbackQuery, user_id: int):
    """
    Отправляет предпросмотр заказа с 4 inline-кнопками:
    ✅ Подтвердить | ✏️ Изменить (товары) | 🛠 Редактировать детали | ❌ Отменить
    """
    # Получаем сообщение/чат куда отправлять
    if isinstance(msg_obj, types.CallbackQuery):
        chat_msg = msg_obj.message
    else:
        chat_msg = msg_obj

    order = get_order(user_id)
    if not order:
        await chat_msg.answer("Ошибка: заказ не найден.")
        return

    products_list = ""
    for i, item in enumerate(order.get("products", []), 1):
        products_list += (
            f"{i}) {item['name']} — {item['qty']} шт\n"
            f"   Срок: {item.get('expiry')}\n"
            f"   Цена без НДС: {item.get('price_no_vat')} € | с НДС: {item.get('price_with_vat')} €\n"
            f"   ➡️ Сумма: {item.get('sum_no_vat')} €\n\n"
        )

    preview = (
        f"🧾 Предпросмотр заказа:\n"
        f"👤 Менеджер: {order.get('manager')}\n"
        f"💎 Клиент: {order.get('client')}\n"
        f"📅 Доставка: {order.get('delivery_date')}\n"
        f"📍 Адрес: {order.get('delivery_address')}\n\n"
        f"📦 Товары:\n{products_list}"
        f"📋 Примечание: {order.get('note')}\n\n"
        f"✅ Всё верно — выберите действие:"
    )

    ikb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_order"),
                types.InlineKeyboardButton(text="⬅️ Товар", callback_data="edit_products_cb"),
            ],
            [
                types.InlineKeyboardButton(text="⬅️ Детали", callback_data="edit_details_cb"),
                types.InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_order_cb"),
            ]
        ]
    )

    # Отправляем предпросмотр (inline-кнопки под сообщением)
    await chat_msg.answer(preview, reply_markup=ikb)


# ----------------- Inline callbacks for preview actions -----------------
@dp.callback_query(lambda c: c.data == "confirm_order")
async def cb_confirm_order(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    user_id = call.from_user.id
    order = get_order(user_id)
    if not order:
        await call.message.answer("Ошибка: заказ не найден.")
        return

    import asyncio
    asyncio.create_task(asyncio.to_thread(send_order_email, order))
    asyncio.create_task(asyncio.to_thread(write_order_to_archive, order))
    write_order_to_archive(order)
    orders = load_orders()
    orders.pop(str(user_id), None)
    save_orders(orders)

    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    kb = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="Создать новый заказ")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await call.message.answer("✅ Заказ отправлен и сохранён в архив!", reply_markup=kb)
    await state.clear()


@dp.callback_query(lambda c: c.data == "cancel_order_cb")
async def cb_cancel_order(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    kb = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="Создать новый заказ")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await call.message.answer("❌ Заказ не отправлен. Вы можете начать заново.", reply_markup=kb)
    await state.clear()


@dp.callback_query(lambda c: c.data == "edit_products_cb")
async def cb_edit_products(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await show_edit_products(call.message, call.from_user.id, state)


@dp.callback_query(lambda c: c.data == "edit_details_cb")
async def cb_edit_details(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    # Показываем меню редактирования деталей
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="✏️ Редактировать примечание")],
            [types.KeyboardButton(text="✏️ Редактировать дату доставки")],
            [types.KeyboardButton(text="✏️ Редактировать адрес доставки")],
            [types.KeyboardButton(text="Отмена")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await call.message.answer("Выберите, что хотите изменить:", reply_markup=keyboard)
    await state.set_state(OrderState.editing_details_choice)


# ----------------- show edit products (used by callback and text command) -----------------
async def show_edit_products(chat_msg: types.Message, user_id: int, state: FSMContext):
    order = get_order(user_id)
    products = order.get("products", [])
    if not products:
        await chat_msg.answer("В заказе нет товаров для изменения.")
        return

    text = "✏️ Выберите номер товара для изменения:\n"
    for i, item in enumerate(products, 1):
        text += f"{i}) {item['name']} — {item['qty']} шт\n"

    # Создаём клавиатуру: кнопки с номерами + кнопка "➕ Добавить товар" и "Готово" и "Отмена"
    rows = [[types.KeyboardButton(text=str(i))] for i in range(1, len(products) + 1)]
    rows.append([types.KeyboardButton(text="➕ Добавить товар"), types.KeyboardButton(text="Готово")])
    rows.append([types.KeyboardButton(text="Отмена")])

    keyboard = types.ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=True)
    await chat_msg.answer(text, reply_markup=keyboard)
    # Устанавливаем состояние выбора товара и ставим флаг editing_mode
    await state.update_data(editing_mode=True)
    await state.set_state(OrderState.editing_product_choice)


# ----------------- text handler "✏️ Изменить" to open edit products (keeps compatibility) -----------------
@dp.message(lambda message: message.text and message.text.lower() == "✏️ изменить")
async def handle_edit_text(msg: types.Message, state: FSMContext):
    await show_edit_products(msg, msg.from_user.id, state)


# ----------------- choosing product or add new in edit mode -----------------
@dp.message(OrderState.editing_product_choice)
async def handle_editing_choice(msg: types.Message, state: FSMContext):
    text = msg.text.strip()
    order = get_order(msg.from_user.id)
    products = order.get("products", [])

    # Проверяем кнопки "Добавить"/"Готово"/"Отмена"
    if text == "➕ Добавить товар":
        # В режиме редактирования — устанавливаем флаг editing_mode (уже установлен), и просим код
        await state.update_data(editing_mode=True)
        await msg.answer("Введите последние 4️⃣ цифр кода нового товара:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(OrderState.product_code)
        return

    if text.lower() == "отмена":
        # Возвращаемся к предпросмотру
        await send_order_preview(msg, msg.from_user.id)
        await state.clear()
        return

    if text.lower() == "готово":
        # Завершили редактирование — показать предпросмотр
        await send_order_preview(msg, msg.from_user.id)
        await state.clear()
        return

    if not text.isdigit():
        await msg.answer("Введите номер товара из списка или нажмите '➕ Добавить товар' / 'Готово'.")
        return

    choice = int(text)
    if choice < 1 or choice > len(products):
        await msg.answer("Некорректный номер товара.")
        return

    # Сохраняем индекс редактируемого товара и просим новое количество
    await state.update_data(edit_index=choice - 1)
    await msg.answer("Введите новое количество (0 — удалить товар):", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(OrderState.editing_product_qty)


# ----------------- apply edited qty -> show preview (no redirect to note) -----------------
@dp.message(OrderState.editing_product_qty)
async def handle_editing_qty(msg: types.Message, state: FSMContext):
    if not msg.text.isdigit() or int(msg.text) < 0:
        await msg.answer("Введите корректное количество (0 или больше).")
        return
    qty = int(msg.text)
    data = await state.get_data()
    idx = data.get("edit_index")
    if idx is None:
        await msg.answer("Ошибка: индекс товара не найден. Попробуйте снова.")
        await state.set_state(OrderState.editing_product_choice)
        return

    order = get_order(msg.from_user.id)
    products = order.get("products", [])

    if idx < 0 or idx >= len(products):
        await msg.answer("Некорректный индекс товара.")
        await state.set_state(OrderState.editing_product_choice)
        return

    if qty == 0:
        products.pop(idx)
        await msg.answer("Товар удалён из заказа.")
    else:
        product = products[idx]
        product["qty"] = qty
        product["sum_no_vat"] = round(float(product["price_no_vat"]) * qty, 2)
        product["sum_with_vat"] = round(float(product["price_with_vat"]) * qty, 2)
        await msg.answer(f"Количество для товара '{product['name']}' изменено на {qty}.")

    update_order(msg.from_user.id, "products", products)

    # После редактирования — показать предпросмотр (без перехода к note)
    await send_order_preview(msg, msg.from_user.id)
    await state.clear()


# ----------------- editing details menu (text buttons chosen from preview) -----------------
@dp.message(lambda message: message.text and (
    message.text.lower() == "🛠 редактировать детали"
    or message.text.lower() == "✏️ редактировать примечание"
    or message.text.lower() == "✏️ редактировать дату доставки"
    or message.text.lower() == "✏️ редактировать адрес доставки"
))
async def handle_edit_details_text(msg: types.Message, state: FSMContext):
    text = msg.text.strip().lower()
    # Если нажали "🛠 редактировать детали" — покажем меню
    if text == "🛠 редактировать детали":
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="✏️ Редактировать примечание")],
                [types.KeyboardButton(text="✏️ Редактировать дату доставки")],
                [types.KeyboardButton(text="✏️ Редактировать адрес доставки")],
                [types.KeyboardButton(text="Отмена")],
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await msg.answer("Выберите, что хотите изменить:", reply_markup=keyboard)
        await state.set_state(OrderState.editing_details_choice)
        return

    # Если пользователь пришёл сюда напрямую (один из под-элементов) — перенаправим на соответствующий обработчик ниже
    await handle_editing_details_choice(msg, state)


@dp.message(OrderState.editing_details_choice)
async def handle_editing_details_choice(msg: types.Message, state: FSMContext):
    text = msg.text.strip().lower()
    if text == "✏️ редактировать примечание" or text == "редактировать примечание":
        await state.update_data(from_details_edit=True)
        await msg.answer("Введите новое примечание для бухгалтера:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(OrderState.note)
    elif text == "✏️ редактировать дату доставки" or text == "редактировать дату доставки":
        await state.update_data(from_details_edit=True)
        await msg.answer("Введите новую дату доставки (например, 28.07):", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(OrderState.delivery_date)
    elif text == "✏️ редактировать адрес доставки" or text == "редактировать адрес доставки":
        await state.update_data(from_details_edit=True)
        await msg.answer("Введите новый адрес доставки:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(OrderState.delivery_address)
    elif text == "отмена":
        await send_order_preview(msg, msg.from_user.id)
        await state.clear()
    else:
        await msg.answer("Выберите один из пунктов меню: редактировать примечание/дату/адрес или 'Отмена'.")


# ----------------- legacy text handlers for confirm/cancel/create new order as fallback -----------------
@dp.message(lambda message: message.text and message.text.lower() == "✅ подтвердить")
async def handle_submit_text(msg: types.Message, state: FSMContext):
    # текстовый эквивалент кнопки подтверждения (на случай, если inline не используются)
    user_id = msg.from_user.id
    order = get_order(user_id)
    if not order:
        await msg.answer("Ошибка: заказ не найден.")
        return

    import asyncio
    asyncio.create_task(asyncio.to_thread(send_order_email, order))
    asyncio.create_task(asyncio.to_thread(write_order_to_archive, order))
    write_order_to_archive(order)
    orders = load_orders()
    orders.pop(str(user_id), None)
    save_orders(orders)

    kb = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="Создать новый заказ")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await msg.answer("✅ Заказ отправлен бухгалтеру!", reply_markup=kb)
    await state.clear()


@dp.message(lambda message: message.text and message.text.lower() == "❌ отменить")
async def handle_cancel_text(msg: types.Message, state: FSMContext):
    kb = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="Создать новый заказ")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await msg.answer("❌ Заказ не отправлен. Вы можете начать заново.", reply_markup=kb)
    await state.clear()


@dp.message(lambda message: message.text and message.text.lower() == "создать новый заказ")
async def handle_new_order(msg: types.Message, state: FSMContext):
    init_order(msg.from_user.id)
    await msg.answer("Начнём новый заказ!\nВведите ваше имя:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(OrderState.manager)


# ----------------- MAIN -----------------
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
