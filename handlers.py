from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from sqlalchemy import select
from database import get_db
from models import User, Event, Reminder, Family, Memory
from ai_service import AIService
import pytz
from config import config

# Создаем роутер
router = Router()
ai_service = AIService()

# Состояния для FSM
class EventStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_confirm = State()

class QuestionStates(StatesGroup):
    waiting_for_question = State()

# Команда /start
@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    
    # Получаем сессию БД
    async for db in get_db():
        # Проверяем, есть ли пользователь в БД
        result = await db.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Создаем нового пользователя
            new_user = User(
                telegram_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name
            )
            db.add(new_user)
            await db.commit()
            
            await message.answer(
                f"👋 Привет, {message.from_user.first_name}!\n\n"
                f"Я семейный планировщик с ИИ. Я помогу тебе:\n"
                f"📅 Планировать события\n"
                f"🔔 Напоминать о важных делах\n"
                f"💬 Отвечать на вопросы\n\n"
                f"Используй /help для списка команд"
            )
        else:
            await message.answer(f"С возвращением, {user.first_name}! 👋")

# Команда /help
@router.message(Command("help"))
async def cmd_help(message: Message):
    """Показывает справку"""
    help_text = """
📋 Доступные команды:

/start - Начать работу
/help - Показать эту справку
/addevent - Создать новое событие
/myevents - Мои события
/ask - Задать вопрос ИИ
/remember - Запомнить информацию
/memories - Посмотреть что я помню
/family - Управление семьей

Просто напиши мне сообщение, и я помогу!
    """
    await message.answer(help_text)

# Создание события через команду
@router.message(Command("addevent"))
async def cmd_addevent(message: Message, state: FSMContext):
    """Начинает процесс создания события"""
    await message.answer("📝 Опиши событие:\nНапример: Встреча с друзьями завтра в 19:00")
    await state.set_state(EventStates.waiting_for_title)

# Обработка текста для создания события
@router.message(EventStates.waiting_for_title)
async def process_event_text(message: Message, state: FSMContext):
    """Обрабатывает описание события через ИИ"""
    text = message.text
    
    # Отправляем сообщение о начале обработки
    processing_msg = await message.answer("🤔 Анализирую информацию...")
    
    # Парсим текст через ИИ
    event_data = await ai_service.parse_event_from_text(text)
    
    if "error" in event_data:
        await processing_msg.edit_text("❌ Не удалось распознать событие. Попробуй еще раз.")
        await state.clear()
        return
    
    # Сохраняем данные в состоянии
    await state.update_data(event_data=event_data)
    
    # Формируем сообщение для подтверждения
    confirm_text = "📋 Проверьте данные:\n\n"
    confirm_text += f"📌 Название: {event_data.get('title', 'Не указано')}\n"
    confirm_text += f"📅 Дата: {event_data.get('date', 'Не указана')}\n"
    confirm_text += f"⏰ Время: {event_data.get('time', 'Не указано')}\n"
    confirm_text += f"🔄 Повтор: {event_data.get('repeat_type', 'once')}\n"
    
    if event_data.get('description'):
        confirm_text += f"📝 Описание: {event_data['description']}\n"
    
    # Создаем клавиатуру для подтверждения
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_event"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_event")
        ],
        [
            InlineKeyboardButton(text="✏️ Изменить", callback_data="edit_event")
        ]
    ])
    
    await processing_msg.edit_text(confirm_text, reply_markup=keyboard)
    await state.set_state(EventStates.waiting_for_confirm)

# Подтверждение создания события
@router.callback_query(F.data == "confirm_event", EventStates.waiting_for_confirm)
async def confirm_event(callback: CallbackQuery, state: FSMContext):
    """Сохраняет событие в БД"""
    data = await state.get_data()
    event_data = data.get('event_data')
    
    user_id = callback.from_user.id
    
    async for db in get_db():
        # Получаем пользователя
        result = await db.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one()
        
        # Создаем дату события
        event_datetime = datetime.strptime(
            f"{event_data['date']} {event_data['time']}", 
            "%Y-%m-%d %H:%M"
        )
        
        # Создаем событие
        new_event = Event(
            title=event_data['title'],
            description=event_data.get('description', ''),
            event_date=event_datetime,
            event_time=event_data['time'],
            repeat_type=event_data.get('repeat_type', 'once'),
            created_by=user.id,
            family_id=user.family_id
        )
        
        db.add(new_event)
        await db.flush()  # Чтобы получить ID события
        
        # Создаем напоминание (за 1 час до события)
        remind_at = event_datetime - timedelta(hours=1)
        reminder = Reminder(
            event_id=new_event.id,
            user_id=user.id,
            remind_at=remind_at
        )
        
        db.add(reminder)
        await db.commit()
        
        # Здесь нужно будет добавить планировщик для отправки уведомления
        
    await callback.message.edit_text(
        f"✅ Событие '{event_data['title']}' успешно создано!\n"
        f"Я напомню о нем за час до начала."
    )
    await state.clear()

@router.callback_query(F.data == "cancel_event")
async def cancel_event(callback: CallbackQuery, state: FSMContext):
    """Отменяет создание события"""
    await callback.message.edit_text("❌ Создание события отменено.")
    await state.clear()

