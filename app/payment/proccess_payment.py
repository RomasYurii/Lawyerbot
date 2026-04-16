import logging
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from aiogram import Bot
import time
import json
from aiohttp import web

from app.payment.payments import get_wfp_signature
from app.handlers.messaging import send_request_to_group
from app.models import Request, User
from app.database import async_session_maker


async def process_successful_payment(req_id: int, amount: float, bot: Bot):
    """
    Викликається при отриманні Approved статусу від WayForPay
    """
    async with async_session_maker() as session:
        stmt = select(Request).where(Request.id == req_id).options(
            selectinload(Request.files)
        )
        result = await session.execute(stmt)
        db_request = result.scalar_one_or_none()

        if not db_request:
            logging.error(f"Запит #{req_id} не знайдено при обробці оплати.")
            return

        if db_request.status == 'paid':
            logging.info(f"Запит #{req_id} вже був позначений як оплачений.")
            return

        db_request.status = 'paid'

        client = await session.get(User, db_request.client_id)

        await session.commit()

        user_info = {
            "id": client.user_id,
            "username": client.username,
            "full_name": client.full_name
        }

        files_list = [
            {"type": f.file_type, "file_id": f.file_id}
            for f in db_request.files
        ]

        data = {
            "category": db_request.category,
            "question": db_request.question_text,
            "files": files_list
        }

        success = await send_request_to_group(bot, req_id, data, user_info)

        if success:
            logging.info(f"Запит #{req_id} успішно відправлено в групу юристів.")
        else:
            logging.error(f"Не вдалося відправити запит #{req_id} в групу.")

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


async def wfp_webhook_handler(request: web.Request):
    raw_data = await request.text()
    logging.warning(f"Сирі дані від WFP: {raw_data}")

    try:
        data = json.loads(raw_data) if raw_data else {}
    except json.JSONDecodeError:
        data = dict(await request.post())

    if not data:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    order_ref = data.get("orderReference")
    status = data.get("transactionStatus")
    amount = float(data.get("amount", 0))

    try:
        req_id = int(order_ref.split("_")[0])
    except (ValueError, AttributeError, IndexError):
        return web.json_response({"error": "Invalid orderReference"}, status=400)

    if status == "Approved":
        bot = request.app['bot']

        await process_successful_payment(req_id=req_id, amount=amount, bot=bot)

    current_time = int(time.time())
    response_status = "accept"
    sign_str = f"{order_ref};{response_status};{current_time}"
    signature = get_wfp_signature(sign_str)

    return web.json_response({
        "orderReference": order_ref,
        "status": response_status,
        "time": current_time,
        "signature": signature
    })