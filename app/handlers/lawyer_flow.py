from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InputMediaPhoto, InputMediaDocument
import logging
from aiogram.fsm.storage.base import StorageKey
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models import User, Request, Reply, ReplyFile
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.keyboard.keyboards import lawyer_send_reply_kb, main_menu
from app.handlers.messaging import send_files_to_lawyer_pm

from aiogram.fsm.context import FSMContext
from app.states import LawyerState

from aiogram.types import Message, ReactionTypeEmoji
from contextlib import suppress
from aiogram.exceptions import TelegramBadRequest

router = Router()
#user_state = {}

# === (ОНОВЛЕНО) Юрист натиснув "Взяти в роботу" ===
@router.callback_query(F.data.startswith("take:"))
async def take_request(callback: CallbackQuery, bot: Bot, session_maker: async_sessionmaker[AsyncSession], state: FSMContext):
    lawyer_chat_id = callback.from_user.id
    req_id = int(callback.data.split(":")[1])


    async with session_maker() as session:
        lawyer_user = await session.get(User, lawyer_chat_id)
        if not lawyer_user:
            lawyer_user = User(
                user_id=lawyer_chat_id,
                username=callback.from_user.username,
                full_name=callback.from_user.full_name
            )
            session.add(lawyer_user)

        result = await session.execute(
            select(Request)
            .where(Request.id == req_id)
            .options(selectinload(Request.files))
        )
        request = result.scalar_one_or_none()

        if not request:
            return await callback.answer("⚠️ Цей запит вже неактуальний.", show_alert=True)

        if request.lawyer_id:
            if request.lawyer_id == lawyer_chat_id:
                return await callback.answer("Ви вже взяли цей запит.", show_alert=True)
            other_lawyer = await session.get(User, request.lawyer_id)
            username = other_lawyer.username if other_lawyer else "інший юрист"
            return await callback.answer(f"⚠️ Вже в роботі у @{username}", show_alert=True)

        request.lawyer_id = lawyer_chat_id
        request.status = "in_progress"
        request.taken_at = func.now()

        await session.commit()

        # (ОНОВЛЕНО) Витягуємо файли для перевірки
        request_files = request.files
        request_data_dict = {
            "category": request.category,
            "question": request.question_text,
            "files": request_files  # request.files - це список об'єктів RequestFile
        }

    await callback.message.edit_text(
        callback.message.text + f"\n\n✅ *В роботі у @{lawyer_user.username or lawyer_user.full_name}*",
        reply_markup=None
    )

    # ❗ СТВОРЮЄМО СТЕЙТ ДЛЯ ОСОБИСТИХ ПОВІДОМЛЕНЬ ЮРИСТА
    state_pm = FSMContext(
        storage=state.storage,
        key=StorageKey(
            bot_id=bot.id,
            chat_id=lawyer_chat_id,  # ID приватного чату юриста
            user_id=lawyer_chat_id  # ID самого юриста
        )
    )

    # Очищаємо можливий старий стан в особистих повідомленнях
    await state_pm.clear()

    # Зберігаємо дані в ПРИВАТНИЙ стейт
    await state_pm.update_data(
        req_id=req_id,
        reply_text="",
        reply_files=[],
        file_ids=[]
    )

    # Встановлюємо стан відповіді ТАМ (в PM)
    await state_pm.set_state(LawyerState.replying)

    # 1. Готуємо перше повідомлення
    info_text = (
        f"🧑‍⚖️ Ви взяли запит *#{req_id}* в роботу.\n\n"
        f"⚖️ *Категорія:* {request_data_dict['category']}\n"
        f"❓ *Питання клієнта:*\n{request_data_dict.get('question', 'Немає тексту')}"
    )

    if request_files:
        info_text += "\n\nЗараз надішлю всі файли від клієнта. 👇"

    await bot.send_message(lawyer_chat_id, info_text)

    # 2. Надсилаємо файли
    if request_files:
        await send_files_to_lawyer_pm(bot, lawyer_chat_id, req_id, request_data_dict)

    # 3. Готуємо фінальну інструкцію
    if request_files:
        final_instruction_text = (
            f"👆 *Це всі матеріали.* \n"
            f"Тепер надішліть сюди вашу відповідь: можна кількома повідомленнями (текст, фото, документи).\n\n"
            f"Коли закінчите, натисніть кнопку 'Надіслати відповідь' 👇"
        )
    else:
        final_instruction_text = (
            f"👆 *Файлів від клієнта не було.* \n"
            f"Надішліть сюди вашу відповідь: можна кількома повідомленнями (текст, фото, документи).\n\n"
            f"Коли закінчите, натисніть кнопку 'Надіслати відповідь' 👇"
        )

    await bot.send_message(
        lawyer_chat_id,
        final_instruction_text,
        reply_markup=lawyer_send_reply_kb()
    )

    # Зверніть увагу: ми ВИДАЛИЛИ звідси старі state.clear() і state.set_state()

    await callback.answer()
    return None