# Команда для вопросов ИИ
@router.message(Command("ask"))
async def cmd_ask(message: Message, state: FSMContext):
    """Начинает диалог с ИИ"""
    await message.answer("💭 Задай свой вопрос. Я постараюсь помочь!")
    await state.set_state(QuestionStates.waiting_for_question)

@router.message(QuestionStates.waiting_for_question)
async def process_question(message: Message, state: FSMContext):
    """Обрабатывает вопрос пользователя"""
    question = message.text
    
    # Собираем контекст
    context = {
        'members': [],
        'upcoming_events': [],
        'important_dates': {}
    }
    
    async for db in get_db():
        # Получаем пользователя
        result = await db.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if user and user.family_id:
            # Получаем членов семьи
            members_result = await db.execute(
                select(User).where(User.family_id == user.family_id)
            )
            context['members'] = [m.first_name for m in members_result.scalars().all()]
            
            # Получаем ближайшие события
            now = datetime.utcnow()
            events_result = await db.execute(
                select(Event).where(
                    Event.family_id == user.family_id,
                    Event.event_date >= now
                ).order_by(Event.event_date).limit(5)
            )
            context['upcoming_events'] = [
                f"{e.title} ({e.event_date.strftime('%d.%m')})" 
                for e in events_result.scalars().all()
            ]
            
            # Получаем важные даты из памяти
            memories_result = await db.execute(
                select(Memory).where(
                    Memory.family_id == user.family_id,
                    Memory.category == 'important_date'
                )
            )
            for mem in memories_result.scalars().all():
                context['important_dates'][mem.key] = mem.value
    
    # Отправляем сообщение о начале обработки
    processing_msg = await message.answer("🤔 Думаю...")
    
    # Получаем ответ от ИИ
    answer = await ai_service.answer_question(question, context)
    
    await processing_msg.edit_text(answer)
    await state.clear()

# Команда для запоминания информации
@router.message(Command("remember"))
async def cmd_remember(message: Message):
    """Запоминает информацию"""
    text = message.text.replace("/remember", "").strip()
    
    if not text:
        await message.answer("📝 Напиши, что нужно запомнить.\n"
                            "Например: /remember День рождения мамы 15 мая")
        return
    
    # Извлекаем информацию через ИИ
    memory_data = await ai_service.extract_memory(text)
    
    if memory_data.get('has_memory'):
        async for db in get_db():
            # Получаем пользователя
            result = await db.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
            user = result.scalar_one()
            
            # Сохраняем в память
            memory = Memory(
                family_id=user.family_id,
                key=memory_data['key'],
                value=memory_data['value'],
                category=memory_data.get('category', 'general'),
                created_by=user.id
            )
            
            db.add(memory)
            await db.commit()
            
        await message.answer(f"✅ Запомнил: {memory_data['key']} - {memory_data['value']}")
    else:
        await message.answer("❌ Не удалось понять, что нужно запомнить. Попробуй еще раз.")

# Просмотр событий
@router.message(Command("myevents"))
async def cmd_myevents(message: Message):
    """Показывает ближайшие события"""
    user_id = message.from_user.id
    
    async for db in get_db():
        # Получаем пользователя
        result = await db.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one()
        
        # Получаем события
        now = datetime.utcnow()
        events_result = await db.execute(
            select(Event).where(
                Event.created_by == user.id,
                Event.event_date >= now
            ).order_by(Event.event_date).limit(10)
        )
        
        events = events_result.scalars().all()
        
        if not events:
            await message.answer("📅 У тебя нет ближайших событий.")
            return
        
        text = "📅 Твои ближайшие события:\n\n"
        for event in events:
            date_str = event.event_date.strftime("%d.%m.%Y в %H:%M")
            status = "✅" if event.is_completed else "⏳"
            text += f"{status} {event.title} - {date_str}\n"
        
        await message.answer(text)

# Обработка любых сообщений (для ИИ ассистента)
@router.message()
async def handle_all_messages(message: Message):
    """Обрабатывает все сообщения как потенциальные события или вопросы"""
    text = message.text
    
    # Проверяем, похоже ли это на событие
    time_keywords = ['завтра', 'сегодня', 'послезавтра', 'в', 'через']
    has_time_keyword = any(keyword in text.lower() for keyword in time_keywords)
    
    if has_time_keyword:
        # Пробуем распарсить как событие
        event_data = await ai_service.parse_event_from_text(text)
        
        if "error" not in event_data and event_data.get('title'):
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Да, создать", callback_data="quick_create"),
                    InlineKeyboardButton(text="❌ Нет", callback_data="quick_cancel")
                ]
            ])
            
            await message.answer(
                f"🔍 Я нашел в сообщении событие:\n"
                f"'{event_data['title']}'\n"
                f"Создать напоминание?",
                reply_markup=keyboard
            )
            return
    
    # Если не похоже на событие, предлагаем задать вопрос
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💭 Задать вопрос", callback_data="ask_question")]
    ])
    
    await message.answer(
        "Не уверен, что это событие. Хочешь задать вопрос?",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "ask_question")
async def callback_ask_question(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки вопроса"""
    await callback.message.edit_text("💭 Задай свой вопрос:")
    await state.set_state(QuestionStates.waiting_for_question)