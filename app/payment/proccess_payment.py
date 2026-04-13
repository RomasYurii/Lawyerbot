import logging
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from aiogram import Bot
import time
import functions_framework
import asyncio
import json


from app.config import BOT_TOKEN
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.payment.payments import get_wfp_signature
from app.handlers.messaging import send_request_to_group
from app.models import Request, User
from app.database import async_session_maker


async def process_successful_payment(req_id: int, amount: float, bot: Bot):
    """
    Викликається при отриманні Approved статусу від WayForPay
    """
    async with async_session_maker() as session:
        # Витягуємо запит відразу з прив'язаними файлами, щоб не робити зайвих запитів
        stmt = select(Request).where(Request.id == req_id).options(
            selectinload(Request.files)
        )
        result = await session.execute(stmt)
        db_request = result.scalar_one_or_none()

        if not db_request:
            logging.error(f"Запит #{req_id} не знайдено при обробці оплати.")
            return

        # Захист від дублювання вебхуків
        if db_request.status == 'paid':
            logging.info(f"Запит #{req_id} вже був позначений як оплачений.")
            return

        # Оновлюємо статус
        db_request.status = 'paid'

        # Витягуємо інформацію про клієнта
        client = await session.get(User, db_request.client_id)

        await session.commit()

        # 1. Формуємо user_info
        user_info = {
            "id": client.user_id,
            "username": client.username,
            "full_name": client.full_name
        }

        # 2. Формуємо data (перетворюємо об'єкти БД у словники для твоєї функції)
        files_list = [
            {"type": f.file_type, "file_id": f.file_id}
            for f in db_request.files
        ]

        data = {
            "category": db_request.category,
            "question": db_request.question_text,
            "files": files_list
        }

        # 3. Відправляємо в групу юристів через твою готову функцію!
        success = await send_request_to_group(bot, req_id, data, user_info)

        if success:
            logging.info(f"Запит #{req_id} успішно відправлено в групу юристів.")
        else:
            logging.error(f"Не вдалося відправити запит #{req_id} в групу.")

        # 4. Сповіщаємо клієнта про успішну оплату
        try:
            await bot.send_message(
                chat_id=client.user_id,
                text=(
                    f"🎉 Оплату ({amount} грн) успішно отримано!\n\n"
                    f"Ваш запит <b>#{req_id}</b> передано адвокатам. "
                    f"Очікуйте на відповідь."
                ),
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"Не вдалося сповістити клієнта {client.user_id}: {e}")


@functions_framework.http
def wfp_webhook_handler(request):
    # 1. Витягуємо "сирі" дані як текст, ігноруючи заголовки
    raw_data = request.get_data(as_text=True)
    logging.warning(f"Сирі дані від WFP: {raw_data}") # Виведемо в консоль для діагностики

    # 2. Намагаємося розпарсити їх вручну
    try:
        data = json.loads(raw_data) if raw_data else {}
    except json.JSONDecodeError:
        # Якщо це не чистий JSON, пробуємо витягти як форму
        data = request.form.to_dict()

    # Якщо даних зовсім немає
    if not data:
         logging.error("Помилка: WayForPay надіслав порожній запит.")
         return {"error": "Invalid JSON"}, 400

    logging.info(f"Отримано вебхук від WFP: {data}")

    order_ref = data.get("orderReference")
    status = data.get("transactionStatus")
    # Щоб уникнути помилки, якщо amount приходить як рядок або відсутній:
    amount = float(data.get("amount", 0))

    try:
        req_id = int(order_ref.split("_")[0])
    except (ValueError, AttributeError, IndexError):
         logging.error(f"Некоректний orderReference: {order_ref}")
         return {"error": "Invalid orderReference"}, 400

    # 2. Якщо оплата успішна — викликаємо нашу логіку!
    if status == "Approved":
        # Створюємо реальний екземпляр бота за допомогою твого токену
        bot_instance = Bot(
            token=BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
        )

        # Оскільки GCF синхронні, а бот і БД асинхронні, запускаємо через asyncio.run
        asyncio.run(process_successful_payment(
            req_id=req_id,
            amount=amount,
            bot=bot_instance  # Передаємо створений об'єкт!
        ))
    elif status == "Declined":
        # Тут можна додати логіку для відхилених платежів (наприклад, написати клієнту)
        logging.info(f"Оплату для запиту #{req_id} відхилено.")

    # 3. ФОРМУЄМО ОБОВ'ЯЗКОВУ ВІДПОВІДЬ ДЛЯ WAYFORPAY
    # Щоб вони зрозуміли, що ми прийняли статус, і не спамили нас повторними запитами
    current_time = int(time.time())
    response_status = "accept"

    sign_str = f"{order_ref};{response_status};{current_time}"
    signature = get_wfp_signature(sign_str)  # Твоя функція з payments.py

    # GCF автоматично перетворить цей словник у JSON-відповідь
    return {
        "orderReference": order_ref,
        "status": response_status,
        "time": current_time,
        "signature": signature
    }