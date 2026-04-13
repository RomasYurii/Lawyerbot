from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from app.config import DATABASE_URL

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    poolclass=NullPool,  # Вимикаємо пул SQLAlchemy для сумісності з Supabase
    connect_args={
        "statement_cache_size": 0,          # Вимикає кеш у asyncpg
        "prepared_statement_cache_size": 0  # Вимикає кеш у SQLAlchemy
    }
)

# Створюємо "фабрику сесій"
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

# Функція для ініціалізації таблиць
async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)