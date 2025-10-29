"""
AI-IdeaFactory: Telegram Bot для генерации контент-идей
Webhook версия для работы через Cloudflare Tunnel
"""

import os
import logging
import json
from flask import Flask, request
from dotenv import load_dotenv
import telebot
from telebot import types

from ai_client import OpenRouterClient

# Конфигурация логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL_BASE = os.getenv("WEBHOOK_URL", "https://your-tunnel-url.trycloudflare.com")
WEBHOOK_URL_PATH = f"/{TELEGRAM_TOKEN}"

# Flask приложение
app = Flask(__name__)

# Создание бота (без прокси для webhook)
bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=False)

# Клиент для работы с AI
ai_client = OpenRouterClient()

# Хранилище данных пользователей
user_data_store = {}


class UserState:
    """Класс для хранения состояния пользователя"""
    WAITING_NICHE = 1
    WAITING_GOAL = 2
    WAITING_FORMAT = 3
    WAITING_IDEA_SELECTION = 4


def get_user_state(user_id):
    """Получить состояние пользователя"""
    return user_data_store.get(user_id, {}).get('state', None)


def set_user_state(user_id, state):
    """Установить состояние пользователя"""
    if user_id not in user_data_store:
        user_data_store[user_id] = {}
    user_data_store[user_id]['state'] = state


def get_user_data(user_id):
    """Получить данные пользователя"""
    if user_id not in user_data_store:
        user_data_store[user_id] = {}
    return user_data_store[user_id]


@bot.message_handler(commands=['start'])
def handle_start(message):
    """Обработчик команды /start"""
    user_id = message.chat.id
    logger.info(f"User {user_id} started the bot")
    
    welcome_text = (
        "🎯 <b>Добро пожаловать в AI-IdeaFactory!</b>\n\n"
        "Я помогу вам придумать крутые идеи для контента используя AI.\n\n"
        "<b>Как это работает:</b>\n"
        "1️⃣ Расскажите мне о вашей нише\n"
        "2️⃣ Определите цель контента\n"
        "3️⃣ Выберите формат контента\n"
        "4️⃣ Получите 5 готовых идей\n"
        "5️⃣ Выберите идею и получите полный пост\n\n"
        "📌 Давайте начнем! Укажите вашу <b>нишу</b> "
        "(например: фитнес, образование, бизнес, блоги и т.д.):"
    )
    
    set_user_state(user_id, UserState.WAITING_NICHE)
    bot.send_message(user_id, welcome_text, parse_mode='HTML')


@bot.message_handler(func=lambda message: get_user_state(message.chat.id) == UserState.WAITING_NICHE)
def handle_niche(message):
    """Обработчик ввода ниши"""
    user_id = message.chat.id
    niche = message.text.strip()
    
    if not niche or len(niche) < 2:
        bot.send_message(user_id, "❌ Пожалуйста, укажите корректную нишу (минимум 2 символа)")
        return
    
    data = get_user_data(user_id)
    data['niche'] = niche
    
    logger.info(f"User {user_id} selected niche: {niche}")
    
    goal_text = (
        f"✅ <b>Ниша:</b> {niche}\n\n"
        "Теперь укажите <b>цель контента</b>\n"
        "(например: привлечь аудиторию, обучить, продать, развлечь)"
    )
    
    set_user_state(user_id, UserState.WAITING_GOAL)
    bot.send_message(user_id, goal_text, parse_mode='HTML')


@bot.message_handler(func=lambda message: get_user_state(message.chat.id) == UserState.WAITING_GOAL)
def handle_goal(message):
    """Обработчик ввода цели"""
    user_id = message.chat.id
    goal = message.text.strip()
    
    if not goal or len(goal) < 2:
        bot.send_message(user_id, "❌ Пожалуйста, укажите корректную цель (минимум 2 символа)")
        return
    
    data = get_user_data(user_id)
    data['goal'] = goal
    
    logger.info(f"User {user_id} selected goal: {goal}")
    
    format_text = (
        f"✅ <b>Цель:</b> {goal}\n\n"
        "Теперь выберите <b>формат контента</b>\n"
        "(например: пост в соцсетях, статья, видео, рилс, карусель)"
    )
    
    set_user_state(user_id, UserState.WAITING_FORMAT)
    bot.send_message(user_id, format_text, parse_mode='HTML')


