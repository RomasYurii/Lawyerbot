import hmac
import hashlib
import time
from typing import Any

import aiohttp
import logging

from app.config import WPF_MERCHANT_ACCOUNT, WFP_SECRET_KEY, BASE_URL, WFP_API_URL, SERVICE_URL, RETURN_URL


def get_wfp_signature(string_to_sign: str) -> str:
    """
    Генерує підпис HMAC_MD5.
    """
    key = WFP_SECRET_KEY.encode('utf-8')
    message = string_to_sign.encode('utf-8')
    return hmac.new(key, message, hashlib.md5).hexdigest()


async def create_invoice(req_id: int, amount: float, description: str) -> Any | None:
    """
    Звертається до API WayForPay і отримує посилання на оплату (Invoice).
    """
    order_date = int(time.time())
    order_ref = f"{req_id}_{order_date}"

    # Очищуємо домен
    #domain = BASE_URL.replace("https://", "").replace("http://", "").split('/')[0]

    domain = BASE_URL
    amount = "1"

    amount_str = f"{float(amount):.2f}"

    sign_str = (
        f"{WPF_MERCHANT_ACCOUNT};"
        f"{domain};"
        f"{order_ref};"
        f"{order_date};"
        f"{amount_str};"  
        f"UAH;"
        f"{description};"
        f"1;"
        f"{amount_str}"
    )

    signature = get_wfp_signature(sign_str)

    data = {
        "transactionType": "CREATE_INVOICE",
        "merchantAccount": WPF_MERCHANT_ACCOUNT,
        "merchantDomainName": domain,
        "merchantAuthType": "SimpleSignature",
        "merchantSignature": signature,
        "apiVersion": 1,
        "orderReference": order_ref,
        "orderDate": order_date,
        "amount": amount_str,
        "currency": "UAH",
        "productName": [description],
        "productCount": [1],
        "productPrice": [amount_str],
        "serviceUrl": SERVICE_URL,
        "returnUrl": RETURN_URL
    }


    logging.info(f"Signing string: {sign_str}")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(WFP_API_URL, json=data) as response:
                result = await response.json()

                if result.get("reasonCode") == 1100:
                    return result.get("invoiceUrl")
                else:
                    logging.error(f"WayForPay Error: {result.get('reason')} (Code: {result.get('reasonCode')})")
                    return None
        except Exception as e:
            logging.error(f"Connection Error to WayForPay: {e}")
            return None


def generate_wfp_webhook_response(order_ref: str, status: str = "accept") -> dict:
    """
    WayForPay вимагає обов'язкової відповіді на свій вебхук з правильним підписом.
    Якщо цього не зробити, вони будуть дублювати запити кожні 15 хвилин.
    """
    current_time = int(time.time())
    # Рядок для підпису відповіді: orderReference;status;time
    sign_str = f"{order_ref};{status};{current_time}"
    signature = get_wfp_signature(sign_str)

    return {
        "orderReference": order_ref,
        "status": status,
        "time": current_time,
        "signature": signature
    }
