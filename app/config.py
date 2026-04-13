import os
from dotenv import load_dotenv

load_dotenv(".env")

try:
    if not os.environ.get("BOT_TOKEN"):
        raise ValueError("Помилка: не знайдено BOT_TOKEN в змінних оточення.")

    if not os.environ.get("LAWYERS_CHAT_ID"):
        raise ValueError("Помилка: не знайдено LAWYERS_CHAT_ID або він має неправильний формат.")

    if not os.environ.get("DATABASE_URL"):
        raise ValueError("Помилка: не знайдено DATABASE_URL в змінних оточення.")

    if not os.environ.get("WFP_MERCHANT_ACCOUNT"):
        raise ValueError("Помилка: не знайдено WFP_MERCHANT_ACCOUNT в змінних оточення.")

    if not os.environ.get("WFP_SECRET_KEY"):
        raise ValueError("Помилка: не знайдено WFP_SECRET_KEY в змінних оточення.")

    if not os.environ.get("BASE_URL"):
        raise ValueError("Помилка: не знайдено BASE_URL в змінних оточення.")

    if not os.environ.get("REDIS_URL"):
        raise ValueError("Помилка: не знайдено REDIS_URL в змінних оточення.")

    if not os.environ.get("PRICE"):
        raise ValueError("Помилка: не знайдено PRICE в змінних оточення.")

    if not os.environ.get("WFP_API_URL"):
        raise ValueError("Помилка: не знайдено WFP_API_URL в змінних оточення.")

    if not os.environ.get("SERVICE_URL"):
        raise ValueError("Помилка: не знайдено SERVICE_URL в змінних оточення.")

    if not os.environ.get("RETURN_URL"):
        raise ValueError("Помилка: не знайдено RETURN_URL в змінних оточення.")

except ValueError as e:
    print(e)

else:
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    LAWYERS_CHAT_ID = os.environ.get("LAWYERS_CHAT_ID")
    DATABASE_URL = os.environ.get("DATABASE_URL")
    REDIS_URL = os.environ.get("REDIS_URL")
    WFP_API_URL = os.environ.get("WFP_API_URL")
    WPF_MERCHANT_ACCOUNT = os.environ.get("WFP_MERCHANT_ACCOUNT")
    WFP_SECRET_KEY = os.environ.get("WFP_SECRET_KEY")
    BASE_URL = os.environ.get("BASE_URL")
    PRICE = float(os.environ.get("PRICE"))
    SERVICE_URL = os.environ.get("SERVICE_URL")
    RETURN_URL = os.environ.get("RETURN_URL")