from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config import config

# Создаем движок базы данных
engine = create_async_engine(
    config.DATABASE_URL,
    echo=True,  # Логирование SQL запросов (для отладки)
)

# Создаем фабрику сессий
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Базовый класс для моделей
Base = declarative_base()

# Функция для получения сессии БД
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# Функция для создания таблиц
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)