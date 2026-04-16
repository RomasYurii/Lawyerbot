import logging
from aiogram import Bot
from aiogram.types import InputMediaPhoto, InputMediaDocument
from aiogram.exceptions import TelegramBadRequest
from contextlib import suppress

from app.config import LAWYERS_CHAT_ID

from app.keyboard.keyboards import lawyer_take_request_kb


async def send_request_to_group(bot: Bot, req_id: int, data: dict, user_info: dict) -> bool:
    """
    Надсилає фіналізований запит (текст + файли) у групу юристів.
    Повертає True у разі успіху, False - у разі помилки.

    :param bot: Екземпляр Bot
    :param req_id: ID нового запиту
    :param data: Словник з даними запиту (category, question, files)
    :param user_info: Словник з даними клієнта (id, username, full_name)
    """

    caption = (
        f"📩 *Новий запит #{req_id}*\n"
        f"👤 Від користувача: @{user_info.get('username') or user_info.get('full_name')} (ID: `{user_info.get('id')}`)\n"
        f"⚖️ Категорія: {data.get('category')}\n\n"
        f"❓ *Питання:*\n{data.get('question', 'Немає тексту (див. файли)')}"
    )

    files = data.get("files", [])
    photos = [f for f in files if f["type"] == "photo"]
    docs = [f for f in files if f["type"] == "document"]

    try:
        main_message = await bot.send_message(
            LAWYERS_CHAT_ID,
            caption,
            reply_markup=lawyer_take_request_kb(req_id)
        )

        reply_to_msg_id = main_message.message_id
        message_thread_id = main_message.message_thread_id if main_message.is_topic_message else None

        if photos:
            media_group_photo = [InputMediaPhoto(media=p["file_id"]) for p in photos]
            for i in range(0, len(media_group_photo), 10):
                batch = media_group_photo[i:i + 10]
                if len(batch) > 1:
                    await bot.send_media_group(
                        chat_id=LAWYERS_CHAT_ID,
                        media=batch,
                        message_thread_id=message_thread_id,
                        reply_to_message_id=reply_to_msg_id
                    )
                elif len(batch) == 1:
                    await bot.send_photo(
                        chat_id=LAWYERS_CHAT_ID,
                        photo=batch[0].media,
                        message_thread_id=message_thread_id,
                        reply_to_message_id=reply_to_msg_id
                    )

        if docs:
            media_group_doc = [InputMediaDocument(media=d["file_id"]) for d in docs]
            for i in range(0, len(media_group_doc), 10):
                batch = media_group_doc[i:i + 10]
                if len(batch) > 1:
                    await bot.send_media_group(
                        chat_id=LAWYERS_CHAT_ID,
                        media=batch,
                        message_thread_id=message_thread_id,
                        reply_to_message_id=reply_to_msg_id
                    )
                elif len(batch) == 1:
                    await bot.send_document(
                        chat_id=LAWYERS_CHAT_ID,
                        document=batch[0].media,
                        message_thread_id=message_thread_id,
                        reply_to_message_id=reply_to_msg_id
                    )

        return True

    except Exception as e:
        logging.error(f"Помилка відправки в чат юристів запиту #{req_id}: {e}")
        return False


async def send_files_to_lawyer_pm(bot: Bot, lawyer_chat_id: int, req_id: int, data: dict):
    """
    Надсилає матеріали справи (файли) юристу в особисті повідомлення.

    :param req_id:
    :param lawyer_chat_id:
    :param bot:
    :param data: Словник з даними, ключ 'files' містить список об'єктів RequestFile
    """

    files = data.get("files", [])
    photos = [f for f in files if f.file_type == "photo"]
    docs = [f for f in files if f.file_type == "document"]

    try:
        if photos:
            media_group_photo = [InputMediaPhoto(media=f.file_id) for f in photos]
            for i in range(0, len(media_group_photo), 10):
                batch = media_group_photo[i:i + 10]
                if len(batch) > 1:
                    await bot.send_media_group(chat_id=lawyer_chat_id, media=batch)
                elif len(batch) == 1:
                    await bot.send_photo(chat_id=lawyer_chat_id, photo=batch[0].media)

        if docs:
            media_group_doc = [InputMediaDocument(media=f.file_id) for f in docs]
            for i in range(0, len(media_group_doc), 10):
                batch = media_group_doc[i:i + 10]
                if len(batch) > 1:
                    await bot.send_media_group(chat_id=lawyer_chat_id, media=batch)
                elif len(batch) == 1:
                    await bot.send_document(chat_id=lawyer_chat_id, document=batch[0].media)

    except Exception as e:
        logging.error(f"Помилка відправки файлів юристу {lawyer_chat_id} для запиту #{req_id}: {e}")
        with suppress(TelegramBadRequest):
            await bot.send_message(lawyer_chat_id,
                                   "⚠️ Не вдалося завантажити файли клієнта. Зверніться до адміністратора.")