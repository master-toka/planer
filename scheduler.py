from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import pytz
from typing import Optional
from config import config

class TaskScheduler:
    def __init__(self, bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler(timezone=pytz.timezone(config.TIMEZONE))
        
    def start(self):
        """Запуск планировщика"""
        self.scheduler.start()
        
    async def schedule_reminder(self, reminder_id: int, user_id: int, event_title: str, 
                                remind_at: datetime, event_date: datetime):
        """Планирование напоминания"""
        trigger = DateTrigger(run_date=remind_at)
        
        self.scheduler.add_job(
            self.send_reminder,
            trigger=trigger,
            args=[reminder_id, user_id, event_title, event_date],
            id=f"reminder_{reminder_id}",
            replace_existing=True
        )
        
    async def send_reminder(self, reminder_id: int, user_id: int, event_title: str, event_date: datetime):
        """Отправка напоминания пользователю"""
        try:
            # Форматируем время события
            event_time_str = event_date.strftime("%d.%m.%Y в %H:%M")
            
            text = f"🔔 Напоминание!\n\n"
            text += f"📅 Событие: {event_title}\n"
            text += f"⏰ Время: {event_time_str}"
            
            await self.bot.send_message(
                chat_id=user_id,
                text=text
            )
            
            # Здесь можно обновить статус напоминания в БД
            print(f"Напоминание {reminder_id} отправлено пользователю {user_id}")
            
        except Exception as e:
            print(f"Ошибка при отправке напоминания: {e}")
    
    def schedule_recurring_event(self, event_id: int, event_data: dict):
        """Планирование повторяющихся событий"""
        # Например, для еженедельных событий
        if event_data.get('repeat_type') == 'weekly':
            # Получаем день недели и время из оригинального события
            original_date = event_data['event_date']
            hour = original_date.hour
            minute = original_date.minute
            day_of_week = original_date.weekday()
            
            trigger = CronTrigger(
                day_of_week=day_of_week,
                hour=hour,
                minute=minute,
                timezone=pytz.timezone(config.TIMEZONE)
            )
            
            self.scheduler.add_job(
                self.create_next_event,
                trigger=trigger,
                args=[event_id],
                id=f"recurring_{event_id}"
            )
    
    async def create_next_event(self, event_id: int):
        """Создание следующего повторяющегося события"""
        # Здесь логика создания нового события на основе старого
        pass
        
    def cancel_reminder(self, reminder_id: int):
        """Отмена напоминания"""
        try:
            self.scheduler.remove_job(f"reminder_{reminder_id}")
        except:
            pass