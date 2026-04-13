from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, ReactionTypeEmoji)
from contextlib import suppress
from aiogram.exceptions import TelegramBadRequest
import logging

from app.models import User, Request, RequestFile

from app.config import PRICE

from app.keyboard.keyboards import (
    level_1_categories, private_submenu, business_submenu,
    gov_submenu, law_violation_submenu,
    client_gathering_files_kb, payment_kb, main_menu
)

from aiogram.fsm.context import FSMContext
from app.states import ClientState


from app.payment.payments import create_invoice
from aiogram.utils.keyboard import InlineKeyboardBuilder

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
router = Router()


@router.callback_query(F.data == "ask")
async def ask_category(callback: CallbackQuery):
    await callback.message.edit_text(
        "Оберіть сферу права:",
        reply_markup=level_1_categories()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("menu:"))
async def show_submenu(callback: CallbackQuery):
    menu_type = callback.data.split(":")[1]
    text = "Оберіть підкатегорію:"
    markup = None
    if menu_type == "private":
        text = "📍 Приватні справи"
        markup = private_submenu()
    elif menu_type == "business":
        text = "💼 Бізнес та ФОП"
        markup = business_submenu()
    elif menu_type == "gov":
        text = "🏛️ Держава та органи"
        markup = gov_submenu()
    elif menu_type == "law_violation":
        text = "⚖️ Порушення закону"
        markup = law_violation_submenu()
    if markup:
        await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data.startswith("cat:"))
async def set_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split("cat:")[1]

    await state.set_state(ClientState.gathering_question)

    # 2. Зберігаємо початкові дані в FSM (Redis)
    await state.update_data(
        category=category,
        files=[],
        file_ids=[],  # Використовуємо список замість set()
        question_text=""
    )
    await callback.message.edit_text(
        f"Ви обрали: *{category}*\n\n"
        f"Тепер, будь ласка, надішліть сюди:\n"
        f"1. Текст вашого питання (одним повідомленням).\n"
        f"2. Усі необхідні файли/фото (можна окремо або альбомом).\n\n"
        f"👇 Коли все надішлете, натисніть кнопку 'Готово' нижче.",
        reply_markup=client_gathering_files_kb()
    )
    await callback.answer()


# === ЕТАП 3: ОБРОБКА ВСІХ ОСОБИСТИХ ПОВІДОМЛЕНЬ ===
@router.message(ClientState.gathering_question, F.chat.type == "private", ~F.successful_payment)
async def client_message(message: Message, state: FSMContext):
    # Дістаємо поточні дані з Redis/Пам'яті
    data = await state.get_data()

    question_text = data.get("question_text", "")
    files = data.get("files", [])
    file_ids = data.get("file_ids", [])

    file_saved = False
    text_saved = False

    if message.text:
        # Якщо клієнт надіслав ще один текст, додаємо його з нового рядка
        question_text += (message.text + "\n")
        text_saved = True
    elif message.caption:
        question_text += (message.caption + "\n")
        text_saved = True

    if text_saved:
        with suppress(TelegramBadRequest):
            await message.react([ReactionTypeEmoji(emoji="📝")])

    if message.photo:
        file_id = message.photo[-1].file_id
        if file_id not in file_ids:
            files.append({"type": "photo", "file_id": file_id})
            file_ids.append(file_id)
            file_saved = True

    if message.document:
        file_id = message.document.file_id
        if file_id not in file_ids:
            files.append({"type": "document", "file_id": file_id})
            file_ids.append(file_id)
            file_saved = True

    if file_saved:
        with suppress(TelegramBadRequest):
            await message.react([ReactionTypeEmoji(emoji="👍")])

    if not text_saved and not file_saved:
        logging.info(f"Ignoring unsupported message type from client {message.from_user.id}")
        return

    # Зберігаємо оновлені дані назад у стан
    await state.update_data(
        question_text=question_text,
        files=files,
        file_ids=file_ids
    )


