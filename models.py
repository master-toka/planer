from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from database import Base
import datetime

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String)
    first_name = Column(String)
    family_id = Column(Integer, ForeignKey('families.id'), nullable=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Отношения
    family = relationship("Family", back_populates="members")
    events = relationship("Event", back_populates="creator")
    reminders = relationship("Reminder", back_populates="user")

class Family(Base):
    __tablename__ = 'families'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Отношения
    members = relationship("User", back_populates="family")
    events = relationship("Event", back_populates="family")

class Event(Base):
    __tablename__ = 'events'
    
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    event_date = Column(DateTime, nullable=False)
    event_time = Column(String)  # Храним время отдельно для гибкости
    repeat_type = Column(String, default='once')  # once, daily, weekly, monthly, yearly
    created_by = Column(Integer, ForeignKey('users.id'))
    family_id = Column(Integer, ForeignKey('families.id'))
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Отношения
    creator = relationship("User", back_populates="events")
    family = relationship("Family", back_populates="events")
    reminders = relationship("Reminder", back_populates="event")

class Reminder(Base):
    __tablename__ = 'reminders'
    
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('events.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    remind_at = Column(DateTime, nullable=False)  # Когда отправить напоминание
    is_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Отношения
    event = relationship("Event", back_populates="reminders")
    user = relationship("User", back_populates="reminders")

class Memory(Base):
    """Таблица для долговременной памяти ИИ"""
    __tablename__ = 'memories'
    
    id = Column(Integer, primary_key=True)
    family_id = Column(Integer, ForeignKey('families.id'))
    key = Column(String, nullable=False)  # Ключ (например, "день_рождения_мамы")
    value = Column(Text, nullable=False)  # Значение (например, "15 мая")
    category = Column(String, default='general')  # Категория (birthdays, preferences, etc.)
    created_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)