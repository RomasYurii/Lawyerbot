from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.config import PRICE

# --- ГОЛОВНЕ МЕНЮ ---
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Задати питання", callback_data="ask")],
        [InlineKeyboardButton(text="📂 Мої звернення", callback_data="my_requests")],
        [InlineKeyboardButton(text="ℹ️ Допомога / Контакти", callback_data="help")]
    ])

# --- КНОПКА НАЗАД ---
def get_back_to_categories_button():
    return InlineKeyboardButton(text="⬅️ Назад", callback_data="ask")

# --- КАТЕГОРІЇ (РІВЕНЬ 1) ---
def level_1_categories():
    kb = InlineKeyboardBuilder()
    kb.button(text="Приватні справи", callback_data="menu:private")
    kb.button(text="Бізнес та ФОП", callback_data="menu:business")
    kb.button(text="Держава та органи", callback_data="menu:gov")
    kb.button(text="Порушення закону", callback_data="menu:law_violation")
    kb.button(text="Військове право", callback_data="cat:Військове право")
    kb.adjust(2, 2, 1)
    return kb.as_markup()

# --- ПІДМЕНЮ (РІВЕНЬ 2) ---
def private_submenu():
    kb = InlineKeyboardBuilder()
    kb.button(text="Сімейне", callback_data="cat:Сімейне")
    kb.button(text="Цивільне", callback_data="cat:Цивільне")
    kb.button(text="Спадщина", callback_data="cat:Спадщина")
    kb.row(get_back_to_categories_button())
    kb.adjust(3)
    return kb.as_markup()

def business_submenu():
    kb = InlineKeyboardBuilder()
    kb.button(text="Господарське", callback_data="cat:Господарське")
    kb.button(text="Податкове", callback_data="cat:Податкове")
    kb.button(text="Трудове", callback_data="cat:Трудове")
    kb.row(get_back_to_categories_button())
    kb.adjust(3)
    return kb.as_markup()

def gov_submenu():
    kb = InlineKeyboardBuilder()
    kb.button(text="Адміністративне", callback_data="cat:Адміністративне")
    kb.button(text="Земельне", callback_data="cat:Земельне")
    kb.row(get_back_to_categories_button())
    kb.adjust(2)
    return kb.as_markup()

def law_violation_submenu():
    kb = InlineKeyboardBuilder()
    kb.button(text="Кримінальне", callback_data="cat:Кримінальне")
    kb.button(text="Адміністративне (штрафи)", callback_data="cat:Адміністративне (штрафи)")
    kb.row(get_back_to_categories_button())
    kb.adjust(2)
    return kb.as_markup()

# --- КНОПКИ ДЛЯ ЗБОРУ ФАЙЛІВ ---
def client_gathering_files_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Готово (я надіслав все)", callback_data="done_adding_files")],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel")]
    ])

# --- КНОПКИ ОПЛАТИ ---
# Ця функція тепер приймає req_id
def payment_kb(req_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        # Кнопка веде на хендлер pay:ID, який вже видасть посилання WayForPay
        [InlineKeyboardButton(text=f"💳 Оплатити {PRICE} грн", callback_data=f"pay:{req_id}")],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data=f"cancel_payment:{req_id}")]
    ])

# --- КНОПКИ ДЛЯ ЮРИСТА ---
def lawyer_take_request_kb(req_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="🔹 Взяти в роботу", callback_data=f"take:{req_id}")
    return kb.as_markup()

def lawyer_send_reply_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Надіслати відповідь клієнту", callback_data="send_reply_to_client")]
    ])