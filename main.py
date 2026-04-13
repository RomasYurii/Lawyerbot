# main.py
from app.payment.proccess_payment import wfp_webhook_handler

# Тепер Google Cloud (і functions-framework) знатиме,
# що твоя функція знаходиться тут, і всі імпорти 'app.something' працюватимуть.