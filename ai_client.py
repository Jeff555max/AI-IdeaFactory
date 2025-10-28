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
from prompts import SYSTEM_PROMPT, IDEAS_GENERATION_PROMPT, POST_GENERATION_PROMPT

load_dotenv()

logger = logging.getLogger(__name__)

OPENAI_KEY = os.getenv("OPENAI_KEY")
OPENAI_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-4o-mini"


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