@router.callback_query(ClientState.gathering_question, F.data == "done_adding_files")
async def done_adding_files(callback: CallbackQuery, state: FSMContext,
                            session_maker: async_sessionmaker[AsyncSession]):
    # Читаємо дані зі стану
    data = await state.get_data()
    category = data.get("category")
    question_text = data.get("question_text", "").strip()
    files = data.get("files", [])

    if not question_text and not files:
        return await callback.answer("⚠️ Ви не додали ані тексту, ані файлів.", show_alert=True)

    user_id = callback.from_user.id

    try:
        async with session_maker() as session:
            user = await session.get(User, user_id)
            if not user:
                user = User(
                    user_id=user_id,
                    username=callback.from_user.username,
                    full_name=callback.from_user.full_name
                )
                session.add(user)

            new_request = Request(
                category=category,
                question_text=question_text,
                client_id=user_id
            )
            session.add(new_request)
            await session.commit()

            files_to_add = []
            for file_data in files:
                files_to_add.append(
                    RequestFile(
                        request_id=new_request.id,
                        file_id=file_data["file_id"],
                        file_type=file_data["type"]
                    )
                )
            if files_to_add:
                session.add_all(files_to_add)
                await session.commit()

            new_req_id = new_request.id
    except Exception as e:
        logging.error(f"Помилка створення 'pending_payment' запиту в БД: {e}")
        await callback.message.edit_text("⚠️ Виникла серйозна помилка. Адміністратора сповіщено.",
                                         reply_markup=main_menu())
        await callback.answer()
        return None

    # ОЧИЩАЄМО СТАН! Клієнт завершив формування запиту
    await state.clear()

    await callback.message.edit_text(
        f"✅ Добре! Ваш запит #{new_req_id} по категорії '{category}' готовий до відправки.\n"
        f"Текст: {'Так' if question_text else 'Ні'}\n"
        f"Файли: {len(files)} шт.\n\n"
        "⏳ Увага! Важливий крок.\n"
        "Наш спеціалізований адвокат надає відповіді на ваші питання в рамках платної консультації.\n"
        f"❇️Вартість консультації: {PRICE} гривень\n"
        f"Що ви отримаєте за {PRICE} грн:\n"
        "* Чітку, обґрунтовану відповідь від практикуючого адвоката\n"
        "* Посилання на відповідні норми закону (за потреби)\n"
        "* Покроковий алгоритм дій у вашій ситуації\n\n"
        "Надання відповіді гарантоване протягом 24 годин (зазвичай швидше).\n\n"
        "> Продовжуємо?\n"
        "Тисни оплатити на обирай зручний спосіб",
        reply_markup=payment_kb(req_id=new_req_id),
        parse_mode=None
    )
    await callback.answer()
    return None


# === ЕТАП 5: Клієнт натиснув "Оплатити" ===
@router.callback_query(F.data.startswith("pay:"))
async def send_payment_link(callback: CallbackQuery, session_maker: async_sessionmaker[AsyncSession]):
    req_id = int(callback.data.split(":")[1])

    async with session_maker() as session:
        request = await session.get(Request, req_id)
        if not request:
            return await callback.answer("⚠️ Запит не знайдено.", show_alert=True)
        if request.status != 'pending_payment':
            return await callback.answer(f"⚠️ Статус: {request.status}", show_alert=True)

        category = request.category

    # Показуємо користувачу, що ми думаємо (генеруємо посилання)
    await callback.message.edit_text("⏳ Генерую посилання на оплату...")

    desc = f"Consultation #{req_id} ({category})"

    # (ОСЬ ТУТ ЗМІНА) Викликаємо нову асинхронну функцію
    link = await create_invoice(req_id, PRICE, desc)

    if link:
        kb = InlineKeyboardBuilder()
        kb.button(text=f"💳 Перейти до оплати ({PRICE} грн)", url=link)

        await callback.message.edit_text(
            f"✅ Рахунок сформовано.\n"
            f"Для оплати запиту *#{req_id}* натисніть кнопку нижче.",
            reply_markup=kb.as_markup()
        )
    else:
        await callback.message.edit_text(
            "⚠️ Помилка платіжної системи. Спробуйте пізніше або зверніться до адміністратора.",
            reply_markup=main_menu()
        )

    await callback.answer()
    return None


@router.callback_query(F.data.startswith("cancel_payment:"))
async def cancel_payment(callback: CallbackQuery, session_maker: async_sessionmaker[AsyncSession]):
    req_id = int(callback.data.split(":")[1])
    try:
        async with session_maker() as session:
            request = await session.get(Request, req_id)
            if request and request.status == 'pending_payment':
                request.status = 'cancelled'
                await session.commit()
            await callback.message.edit_text(f"❌ Запит #{req_id} скасовано.", reply_markup=main_menu())
    except Exception as e:
        logging.error(f"Помилка скасування запиту #{req_id}: {e}")
        await callback.answer("⚠️ Помилка скасування.", show_alert=True)
    await callback.answer()