# === (ОНОВЛЕНО) Юрист натиснув "Надіслати відповідь" ===
@router.callback_query(LawyerState.replying, F.data == "send_reply_to_client")
async def send_reply_to_client(callback: CallbackQuery, bot: Bot, session_maker: async_sessionmaker[AsyncSession], state: FSMContext):
    lawyer_chat_id = callback.from_user.id

    await callback.answer()
    # 1. ЧИТАЄМО ДАНІ (Ось заміна user_state.get!)

    data = await state.get_data()

    req_id = data.get("req_id")
    reply_text = data.get("reply_text", "").strip()
    reply_files = data.get("reply_files", [])

    if not reply_text and not reply_files:
        return await callback.answer("⚠️ Ви не додали ані тексту, ані файлів.", show_alert=True)

    # --- (ОНОВЛЕНА ЛОГІКА ДЛЯ ЗАПИТУ 1) ---
    # 1. Надсилаємо НОВЕ повідомлення про статус (замість редагування)
    status_msg = await callback.message.answer("⏳ Зберігаю відповідь та надсилаю клієнту...")



    # 2. "Закриваємо" годинник на кнопці, яку натиснув юрист
    await callback.answer()

    try:
        async with session_maker() as session:
            request = await session.get(Request, req_id)
            if not request:
                await status_msg.edit_text("⚠️ Запит вже неактуальний.", reply_markup=main_menu())
                return None

            lawyer = await session.get(User, lawyer_chat_id)
            lawyer_username = lawyer.username if lawyer else "Юрист"
            client_user_id = request.client_id

            # Створюємо Відповідь (Reply)
            new_reply = Reply(
                request_id=req_id,
                reply_text=reply_text
            )
            session.add(new_reply)
            await session.commit()

            # Створюємо Файли Відповіді (ReplyFile)
            files_to_add = []
            for file_data in reply_files:
                files_to_add.append(
                    ReplyFile(
                        reply_id=new_reply.id,
                        file_id=file_data["file_id"],
                        file_type=file_data["type"]
                    )
                )
            if files_to_add:
                session.add_all(files_to_add)

            request.status = "completed"
            await session.commit()

        # --- (БЕЗ ЗМІН) Надсилаємо відповідь клієнту ---
        await bot.send_message(client_user_id,
                               f"📬 Ви отримали відповідь на запит *#{req_id}* від юриста @{lawyer_username}:"
                               )

        if reply_text:
            # Використовуємо parse_mode=None для надійності
            await bot.send_message(client_user_id, reply_text, parse_mode=None)

        photos = [f for f in reply_files if f["type"] == "photo"]
        docs = [f for f in reply_files if f["type"] == "document"]

        if photos:
            media_group_photo = [InputMediaPhoto(media=p["file_id"]) for p in photos]
            for i in range(0, len(media_group_photo), 10):
                batch = media_group_photo[i:i + 10]
                if len(batch) > 1:
                    await bot.send_media_group(chat_id=client_user_id, media=batch)
                elif len(batch) == 1:
                    await bot.send_photo(chat_id=client_user_id, photo=batch[0].media)

        if docs:
            media_group_doc = [InputMediaDocument(media=d["file_id"]) for d in docs]
            for i in range(0, len(media_group_doc), 10):
                batch = media_group_doc[i:i + 10]
                if len(batch) > 1:
                    await bot.send_media_group(chat_id=client_user_id, media=batch)
                elif len(batch) == 1:
                    await bot.send_document(chat_id=client_user_id, document=batch[0].media)

        # (ОНОВЛЕНО) Редагуємо наше повідомлення про статус
        await status_msg.edit_text("✔️ Вашу відповідь успішно надіслано та збережено.")

    except Exception as e:
        logging.error(f"Failed to send/save reply for req #{req_id}: {e}")
        # (ОНОВЛЕНО) Редагуємо наше повідомлення про статус
        await status_msg.edit_text(
            "⚠️ Сталася помилка. Не вдалося надіслати відповідь. "
            "Спробуйте зв'язатися з адміністратором.",
            reply_markup=main_menu()
        )

    # Скидаємо стан юриста
    await state.clear()
    return None

@router.message(LawyerState.replying, F.chat.type == "private")
async def lawyer_reply_message(message: Message, state: FSMContext):
    data = await state.get_data()

    reply_text = data.get("reply_text", "")
    reply_files = data.get("reply_files", [])
    file_ids = data.get("file_ids", [])

    file_saved = False
    text_saved = False

    if message.text:
        reply_text += (message.text + "\n")
        text_saved = True
    elif message.caption:
        reply_text += (message.caption + "\n")
        text_saved = True

    if text_saved:
        with suppress(TelegramBadRequest):
            await message.react([ReactionTypeEmoji(emoji="📝")])

    if message.photo:
        file_id = message.photo[-1].file_id
        if file_id not in file_ids:
            reply_files.append({"type": "photo", "file_id": file_id})
            file_ids.append(file_id)
            file_saved = True

    if message.document:
        file_id = message.document.file_id
        if file_id not in file_ids:
            reply_files.append({"type": "document", "file_id": file_id})
            file_ids.append(file_id)
            file_saved = True

    if file_saved:
        with suppress(TelegramBadRequest):
            await message.react([ReactionTypeEmoji(emoji="👍")])

    if not text_saved and not file_saved:
        return

    # Зберігаємо оновлені дані назад у стан
    await state.update_data(
        reply_text=reply_text,
        reply_files=reply_files,
        file_ids=file_ids
    )