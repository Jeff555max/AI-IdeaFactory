"""
AI-IdeaFactory: OpenRouter API Client
Обработка всех запросов к OpenAI GPT-4o-mini через OpenRouter API
"""

import os
import json
import logging
import httpx
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

OPENAI_KEY = os.getenv("OPENAI_KEY")
OPENAI_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-4o-mini"

SYSTEM_PROMPT = """Ты - профессиональный контент-стратег и копирайтер с опытом в маркетинге и создании вирального контента.

Твоя задача помогать пользователям генерировать уникальные, привлекательные идеи для контента, которые:
- Соответствуют целевой аудитории
- Удерживают внимание и вызывают взаимодействие
- Оптимизированы для конкретной платформы
- Содержат четкий call-to-action

Всегда:
1. Генерируй свежие и креативные идеи
2. Учитывай тренды и текущие события
3. Адаптируй контент под заданный формат
4. Делай текст простым и понятным
5. Используй эмодзи и структурирование для читаемости"""

IDEAS_GENERATION_PROMPT = """Генерируй ровно 5 уникальных идей для контента в формате JSON.

Параметры:
- Ниша: {niche}
- Цель контента: {goal}
- Формат: {content_format}

Требования к каждой идее:
- title: Короткое, цепляющее название (5-10 слов)
- description: Краткое описание идеи (2-3 предложения, максимум 150 символов)

Ответь ТОЛЬКО JSON без дополнительного текста, в формате:
[
  {{"title": "...", "description": "..."}},
  {{"title": "...", "description": "..."}},
  ...
]"""

POST_GENERATION_PROMPT = """Создай готовый пост для контента на основе выбранной идеи.

Параметры:
- Ниша: {niche}
- Цель контента: {goal}
- Формат: {content_format}
- Идея: {idea_title}
- Описание идеи: {idea_description}

Требования к посту:
- Написан для целевой аудитории
- Включает привлекательный заголовок или opening hook
- Структурирован для легкого чтения
- Содержит релевантные эмодзи
- Заканчивается четким call-to-action
- Оптимизирован для выбранного формата
- Готов к мгновенной публикации

Пиши полный, готовый к публикации пост."""


class OpenRouterClient:
    """Клиент для работы с OpenRouter API (OpenAI GPT-4o-mini)"""

    def __init__(self, api_key: str = OPENAI_KEY):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/Jeff555max/AI-IdeaFactory",
            "X-Title": "AI-IdeaFactory-Bot",
            "Content-Type": "application/json"
        }

    async def generate_ideas(
        self,
        niche: str,
        goal: str,
        content_format: str,
        temperature: float = 0.7
    ) -> Optional[List[Dict]]:
        """
        Генерирует 5 идей контента
        
        Args:
            niche: Ниша контента
            goal: Цель контента
            content_format: Формат контента
            temperature: Параметр творчества модели
            
        Returns:
            Список идей или None при ошибке
        """
        prompt = IDEAS_GENERATION_PROMPT.format(
            niche=niche,
            goal=goal,
            content_format=content_format
        )

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    OPENAI_URL,
                    headers=self.headers,
                    json={
                        "model": MODEL,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": temperature,
                        "max_tokens": 2000
                    }
                )

                if response.status_code != 200:
                    logger.error(f"API Error: {response.status_code} - {response.text}")
                    return None

                result = response.json()
                content = result['choices'][0]['message']['content']

                # Парсим JSON из ответа
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                ideas = json.loads(content.strip())
                return ideas

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return None
        except httpx.RequestError as e:
            logger.error(f"API request error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error generating ideas: {e}")
            return None

    async def generate_post(
        self,
        niche: str,
        goal: str,
        content_format: str,
        idea_title: str,
        idea_description: str,
        temperature: float = 0.8
    ) -> Optional[str]:
        """
        Генерирует готовый пост на основе идеи
        
        Args:
            niche: Ниша контента
            goal: Цель контента
            content_format: Формат контента
            idea_title: Название идеи
            idea_description: Описание идеи
            temperature: Параметр творчества модели
            
        Returns:
            Текст поста или None при ошибке
        """
        prompt = POST_GENERATION_PROMPT.format(
            niche=niche,
            goal=goal,
            content_format=content_format,
            idea_title=idea_title,
            idea_description=idea_description
        )

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    OPENAI_URL,
                    headers=self.headers,
                    json={
                        "model": MODEL,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": temperature,
                        "max_tokens": 3000
                    }
                )

                if response.status_code != 200:
                    logger.error(f"API Error: {response.status_code} - {response.text}")
                    return None

                result = response.json()
                post = result['choices'][0]['message']['content']
                return post

        except httpx.RequestError as e:
            logger.error(f"API request error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error generating post: {e}")
            return None