@bot.message_handler(func=lambda message: get_user_state(message.chat.id) == UserState.WAITING_FORMAT)
def handle_format(message):
    """Обработчик ввода формата и генерация идей"""
    user_id = message.chat.id
    content_format = message.text.strip()
    
    if not content_format or len(content_format) < 2:
        bot.send_message(user_id, "❌ Пожалуйста, укажите корректный формат (минимум 2 символа)")
        return
    
    data = get_user_data(user_id)
    data['format'] = content_format
    
    logger.info(f"User {user_id} selected format: {content_format}")
    
    # Показываем сообщение о обработке
    processing_msg = bot.send_message(
        user_id,
        "⏳ <b>Генерирую идеи контента для вас...</b>\n"
        "Это может занять 30-60 секунд ⏱️",
        parse_mode='HTML'
    )
    
    try:
        # Генерируем идеи
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        ideas = loop.run_until_complete(ai_client.generate_ideas(
            niche=data['niche'],
            goal=data['goal'],
            content_format=content_format
        ))
        loop.close()
        
        if not ideas or not isinstance(ideas, list):
            bot.send_message(user_id, "❌ Ошибка при генерации идей. Попробуйте позже.")
            logger.error(f"Failed to generate ideas for user {user_id}")
            return
        
        data['ideas'] = ideas
        logger.info(f"Generated {len(ideas)} ideas for user {user_id}")
        
        # Удаляем сообщение о обработке
        try:
            bot.delete_message(user_id, processing_msg.message_id)
        except Exception:
            pass
        
        # Форматируем идеи для отображения
        ideas_text = "🎨 <b>Вот 5 идей для вашего контента:</b>\n\n"
        for idx, idea in enumerate(ideas[:5], 1):
            title = idea.get('title', 'Без названия')
            description = idea.get('description', 'Нет описания')
            ideas_text += f"<b>💡 Идея {idx}:</b>\n<i>{title}</i>\n{description}\n\n"
        
        # Создаем inline кнопки
        markup = types.InlineKeyboardMarkup()
        for idx in range(min(5, len(ideas))):
            button = types.InlineKeyboardButton(
                f"💡 Идея {idx + 1}",
                callback_data=f"idea_{idx}"
            )
            markup.add(button)
        
        set_user_state(user_id, UserState.WAITING_IDEA_SELECTION)
        bot.send_message(user_id, ideas_text, reply_markup=markup, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error generating ideas: {e}")
        bot.send_message(user_id, "❌ Ошибка при генерации идей. Попробуйте позже.")


@bot.callback_query_handler(func=lambda call: call.data.startswith('idea_'))
def handle_idea_selection(call):
    """Обработчик выбора идеи"""
    user_id = call.from_user.id
    
    try:
        idea_index = int(call.data.split('_')[1])
        data = get_user_data(user_id)
        
        if 'ideas' not in data or idea_index >= len(data['ideas']):
            bot.answer_callback_query(call.id, "❌ Неверный выбор идеи")
            return
        
        bot.answer_callback_query(call.id)
        
        # Показываем сообщение о обработке
        processing_msg = bot.send_message(
            user_id,
            "⏳ <b>Генерирую пост на основе выбранной идеи...</b>\n"
            "Это может занять 30-60 секунд ⏱️",
            parse_mode='HTML'
        )
        
        selected_idea = data['ideas'][idea_index]
        idea_title = selected_idea.get('title', 'Идея')
        idea_description = selected_idea.get('description', '')
        
        # Генерируем пост
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        post = loop.run_until_complete(ai_client.generate_post(
            niche=data['niche'],
            goal=data['goal'],
            content_format=data['format'],
            idea_title=idea_title,
            idea_description=idea_description
        ))
        loop.close()
        
        if not post:
            bot.send_message(user_id, "❌ Ошибка при генерации поста. Попробуйте позже.")
            logger.error(f"Failed to generate post for user {user_id}")
            return
        
        logger.info(f"Generated post for user {user_id}")
        
        # Удаляем сообщение о обработке
        try:
            bot.delete_message(user_id, processing_msg.message_id)
        except Exception:
            pass
        
        # Отправляем готовый пост
        post_text = (
            f"📝 <b>Готовый пост:</b>\n\n"
            f"{post}\n\n"
            f"<i>Идея основана на: {idea_title}</i>"
        )
        
        bot.send_message(user_id, post_text, parse_mode='HTML')
        
        # Предлагаем варианты дальнейшего действия с reply кнопками
        reply_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        reply_markup.add(types.KeyboardButton("🔄 Создать новые идеи"))
        reply_markup.add(types.KeyboardButton("⬅️ Выбрать другую идею"))
        
        bot.send_message(user_id, "Что дальше?", reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error selecting idea: {e}")
        bot.answer_callback_query(call.id, "❌ Произошла ошибка")


@bot.callback_query_handler(func=lambda call: call.data == "restart")
def handle_restart(call):
    """Обработчик перезагрузки"""
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    
    # Очищаем данные пользователя
    if user_id in user_data_store:
        user_data_store[user_id].clear()
    
    set_user_state(user_id, UserState.WAITING_NICHE)
    
    restart_text = (
        "🎯 <b>Новый раунд генерации идей!</b>\n\n"
        "Укажите вашу <b>нишу</b>:"
    )
    
    bot.send_message(user_id, restart_text, parse_mode='HTML')


@bot.callback_query_handler(func=lambda call: call.data == "select_other")
def handle_select_other(call):
    """Обработчик выбора другой идеи"""
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    
    data = get_user_data(user_id)
    
    if 'ideas' not in data:
        bot.send_message(user_id, "❌ Данные сессии потеряны. Начните заново /start")
        return
    
    ideas = data['ideas']
    
    # Форматируем идеи
    ideas_text = "🎨 <b>Выберите другую идею:</b>\n\n"
    for idx, idea in enumerate(ideas[:5], 1):
        title = idea.get('title', 'Без названия')
        description = idea.get('description', 'Нет описания')
        ideas_text += f"<b>💡 Идея {idx}:</b>\n<i>{title}</i>\n{description}\n\n"
    
    # Создаем кнопки
    markup = types.InlineKeyboardMarkup()
    for idx in range(min(5, len(ideas))):
        button = types.InlineKeyboardButton(
            f"💡 Идея {idx + 1}",
            callback_data=f"idea_{idx}"
        )
        markup.add(button)
    
    set_user_state(user_id, UserState.WAITING_IDEA_SELECTION)
    bot.send_message(user_id, ideas_text, reply_markup=markup, parse_mode='HTML')


@bot.message_handler(func=lambda message: message.text and "Создать новые идеи" in message.text)
def handle_create_new_ideas(message):
    """Обработчик reply кнопки 'Создать новые идеи'"""
    user_id = message.chat.id
    logger.info(f"User {user_id} pressed 'Создать новые идеи' button")
    
    # Очищаем данные пользователя
    if user_id in user_data_store:
        user_data_store[user_id].clear()
    
    set_user_state(user_id, UserState.WAITING_NICHE)
    
    restart_text = (
        "🎯 <b>Новый раунд генерации идей!</b>\n\n"
        "Укажите вашу <b>нишу</b>:"
    )
    
    # Удаляем reply клавиатуру
    markup = types.ReplyKeyboardRemove()
    bot.send_message(user_id, restart_text, parse_mode='HTML', reply_markup=markup)


@bot.message_handler(func=lambda message: message.text and "Выбрать другую идею" in message.text)
def handle_select_another_idea(message):
    """Обработчик reply кнопки 'Выбрать другую идею'"""
    user_id = message.chat.id
    logger.info(f"User {user_id} pressed 'Выбрать другую идею' button")
    data = get_user_data(user_id)
    
    if 'ideas' not in data:
        bot.send_message(user_id, "❌ Данные сессии потеряны. Начните заново /start")
        return
    
    ideas = data['ideas']
    
    # Форматируем идеи
    ideas_text = "🎨 <b>Выберите другую идею:</b>\n\n"
    for idx, idea in enumerate(ideas[:5], 1):
        title = idea.get('title', 'Без названия')
        description = idea.get('description', 'Нет описания')
        ideas_text += f"<b>💡 Идея {idx}:</b>\n<i>{title}</i>\n{description}\n\n"
    
    # Создаем inline кнопки
    markup = types.InlineKeyboardMarkup()
    for idx in range(min(5, len(ideas))):
        button = types.InlineKeyboardButton(
            f"💡 Идея {idx + 1}",
            callback_data=f"idea_{idx}"
        )
        markup.add(button)
    
    set_user_state(user_id, UserState.WAITING_IDEA_SELECTION)
    bot.send_message(user_id, ideas_text, reply_markup=markup, parse_mode='HTML')


@bot.message_handler(commands=['help'])
def handle_help(message):
    """Обработчик команды /help"""
    user_id = message.chat.id
    
    help_text = (
        "<b>📖 Справка по использованию:</b>\n\n"
        "<b>/start</b> - Начать новую сессию генерации идей\n"
        "<b>/help</b> - Показать эту справку\n"
        "<b>/cancel</b> - Отменить текущий диалог\n\n"
        "<b>🎯 Как работает бот:</b>\n"
        "1. Укажите нишу контента\n"
        "2. Определите цель контента\n"
        "3. Выберите формат контента\n"
        "4. Получите 5 идей\n"
        "5. Выберите идею и получите готовый пост\n\n"
        "<b>💡 Примеры:</b>\n"
        "• Ниша: фитнес\n"
        "• Цель: привлечь аудиторию\n"
        "• Формат: пост в Instagram"
    )
    
    bot.send_message(user_id, help_text, parse_mode='HTML')


@bot.message_handler(commands=['cancel'])
def handle_cancel(message):
    """Обработчик команды /cancel"""
    user_id = message.chat.id
    
    if user_id in user_data_store:
        user_data_store[user_id].clear()
    
    bot.send_message(user_id, "❌ Диалог отменен. Введите /start для начала.")


@bot.message_handler(func=lambda message: True)
def handle_default(message):
    """Обработчик неизвестных сообщений"""
    user_id = message.chat.id
    state = get_user_state(user_id)
    
    if state is None:
        bot.send_message(user_id, "Привет! Введите /start для начала работы с ботом.")
    else:
        bot.send_message(user_id, "Я не понял ваше сообщение. Пожалуйста, следуйте инструкциям выше.")

# Webhook endpoints
@app.route(WEBHOOK_URL_PATH, methods=['POST'])
def webhook():
    """Обработка webhook от Telegram"""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return '', 403


@app.route('/')
def index():
    """Главная страница для проверки работы"""
    return 'AI-IdeaFactory Bot is running! 🤖', 200


@app.route('/health')
def health():
    """Health check endpoint"""
    return 'OK', 200


def main():
    """Главная функция для webhook режима"""
    if not TELEGRAM_TOKEN:
        logger.error("❌ TELEGRAM_TOKEN не установлен в .env файле")
        return
    
    try:
        # Webhook должен быть установлен вручную через API (из-за блокировки на сервере)
        # curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
        #   -H "Content-Type: application/json" \
        #   -d '{"url": "https://<tunnel-url>/<TOKEN>"}'
        
        webhook_url = WEBHOOK_URL_BASE + WEBHOOK_URL_PATH
        logger.info(f"🌐 Ожидаемый webhook: {webhook_url}")
        logger.info("ℹ️ Убедитесь, что webhook установлен через Telegram API")
        
        logger.info("🚀 Запуск Flask сервера на порту 8000")
        logger.info("🤖 Бот готов к работе через webhook!")
        
        # Запускаем Flask
        app.run(host='0.0.0.0', port=8000, debug=False)
        
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")


if __name__ == "__main__":
    main()

    main()
