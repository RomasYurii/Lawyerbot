from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext  # Додаємо імпорт FSM

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy.future import select
from app.models import Request


# Імпортуємо клавіатури
from app.keyboard.keyboards import main_menu

router = Router()


@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    # Повністю очищаємо будь-який попередній стан (це аналог mode: client)
    await state.clear()

    await message.answer(
        "👋 Вітаю у боті *СамеТойАдвокат*!\n\n"
        "Тут ви можете отримати швидку юридичну консультацію від кваліфікованого фахівця. Надання відповіді гарантоване протягом 24 годин (зазвичай швидше)\n\n"
        "Оберіть дію нижче:",
        reply_markup=main_menu()
    )


@router.callback_query(F.data == "help")
async def help_info(callback: CallbackQuery, state: FSMContext):
    # При переході в допомогу теж корисно скинути стан, якщо користувач був посеред заповнення чогось
    await state.clear()

    await callback.message.answer(
        "📞 *Контакти:*\n"
        "Telegram: @SametoiAdmin\n"
        "Email: sametoi.law@gmail.com\n"
        "Графік роботи: Пн–Пт, 9:00–18:00",
        reply_markup=main_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cancel(callback: CallbackQuery, state: FSMContext):
    # Скидаємо стан FSM (тепер дані в Redis видаляться для цього юзера)
    await state.clear()

    await callback.message.answer("❌ Дію скасовано.", reply_markup=main_menu())
    await callback.answer()


@router.callback_query(F.data == "my_requests")
async def my_requests(callback: CallbackQuery, session_maker: async_sessionmaker[AsyncSession], state: FSMContext):
    # Користувач перевіряє свої запити — скидаємо активні стейти заповнення
    await state.clear()

    user_id = callback.from_user.id

    async with session_maker() as session:
        query = (
            select(Request)
            .where(Request.client_id == user_id)
            .order_by(Request.created_at.desc())
        )
        result = await session.execute(query)
        user_reqs = result.scalars().all()

    if not user_reqs:
        await callback.message.answer("📭 У вас ще немає звернень.", reply_markup=main_menu())
        await callback.answer()
        return

    text = "📂 *Ваші звернення:*\n\n"
    for req in user_reqs:
        # Встановлюємо правильний статус
        if req.status == 'pending_payment':
            status = "💳 Очікує оплати"
        elif req.status == 'paid':
            status = "🕐 Очікує адвоката"
        elif req.status == 'in_progress':
            status = "👨‍⚖️ В роботі"
        elif req.status == 'completed':
            status = "✅ Завершено"
        else:
            status = "❓ Невідомо"

        question_preview = req.question_text[:50] if req.question_text else '... '
        text += f"*#{req.id}* — {req.category}\n❓ {question_preview}...\nСтатус: {status}\n\n"

    await callback.message.answer(text, reply_markup=main_menu())
    await callback.answer()