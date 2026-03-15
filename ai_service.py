import openai
from datetime import datetime
import json
import re
from config import config

class AIService:
    def __init__(self):
        self.api_key = config.OPENAI_API_KEY
        self.model = config.AI_MODEL
        
        # Важно: устанавливаем base_url для DeepSeek
        openai.api_base = "https://api.deepseek.com/v1"  # <-- ДОБАВЬ ЭТУ СТРОКУ
        openai.api_key = self.api_key
        
    async def parse_event_from_text(self, text: str) -> dict:
        """Парсит текст сообщения и извлекает информацию о событии"""
        
        prompt = f"""
        Извлеки информацию о событии из текста: "{text}"
        
        Текущая дата: {datetime.now().strftime("%Y-%m-%d %H:%M")}
        
        Верни JSON в формате:
        {{
            "title": "название события",
            "date": "YYYY-MM-DD",
            "time": "HH:MM",
            "repeat_type": "once/daily/weekly/monthly/yearly",
            "description": "дополнительное описание"
        }}
        
        Если какая-то информация отсутствует, поставь null.
        Дата должна быть в будущем, если не указано иное.
        """
        
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Ты помощник для извлечения структурированных данных из текста."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            result_text = response.choices[0].message.content
            
            # Извлекаем JSON из ответа
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                event_data = json.loads(json_match.group())
                return event_data
            else:
                return {"error": "Не удалось распарсить событие"}
                
        except Exception as e:
            print(f"Ошибка AI парсинга: {e}")
            return {"error": str(e)}
    
    async def answer_question(self, question: str, context: dict) -> str:
        """Отвечает на вопросы пользователя с учетом контекста"""
        
        # Формируем контекст из базы знаний
        context_text = f"""
        Информация о семье:
        - Участники: {context.get('members', [])}
        - Ближайшие события: {context.get('upcoming_events', [])}
        - Важные даты: {context.get('important_dates', {})}
        """
        
        prompt = f"""
        Контекст:
        {context_text}
        
        Вопрос пользователя: {question}
        
        Ответь на вопрос, используя предоставленный контекст.
        Если информации недостаточно, вежливо сообщи об этом.
        """
        
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Ты дружелюбный семейный помощник. Отвечай кратко и по делу."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Извините, у меня возникла ошибка: {e}"
    
    async def extract_memory(self, text: str) -> dict:
        """Извлекает информацию для долговременной памяти"""
        
        prompt = f"""
        Из текста: "{text}"
        
        Определи, есть ли здесь информация, которую стоит запомнить.
        Например: дни рождения, предпочтения, важные даты.
        
        Верни JSON:
        {{
            "has_memory": true/false,
            "key": "короткий_ключ",
            "value": "значение для запоминания",
            "category": "birthday/preference/important_date/general"
        }}
        """
        
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )
            
            result = response.choices[0].message.content
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"has_memory": False}
            
        except Exception as e:
            print(f"Ошибка извлечения памяти: {e}")
            return {"has_memory": False}
