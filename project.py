import asyncio
import sqlite3
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime
import configparser
import html
import tempfile
from jinja2 import Template
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from PIL import Image
import io
from aiogram.types import ReplyParameters
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def adapt_datetime(dt):
    return dt.isoformat()

def convert_datetime(timestamp):
    return datetime.fromisoformat(timestamp.decode())

sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("TIMESTAMP", convert_datetime)

# Загрузка конфигурации из файла
TOKEN = ""
ADMIN_IDS = []
QUESTIONS_FOLDER = "quiz_photos"
DATABASE_NAME = "quiz_bot.db"
HTML_TEMPLATES_FOLDER = "html_templates"
SCREENSHOTS_FOLDER = "screenshots"

# Создаем необходимые папки
os.makedirs(HTML_TEMPLATES_FOLDER, exist_ok=True)
os.makedirs(SCREENSHOTS_FOLDER, exist_ok=True)

# Вопросы и правильные ответы
QUESTIONS = {
    1: [1], 2: [3], 3: [3], 4: [3], 5: [4],
    6: [3], 7: [4], 8: [3], 9: [2], 10: [3],
    11: [2], 12: [3], 13: [4], 14: [2], 15: [2],
    16: [3], 17: [2], 18: [3], 19: [4], 20: [2],
    21: [1], 22: [3], 23: [4], 24: [1], 25: [1],
    26: [3], 27: [2], 28: [1], 29: [3], 30: [4]
}

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Состояния викторины
class QuizState:
    REGISTRATION = "registration"
    STAGE_1 = "stage_1"
    STAGE_2 = "stage_2"
    STAGE_3 = "stage_3"
    FINISHED = "finished"

# Глобальные переменные
current_state = None
current_question = 0
question_timer = None
break_timer = None
user_registrations = {}
countdown_messages = {}
question_messages = {}
last_bot_messages = {}




LEADERBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Таблица лидеров | Викторина</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
            min-height: 100vh;
            padding: 20px;
            color: #ffffff;
            line-height: 1.6;
        }

        .container {
            max-width: 800px;
            margin: 0 auto;
            background: rgba(19, 21, 33, 0.98);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 
                0 20px 40px rgba(0, 0, 0, 0.5),
                0 0 0 1px rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 25px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            position: relative;
        }

        .header::after {
            content: '';
            position: absolute;
            bottom: -1px;
            left: 25%;
            width: 50%;
            height: 2px;
            background: linear-gradient(90deg, transparent, #10b981, #3b82f6, #10b981, transparent);
        }

        .stage-badge {
            display: inline-block;
            background: linear-gradient(135deg, #3b82f6, #1d4ed8);
            padding: 6px 16px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .title {
            font-size: 28px;
            font-weight: 700;
            background: linear-gradient(135deg, #ffffff, #a5b4fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 8px;
        }

        .subtitle {
            color: #d1d5db;
            font-size: 14px;
            opacity: 0.8;
        }

        .leaderboard {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            margin: 25px 0;
            font-size: 14px;
        }

        .leaderboard thead {
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(16, 185, 129, 0.15));
        }

        .leaderboard th {
            padding: 14px 16px;
            text-align: left;
            font-weight: 600;
            color: #a5b4fc;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 2px solid rgba(255, 255, 255, 0.1);
            font-size: 12px;
        }

        .leaderboard th:first-child {
            border-top-left-radius: 10px;
            width: 60px;
        }

        .leaderboard th:last-child {
            border-top-right-radius: 10px;
            width: 100px;
        }

        .leaderboard td {
            padding: 16px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            transition: all 0.2s ease;
        }

        .leaderboard tr:hover td {
            background: rgba(255, 255, 255, 0.03);
        }

        .rank {
            font-weight: 700;
            font-size: 16px;
            color: #3b82f6;
            text-align: center;
        }

        .rank-1 { color: #fbbf24; }
        .rank-2 { color: #9ca3af; }
        .rank-3 { color: #f59e0b; }

        .nickname {
            font-weight: 600;
            color: #ffffff;
            font-size: 14px;
        }

        .score {
            font-weight: 700;
            color: #10b981;
            text-align: right;
            font-size: 14px;
        }

        .status {
            text-align: center;
        }

        .qualified {
            background: linear-gradient(135deg, #10b981, #059669);
            color: white;
            padding: 4px 10px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 11px;
            display: inline-block;
        }

        .not-qualified {
            background: linear-gradient(135deg, #ef4444, #dc2626);
            color: white;
            padding: 4px 10px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 11px;
            display: inline-block;
        }

        /* Компактные статистические карточки */
        .stats-compact {
            display: flex;
            justify-content: center;
            gap: 15px;
            margin-top: 25px;
            flex-wrap: wrap;
        }

        .stat-item {
            background: rgba(255, 255, 255, 0.04);
            padding: 12px 18px;
            border-radius: 12px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.06);
            min-width: 100px;
        }

        .stat-number {
            font-size: 20px;
            font-weight: 700;
            margin-bottom: 4px;
            background: linear-gradient(135deg, #3b82f6, #10b981);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .stat-label {
            color: #d1d5db;
            font-size: 11px;
            opacity: 0.9;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            color: #9ca3af;
            font-size: 12px;
        }

        /* Улучшения для скриншотов */
        .screenshot-optimized {
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            text-rendering: optimizeLegibility;
            image-rendering: optimizeQuality;
        }

        @media (max-width: 768px) {
            .container {
                padding: 20px;
                margin: 10px;
            }
            
            .stats-compact {
                gap: 10px;
            }
            
            .stat-item {
                padding: 10px 14px;
                min-width: 80px;
            }
            
            .stat-number {
                font-size: 18px;
            }
            
            .title {
                font-size: 24px;
            }
            
            .leaderboard {
                font-size: 13px;
            }
            
            .leaderboard th,
            .leaderboard td {
                padding: 12px 10px;
            }
        }

        @media (max-width: 480px) {
            .stats-compact {
                flex-direction: column;
                align-items: center;
            }
            
            .stat-item {
                width: 120px;
            }
        }
    </style>
</head>
<body class="screenshot-optimized">
    <div class="container">
        <div class="header">
            <div class="stage-badge">Этап {{ stage }}</div>
            <h1 class="title">Итоги Этапа</h1>
            <p class="subtitle">Рейтинг участников викторины</p>
        </div>

        <table class="leaderboard">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Игрок</th>
                    <th style="text-align: right;">Баллы</th>
                    <th style="text-align: center;">Статус</th>
                </tr>
            </thead>
            <tbody>
                {% for player in players %}
                <tr>
                    <td class="rank {% if loop.index == 1 %}rank-1{% elif loop.index == 2 %}rank-2{% elif loop.index == 3 %}rank-3{% endif %}">
                        {{ loop.index }}
                    </td>
                    <td class="nickname">{{ player.nickname }}</td>
                    <td class="score">{{ player.score }}</td>
                    <td class="status">
                        {% if player.qualified %}
                            <span class="qualified">Прошёл ✅</span>
                        {% else %}
                            <span class="not-qualified">Выбыл ❌</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        <div class="footer">
        </div>
    </div>
</body>
</html>
"""

# Проверка является ли пользователь администратором
def is_admin(user_id):
    return user_id in ADMIN_IDS

# Инициализация базы данных
def init_database():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        nickname TEXT,
        stage_1_score INTEGER DEFAULT 0,
        stage_2_score INTEGER DEFAULT 0,
        stage_3_score INTEGER DEFAULT 0,
        total_score INTEGER DEFAULT 0,
        is_active BOOLEAN DEFAULT TRUE,
        registered_at TIMESTAMP
    )
    ''')
    
    # Таблица ответов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        question_number INTEGER,
        answer INTEGER,
        is_correct BOOLEAN,
        answered_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    
    # Таблица состояния викторины
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS quiz_state (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        current_state TEXT DEFAULT "registration",
        current_question INTEGER DEFAULT 0,
        updated_at TIMESTAMP
    )
    ''')
    
    # Инициализация состояния викторины
    cursor.execute('INSERT OR IGNORE INTO quiz_state (id, current_state, current_question, updated_at) VALUES (1, "registration", 0, ?)', (datetime.now(),))
    
    conn.commit()
    conn.close()

ALL_CORRECT_QUESTION = 25
ALL_CORRECT_QUESTIONS = 25



async def send_styled_message(chat_id, text, reply_to_message_id=None, parse_mode="HTML"):
    """
    Отправка стильного сообщения с оформлением
    """
    # HTML-разметка для красивого оформления
    styled_text = f"""
{text}
    """
    
    try:
        if reply_to_message_id:
            # Отправляем с цитированием предыдущего сообщения
            message = await bot.send_message(
                chat_id=chat_id,
                text=styled_text,
                parse_mode=parse_mode,
                reply_parameters=ReplyParameters(
                    message_id=reply_to_message_id,
                    chat_id=chat_id
                )
            )
        else:
            # Отправляем без цитирования
            message = await bot.send_message(
                chat_id=chat_id,
                text=styled_text,
                parse_mode=parse_mode
            )
        return message
    except Exception as e:
        print(f"Ошибка отправки стильного сообщения: {e}")
        # Fallback - обычное сообщение
        return await bot.send_message(chat_id, text)

async def send_animated_processing(chat_id, text, duration=3, dots_interval=0.5):
    """
    Отправка анимированного сообщения с точками
    """
    try:
        base_text = text
        message = await bot.send_message(chat_id, base_text)
        
        # Анимация точек
        dots = 0
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < duration:
            dots_text = base_text + '.' * (dots % 4)
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message.message_id,
                    text=dots_text
                )
            except:
                pass
            
            dots += 1
            await asyncio.sleep(dots_interval)
        
        # Финальное сообщение
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message.message_id,
            text=base_text + ' готово! ✅'
        )
        
        return message.message_id
        
    except Exception as e:
        print(f"Ошибка в анимированном сообщении: {e}")
        # Fallback - обычное сообщение
        message = await bot.send_message(chat_id, text + ' готово! ✅')
        return message.message_id

async def send_quiz_question(chat_id, question_number, photo_path=None, reply_to_message_id=None):
    """
    Отправка вопроса викторины с красивым оформлением
    """
    question_data = QUESTIONS.get(question_number, {"correct": [], "type": "single"})
    question_type = question_data.get("type", "single")
    
    caption = f"""
🎯 <b>ВОПРОС #{question_number}</b>

Выберите правильный ответ:
────────────────────
    """
    
    if question_type == "all_correct":
        caption += "\n💡 <i>Правильно!+1 балл</i>"
    elif question_type == "multiple":
        caption += f"\n💡 <i>Правильных ответов: {len(question_data['correct'])}</i>"
    
    try:
        if photo_path and os.path.exists(photo_path):
            photo = FSInputFile(photo_path)
            if reply_to_message_id:
                message = await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=create_answer_keyboard(),
                    reply_parameters=ReplyParameters(
                        message_id=reply_to_message_id,
                        chat_id=chat_id
                    )
                )
            else:
                message = await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=create_answer_keyboard()
                )
        else:
            # Текстовая версия если фото нет
            caption = f"""
🎯 <b>ВОПРОС #{question_number}</b>

{caption}
📷 <i>Фото недоступно</i>
────────────────────
            """
            if reply_to_message_id:
                message = await bot.send_message(
                    chat_id=chat_id,
                    text=caption,
                    parse_mode="HTML",
                    reply_markup=create_answer_keyboard(),
                    reply_parameters=ReplyParameters(
                        message_id=reply_to_message_id,
                        chat_id=chat_id
                    )
                )
            else:
                message = await bot.send_message(
                    chat_id=chat_id,
                    text=caption,
                    parse_mode="HTML",
                    reply_markup=create_answer_keyboard()
                )
        
        return message
    except Exception as e:
        print(f"Ошибка отправки вопроса: {e}")
        return None

def load_quiz_state():
    global current_state, current_question
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT current_state, current_question FROM quiz_state WHERE id = 1')
    state = cursor.fetchone()
    if state:
        current_state = state[0]
        current_question = state[1]
    else:
        # Если запись не существует, инициализируем значения по умолчанию
        current_state = QuizState.REGISTRATION
        current_question = 0
    conn.close()

def save_quiz_state():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE quiz_state SET current_state = ?, current_question = ?, updated_at = ? WHERE id = 1', 
                  (current_state, current_question, datetime.now()))
    conn.commit()
    conn.close()

# Функции работы с базой данных
def add_user(user_id, username, nickname):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR REPLACE INTO users (user_id, username, nickname, registered_at)
    VALUES (?, ?, ?, ?)
    ''', (user_id, username, nickname, datetime.now()))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def update_score(user_id, stage, score):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    if stage == 1:
        cursor.execute('UPDATE users SET stage_1_score = ? WHERE user_id = ?', (score, user_id))
    elif stage == 2:
        cursor.execute('UPDATE users SET stage_2_score = ? WHERE user_id = ?', (score, user_id))
    elif stage == 3:
        cursor.execute('UPDATE users SET stage_3_score = ? WHERE user_id = ?', (score, user_id))
    
    cursor.execute('UPDATE users SET total_score = stage_1_score + stage_2_score + stage_3_score WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def save_answer(user_id, question_number, answer, is_correct):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO answers (user_id, question_number, answer, is_correct, answered_at)
    VALUES (?, ?, ?, ?, ?)
    ''', (user_id, question_number, answer, is_correct, datetime.now()))
    conn.commit()
    conn.close()

def get_leaderboard(stage=None):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    if stage == 1:
        cursor.execute('SELECT user_id, nickname, stage_1_score, is_active FROM users ORDER BY stage_1_score DESC, nickname ASC')
    elif stage == 2:
        cursor.execute('SELECT user_id, nickname, total_score, is_active FROM users ORDER BY total_score DESC, nickname ASC')
    elif stage == 3:
        cursor.execute('SELECT user_id, nickname, total_score, is_active FROM users ORDER BY total_score DESC, nickname ASC')
    else:
        cursor.execute('SELECT user_id, nickname, total_score, is_active FROM users ORDER BY total_score DESC, nickname ASC')
    
    leaders = cursor.fetchall()
    conn.close()
    return leaders

def deactivate_user(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_active = FALSE WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_active_users():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users WHERE is_active = TRUE')
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

def is_user_registered(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users WHERE user_id = ?', (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

# Создание инлайн клавиатуры с вариантами ответов
def create_answer_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="1", callback_data="answer_1"))
    keyboard.add(InlineKeyboardButton(text="2", callback_data="answer_2"))
    keyboard.add(InlineKeyboardButton(text="3", callback_data="answer_3"))
    keyboard.add(InlineKeyboardButton(text="4", callback_data="answer_4"))
    return keyboard.as_markup()

# Генерация HTML таблицы и создание скриншота
async def generate_leaderboard_image(stage):
    """Асинхронная генерация изображения таблицы лидеров"""
    loop = asyncio.get_event_loop()
    try:
        # Запускаем синхронную функцию в отдельном потоке
        image_path = await loop.run_in_executor(None, sync_generate_leaderboard_image, stage)
        return image_path
    except Exception as e:
        print(f"Ошибка асинхронной генерации изображения: {e}")
        return None

def sync_generate_leaderboard_image(stage):
    """Синхронная версия генерации изображения (для запуска в отдельном потоке)"""
    try:
        leaders = get_leaderboard(stage)
        
        # Подготовка данных для шаблона
        players = []
        qualified_players = 0
        eliminated_players = 0
        
        for i, (user_id, nickname, score, is_active) in enumerate(leaders, 1):
            players.append({
                'rank': i,
                'nickname': html.escape(str(nickname)),
                'score': score,
                'qualified': bool(is_active)
            })
            if is_active:
                qualified_players += 1
            else:
                eliminated_players += 1
        
        template = Template(LEADERBOARD_TEMPLATE)
        html_content = template.render(
            stage=stage,
            players=players,
            total_players=len(leaders),
            qualified_players=qualified_players,
            eliminated_players=eliminated_players
        )
        
        # Сохраняем HTML во временный файл
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html_content)
            html_file = f.name
        
        # Упрощенные настройки Chrome для ускорения
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--hide-scrollbars')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-images')  # Ускоряет загрузку
        chrome_options.add_argument('--blink-settings=imagesEnabled=false')
        
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            driver.get(f'file:///{html_file}')
            
            # Минимальное ожидание вместо implicit_wait
            import time
            time.sleep(1)
            
            # Устанавливаем фиксированный размер окна
            driver.set_window_size(800, 600)
            
            # Делаем скриншот
            screenshot = driver.get_screenshot_as_png()
            
            # Сохраняем скриншот
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                f.write(screenshot)
                return f.name
                
        finally:
            driver.quit()
            os.unlink(html_file)
            
    except Exception as e:
        print(f"Ошибка синхронной генерации изображения: {e}")
        return None

# Обработчики команд
@dp.message(Command("start"))
async def start_command(message: types.Message):
    # Проверяем, что сообщение не от самого бота
    if message.from_user.is_bot:
        return
    
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    
    # Если викторина уже началась и пользователь не админ
    if current_state != QuizState.REGISTRATION and not is_admin(user_id):
        await send_styled_message(
            chat_id=user_id,
            text="❌ <b>Регистрация завершена!</b>\n\nВикторина уже началась. Вы не можете зарегистрироваться сейчас.",
            reply_to_message_id=message.message_id
        )
        return
    
    if is_user_registered(user_id):
        await send_styled_message(
            chat_id=user_id,
            text=f"✨ <b>Добро пожаловать назад, {first_name}!</b>\n\nВы уже зарегистрированы в викторине. Ожидайте начала игры!",
            reply_to_message_id=message.message_id
        )
        return
    
    # Сохраняем пользователя для регистрации
    user_registrations[user_id] = {"username": username, "first_name": first_name}
    
    welcome_text = f"""
✨ <b>Добро пожаловать в викторину, {first_name}!</b> 🎮

Для участия в увлекательной викторине нам нужно знать ваш игровой ник.

📝 <b>Пожалуйста, введите ваш игровой ник:</b>
    """
    
    await send_styled_message(
        chat_id=user_id,
        text=welcome_text,
        reply_to_message_id=message.message_id
    )

@dp.message(Command("reset_quiz"))
async def reset_quiz_command(message: types.Message):
    """
    ПОЛНЫЙ сброс викторины - удаляет ВСЕ данные пользователей
    """
    global current_state, current_question, question_timer, break_timer
    
    if not is_admin(message.from_user.id):
        await message.answer("❌ Эта команда только для администратора!")
        return
    
    # Запрашиваем подтверждение
    confirm_text = """
⚠️ <b>ОПАСНОЕ ДЕЙСТВИЕ</b>

Вы собираетесь УДАЛИТЬ ВСЕ ДАННЫЕ пользователей:
• Все регистрации
• Все результаты
• Все ответы
• Всю историю

❌ Это действие нельзя отменить!

Для подтверждения введите: <code>/reset_quiz confirm</code>
    """
    
    if "confirm" not in message.text.lower():
        await send_styled_message(
            message.from_user.id, 
            confirm_text,
            reply_to_message_id=message.message_id
        )
        return
    
    # ОТМЕНЯЕМ ВСЕ ТАЙМЕРЫ
    if question_timer:
        try:
            question_timer.cancel()
            question_timer = None
        except:
            pass
    
    if break_timer:
        try:
            break_timer.cancel()
            break_timer = None
        except:
            pass
    
    # ПОЛНОСТЬЮ ОЧИЩАЕМ БАЗУ ДАННЫХ
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    try:
        # Удаляем ВСЕ данные пользователей
        cursor.execute('DELETE FROM answers')  # Сначала ответы
        cursor.execute('DELETE FROM users')    # Затем пользователей
        
        # Сбрасываем состояние викторины
        cursor.execute('UPDATE quiz_state SET current_state = ?, current_question = ?, updated_at = ? WHERE id = 1', 
                      ("registration", 0, datetime.now()))
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        error_text = f"""
❌ <b>ОШИБКА ОЧИСТКИ БАЗЫ ДАННЫХ</b>

{str(e)}
        """
        await send_styled_message(
            message.from_user.id, 
            error_text,
            reply_to_message_id=message.message_id
        )
        return
        
    finally:
        conn.close()
    
    # СБРАСЫВАЕМ ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
    current_state = QuizState.REGISTRATION
    current_question = 0
    
    # ОЧИЩАЕМ ВСЕ ВРЕМЕННЫЕ ДАННЫЕ
    user_registrations.clear()
    countdown_messages.clear()
    question_messages.clear()
    last_bot_messages.clear()
    
    # УВЕДОМЛЯЕМ ВСЕХ ПРЕДЫДУЩИХ УЧАСТНИКОВ
    # (сохраняем список ID перед очисткой базы)
    try:
        temp_conn = sqlite3.connect(DATABASE_NAME)
        temp_cursor = temp_conn.cursor()
        temp_cursor.execute('SELECT user_id FROM users')
        previous_users = [row[0] for row in temp_cursor.fetchall()]
        temp_conn.close()
    except:
        previous_users = []
    
    notified_count = 0
    for user_id in previous_users:
        try:
            reset_text = """
🔄 <b>ВИКТОРИНА ПЕРЕЗАПУЩЕНА</b>

Администратор полностью сбросил викторину.
Все данные удалены, регистрация начата заново.

📝 <b>Для участия снова используйте:</b>
/start - новая регистрация

Ожидайте начала новой викторины!
            """
            await send_styled_message(user_id, reset_text)
            notified_count += 1
            await asyncio.sleep(0.1)  # анти-флуд
        except Exception as e:
            print(f"Ошибка отправки уведомления сброса {user_id}: {e}")
    
    # СТАТИСТИКА ДЛЯ АДМИНИСТРАТОРА
    admin_text = f"""
✅ <b>ПОЛНЫЙ СБРОС ВЫПОЛНЕН</b>

🗑️ <b>Удалены все данные:</b>
• Ответы: все
• Результаты: все

🎯 <b>Текущее состояние:</b>
• Этап: регистрация


📝 <b>Для начала новой викторины:</b>
/start_quiz
    """
    
    await send_styled_message(
        message.from_user.id, 
        admin_text,
        reply_to_message_id=message.message_id
    )
    
    print(f"Полный сброс викторины выполнен администратором {message.from_user.id}")

@dp.message(lambda message: message.from_user.id in user_registrations and not message.text.startswith('/'))
async def handle_nickname(message: types.Message):
    # Проверяем, что сообщение не от самого бота
    if message.from_user.is_bot:
        return
    
    user_id = message.from_user.id
    nickname = message.text.strip()
    user_data = user_registrations[user_id]
    first_name = user_data.get("first_name", "")
    
    # Если викторина уже началась и пользователь не админ
    if current_state != QuizState.REGISTRATION and not is_admin(user_id):
        await send_styled_message(
            chat_id=user_id,
            text="❌ <b>Регистрация завершена!</b>\n\nВикторина уже началась. Вы не можете зарегистрироваться сейчас.",
            reply_to_message_id=message.message_id
        )
        return
    
    if len(nickname) < 2:
        error_text = """
❌ <b>Слишком короткий ник!</b>

Ник должен содержать хотя бы 2 символа.
Попробуйте еще раз:
        """
        await send_styled_message(
            chat_id=user_id,
            text=error_text,
            reply_to_message_id=message.message_id
        )
        return
    
    if len(nickname) > 20:
        error_text = """
❌ <b>Слишком длинный ник!</b>

Ник должен быть не длиннее 20 символов.
Попробуйте еще раз:
        """
        await send_styled_message(
            chat_id=user_id,
            text=error_text,
            reply_to_message_id=message.message_id
        )
        return
    
    # Сохраняем пользователя
    add_user(user_id, user_data["username"], nickname)
    
    # Удаляем из временного хранилища
    del user_registrations[user_id]
    
    success_text = f"""
✅ <b>Регистрация завершена!</b>

🎮 <b>Ваш игровой ник:</b> <code>{nickname}</code>
👤 <b>Telegram:</b> @{user_data['username'] or 'скрыт'}

Теперь вы участвуете в викторине! 
Ожидайте начала игры от администратора.

⚡ <b>Команды:</b>
/stats - ваша статистика
/leaderboard - таблица лидеров
    """
    
    await send_styled_message(
        chat_id=user_id,
        text=success_text,
        reply_to_message_id=message.message_id
    )

@dp.message(Command("start_quiz"))
async def start_quiz_command(message: types.Message):
    global current_state, current_question, question_timer
    
    if not is_admin(message.from_user.id):
        await message.answer("❌ Эта команда только для администратора!")
        return
    
    # Загружаем актуальное состояние из БД
    load_quiz_state()
    
    # Если викторина была остановлена, продолжаем с того же места
    if current_state == "STOPPED":
        # Восстанавливаем предыдущее состояние из БД
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT current_state, current_question FROM quiz_state WHERE id = 1')
        state_data = cursor.fetchone()
        conn.close()
        
        if state_data:
            previous_state, previous_question = state_data
            current_state = previous_state
            current_question = previous_question
        else:
            current_state = QuizState.REGISTRATION
            current_question = 0
    
    if current_state == QuizState.REGISTRATION:
        # Начало новой викторины
        active_users_list = get_active_users()
        if not active_users_list:
            await message.answer("❌ Нет зарегистрированных пользователей!")
            return
        
        current_state = QuizState.STAGE_1
        current_question = 1
        save_quiz_state()
        
        await message.answer(f"🎯 Викторина начинается! Участников: {len(active_users_list)}")
        await send_countdown_to_all()
        await asyncio.sleep(3)
        await send_question_to_all(current_question)
        question_timer = asyncio.create_task(question_timeout())
        
    else:
        # Продолжение существующей викторины
        await message.answer(f"🔄 Продолжаем викторину с этапа {current_state}, вопроса {current_question}")
        
        # Отправляем уведомление о продолжении
        active_users = get_active_users()
        for user_id in active_users:
            try:
                continue_text = f"""
▶️ <b>ВИКТОРИНА ПРОДОЛЖАЕТСЯ</b>

Администратор возобновил викторину.
Приготовьтесь к продолжению!
                """
                await send_styled_message(user_id, continue_text)
            except Exception as e:
                print(f"Ошибка отправки уведомления продолжения {user_id}: {e}")
        
        await asyncio.sleep(2)
        
        # Продолжаем с текущего вопроса
        if current_question > 0:
            await send_question_to_all(current_question)
            question_timer = asyncio.create_task(question_timeout())
        else:
            await send_countdown_to_all()
            await asyncio.sleep(3)
            current_question = 1
            await send_question_to_all(current_question)
            question_timer = asyncio.create_task(question_timeout())


@dp.message(Command("stop_quiz"))
async def stop_quiz_command(message: types.Message):
    """
    Полная остановка викторины - замораживает текущее состояние
    """
    global question_timer, break_timer, current_state, current_question
    
    if not is_admin(message.from_user.id):
        await message.answer("❌ Эта команда только для администратора!")
        return
    
    # Отменяем ВСЕ активные таймеры
    timers_cancelled = 0
    if question_timer:
        try:
            question_timer.cancel()
            question_timer = None
            timers_cancelled += 1
        except:
            pass
    
    if break_timer:
        try:
            break_timer.cancel()
            break_timer = None
            timers_cancelled += 1
        except:
            pass
    
    # Сохраняем текущее состояние для возможного продолжения
    previous_state = current_state
    previous_question = current_question
    
    # Переводим викторину в режим "остановлено"
    current_state = "STOPPED"
    save_quiz_state()
    
    # Отправляем уведомление всем активным пользователям
    active_users = get_active_users()
    stopped_count = 0
    
    for user_id in active_users:
        try:
            stop_text = f"""
🛑 <b>ВИКТОРИНА ПРИОСТАНОВЛЕНА</b>

Администратор остановил викторину.
Текущее состояние сохранено.

📊 <b>Последнее состояние:</b>
• Вопрос: {previous_question}

Ожидайте возобновления викторины.
            """
            await send_styled_message(user_id, stop_text)
            stopped_count += 1
        except Exception as e:
            print(f"Ошибка отправки уведомления остановки {user_id}: {e}")
    
    # Статистика для администратора
    admin_text = f"""
✅ <b>ВИКТОРИНА ПОЛНОСТЬЮ ОСТАНОВЛЕНА</b>

📊 <b>Статистика остановки:</b>
• Отменено таймеров: {timers_cancelled}
• Уведомлено участников: {stopped_count}/{len(active_users)}
• Текущий этап: {previous_state}
• Текущий вопрос: {previous_question}

🔄 <b>Для продолжения используйте:</b>
/start_quiz - продолжить с текущего места
/reset_quiz - полный сброс (удалит ВСЕ данные)

⚡ <b>Текущее состояние сохранено в базе данных</b>
    """
    
    await send_styled_message(
        message.from_user.id, 
        admin_text,
        reply_to_message_id=message.message_id
    )

async def send_countdown_to_all():
    countdown_texts = [
        "🎯 ВИКТОРИНА НАЧИНАЕТСЯ!\n\nПриготовьтесь...",
        "3...",
        "2...", 
        "1...",
        "🎉 Начинаем!\n\nУдачи всем участникам!"
    ]
    
    last_message_id = None
    
    for text in countdown_texts:
        for user_id in get_active_users():
            try:
                message = await send_styled_message(
                    chat_id=user_id,
                    text=text,
                    reply_to_message_id=last_message_id
                )
                if message:
                    last_message_id = message.message_id
                    # Сохраняем для последующего удаления
                    if user_id not in last_bot_messages:
                        last_bot_messages[user_id] = []
                    last_bot_messages[user_id].append(message.message_id)
            except Exception as e:
                print(f"Ошибка отправки отсчета пользователю {user_id}: {e}")
        await asyncio.sleep(1)

async def send_question_to_all(question_number):
    photo_path = os.path.join(QUESTIONS_FOLDER, f"{question_number}.jpg")
    
    if not os.path.exists(photo_path):
        print(f"Файл {photo_path} не найден!")
        return
    
    photo = FSInputFile(photo_path)
    
    for user_id in get_active_users():
        try:
            # Удаляем предыдущие сообщения бота
            if user_id in last_bot_messages:
                for msg_id in last_bot_messages[user_id]:
                    try:
                        await bot.delete_message(user_id, msg_id)
                    except:
                        pass
                last_bot_messages[user_id] = []
            
            # Отправляем фото с вопросом и инлайн кнопками
            question_msg = await bot.send_photo(
                chat_id=user_id,
                photo=photo,
                caption=f"Выберите правильный ответ:",
                reply_markup=create_answer_keyboard()
            )
            
            # Сохраняем ID сообщения с вопросом
            question_messages[user_id] = question_msg.message_id
            
            # Затем отправляем сообщение с отсчетом времени
            countdown_msg = await bot.send_message(
                chat_id=user_id,
                text="⏰ Время на ответ: 20 секунд"
            )
            
            # Сохраняем ID сообщения для обновления
            countdown_messages[user_id] = countdown_msg.message_id
            
            # Сохраняем ID всех сообщений бота для этого пользователя
            if user_id not in last_bot_messages:
                last_bot_messages[user_id] = []
            last_bot_messages[user_id].extend([question_msg.message_id, countdown_msg.message_id])
            
        except Exception as e:
            print(f"Ошибка отправки вопроса {question_number} пользователю {user_id}: {e}")

async def update_countdown_timer(seconds_left):
    for user_id in get_active_users():
        if user_id in countdown_messages:
            try:
                await bot.edit_message_text(
                    chat_id=user_id,
                    message_id=countdown_messages[user_id],
                    text=f"⏰ Время на ответ: {seconds_left} секунд"
                )
            except Exception as e:
                print(f"Ошибка обновления таймера для пользователя {user_id}: {e}")

async def start_question_timer():
    global question_timer
    question_timer = asyncio.create_task(question_timeout())

async def question_timeout():
    global current_question, current_state, question_timer
    
    try:
        # Обновляем таймер каждые 5 секунд
        for seconds_left in [20, 15, 10, 5, 4, 3, 2, 1]:
            await asyncio.sleep(5 if seconds_left > 5 else 1)
            await update_countdown_timer(seconds_left)
        
        # Удаляем сообщения с отсчетом и вопросами
        for user_id in list(countdown_messages.keys()):
            try:
                # Удаляем сообщение с таймером
                await bot.delete_message(user_id, countdown_messages[user_id])
                
                # Удаляем сообщение с вопросом
                if user_id in question_messages:
                    await bot.delete_message(user_id, question_messages[user_id])
                
                # Очищаем список сообщений для этого пользователя
                if user_id in last_bot_messages:
                    last_bot_messages[user_id] = []
                    
            except Exception as e:
                print(f"Ошибка при удалении сообщений пользователя {user_id}: {e}")
        
        countdown_messages.clear()
        question_messages.clear()
        
        # Проверяем, является ли это концом этапа
        is_end_of_stage = (
            (current_state == QuizState.STAGE_1 and current_question == 10) or
            (current_state == QuizState.STAGE_2 and current_question == 20) or
            (current_state == QuizState.STAGE_3 and current_question == 30)
        )
        
        if is_end_of_stage:
            # Завершаем этап - отправляем таблицу лидеров ВСЕМ
            stage_number = 1 if current_state == QuizState.STAGE_1 else 2 if current_state == QuizState.STAGE_2 else 3
            await finish_stage(stage_number)
        else:
            # Переходим к следующему вопросу после 15-секундного перерыва
            current_question += 1
            save_quiz_state()
            
            # Отправляем сообщение о перерыве активным пользователям
            active_users = get_active_users()
            for user_id in active_users:
                try:
                    break_msg = await bot.send_message(user_id, "⏳ 15 секунд перед следующим вопросом...")
                    # Сохраняем ID сообщения о перерыве
                    if user_id not in last_bot_messages:
                        last_bot_messages[user_id] = []
                    last_bot_messages[user_id].append(break_msg.message_id)
                except Exception as e:
                    print(f"Ошибка отправки перерыва пользователю {user_id}: {e}")
            
            # Ждем 30 секунд
            await asyncio.sleep(15)
            
            # Очищаем сообщения о перерыве
            for user_id in active_users:
                if user_id in last_bot_messages:
                    for msg_id in last_bot_messages[user_id]:
                        try:
                            await bot.delete_message(user_id, msg_id)
                        except:
                            pass
                    last_bot_messages[user_id] = []
            
            # Отправляем следующий вопрос
            await send_question_to_all(current_question)
            question_timer = asyncio.create_task(question_timeout())
            
    except asyncio.CancelledError:
        # Таймер был отменен, это нормально
        print("Таймер вопроса отменен")
    except Exception as e:
        print(f"Критическая ошибка в question_timeout: {e}")
        # Пытаемся восстановить работу
        try:
            if question_timer:
                question_timer.cancel()
            question_timer = asyncio.create_task(question_timeout())
        except:
            pass

async def finish_stage(stage):
    global current_state, current_question
    
    # Создаем множество для отслеживания отправленных сообщений
    processing_messages = {}
    
    # Отправляем анимированное сообщение ВСЕМ участникам
    all_user_ids = get_all_users()
    
    for user_id in all_user_ids:
        try:
            # Отправляем начальное сообщение без анимации (только один раз)
            initial_text = f"📊 Подвожу итоги {stage} этапа..."
            msg = await bot.send_message(user_id, initial_text)
            processing_messages[user_id] = msg.message_id
            
            # Сохраняем для последующего удаления
            if user_id not in last_bot_messages:
                last_bot_messages[user_id] = []
            last_bot_messages[user_id].append(msg.message_id)
            
        except Exception as e:
            print(f"Ошибка отправки сообщения пользователю {user_id}: {e}")
    
    # СРАЗУ начинаем генерацию таблицы лидеров ПАРАЛЛЕЛЬНО с обновлением БД
    image_task = asyncio.create_task(generate_leaderboard_image(stage))
    
    # Параллельно обновляем баллы и деактивируем выбывших
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # Получаем список выбывших ДО обновления
    if stage == 1:
        cursor.execute('SELECT user_id, nickname FROM users WHERE stage_1_score < 7 AND is_active = TRUE')
        eliminated_users = cursor.fetchall()
        cursor.execute('UPDATE users SET is_active = FALSE WHERE stage_1_score < 7')
        current_state = QuizState.STAGE_2
        current_question = 11
        
    elif stage == 2:
        cursor.execute('SELECT user_id, nickname FROM users WHERE total_score < 14 AND is_active = TRUE')
        eliminated_users = cursor.fetchall()
        cursor.execute('UPDATE users SET is_active = FALSE WHERE total_score < 14')
        current_state = QuizState.STAGE_3
        current_question = 21
        
    elif stage == 3:
        cursor.execute('SELECT user_id, nickname FROM users WHERE is_active = TRUE')
        eliminated_users = []  # На 3 этапе все активные - победители
        current_state = QuizState.FINISHED
    
    conn.commit()
    conn.close()
    
    # Ждем завершения генерации изображения
    image_path = await image_task
    
    # Очищаем сообщения о обработке
    for user_id, msg_id in processing_messages.items():
        try:
            await bot.delete_message(user_id, msg_id)
            # Удаляем из last_bot_messages
            if user_id in last_bot_messages and msg_id in last_bot_messages[user_id]:
                last_bot_messages[user_id].remove(msg_id)
        except Exception as e:
            print(f"Ошибка удаления сообщения обработки {user_id}: {e}")
    
    # Отправляем уведомления выбывшим участникам
    if eliminated_users:
        for user_id, nickname in eliminated_users:
            try:
                elimination_text = f"""
😔 <b>К сожалению, вы выбыли из викторины!</b>

🏆 <b>Результат {stage} этапа:</b>
• Ваш ник: {nickname}
• Этап завершен

Спасибо за участие! Вы можете следить за продолжением викторины на нашем стриме. \n https://www.twitch.tv/cirkontp
                """
                await send_styled_message(user_id, elimination_text)
            except Exception as e:
                print(f"Ошибка отправки уведомления выбывшему {user_id}: {e}")
    
    # Получаем обновленный список ВСЕХ пользователей
    all_user_ids = get_all_users()
    
    # Очищаем предыдущие сообщения только у активных пользователей
    active_users = get_active_users()
    for user_id in active_users:
        if user_id in last_bot_messages:
            for msg_id in last_bot_messages[user_id][:]:  # Копируем список
                try:
                    await bot.delete_message(user_id, msg_id)
                except:
                    pass
            last_bot_messages[user_id] = []
    
    # Отправляем таблицу лидеров ВСЕМ пользователям
    sent_users = set()
    
    for user_id in all_user_ids:
        if user_id in sent_users:
            continue
            
        try:
            caption = f"🏆 <b>РЕЗУЛЬТАТЫ {stage} ЭТАПА</b>\n\n"
            
            if stage < 3:
                caption += "⏳ <i>Перерыв 2 минуты перед следующим этапом...</i>"
            else:
                caption += "🎉 <i>Викторина завершена! Спасибо всем за участие!</i>"
            
            if image_path and os.path.exists(image_path):
                try:
                    image = FSInputFile(image_path)
                    message = await bot.send_photo(
                        user_id, 
                        image, 
                        caption=caption,
                        parse_mode="HTML"
                    )
                    
                    # НЕ удаляем файл сразу! Сохраняем для других пользователей
                    if user_id not in last_bot_messages:
                        last_bot_messages[user_id] = []
                    last_bot_messages[user_id].append(message.message_id)
                    
                except Exception as e:
                    print(f"Ошибка отправки фото пользователю {user_id}: {e}")
                    # Fallback на текстовую версию
                    leaders = get_leaderboard(stage)
                    leaderboard_text = await generate_text_leaderboard(stage, leaders)
                    message = await bot.send_message(user_id, leaderboard_text, parse_mode="HTML")
            else:
                # Текстовая версия
                leaders = get_leaderboard(stage)
                leaderboard_text = await generate_text_leaderboard(stage, leaders)
                message = await bot.send_message(user_id, leaderboard_text, parse_mode="HTML")
            
            if user_id not in last_bot_messages:
                last_bot_messages[user_id] = []
            last_bot_messages[user_id].append(message.message_id)
            
            sent_users.add(user_id)
            
            # Небольшая задержка между отправками для избежания лимитов
            await asyncio.sleep(0.05)
            
        except Exception as e:
            print(f"Ошибка отправки таблицы лидеров пользователю {user_id}: {e}")
    
    # Удаляем временный файл ТОЛЬКО ПОСЛЕ отправки всем
    if image_path and os.path.exists(image_path):
        try:
            os.unlink(image_path)
        except:
            pass
    
    # Для 3 этапа сразу запускаем финиш викторины
    if stage == 3:
        await finish_quiz()
    else:
        # 2-минутный перерыв между этапами
        await asyncio.sleep(120)
        
        # Очищаем сообщения о перерыве у активных пользователей
        for user_id in active_users:
            if user_id in last_bot_messages:
                for msg_id in last_bot_messages[user_id][:]:
                    try:
                        await bot.delete_message(user_id, msg_id)
                    except:
                        pass
                last_bot_messages[user_id] = []
        
        # Начинаем следующий этап
        await send_countdown_to_all()
        await asyncio.sleep(3)
        await send_question_to_all(current_question)
        await start_question_timer()

async def generate_text_leaderboard(stage, leaders):
    """Генерация текстовой версии таблицы лидеров"""
    leaderboard_text = f"🏆 <b>РЕЗУЛЬТАТЫ {stage} ЭТАПА</b>\n\n"
    
    for i, (user_id, nickname, score, is_active) in enumerate(leaders[:15], 1):
        status = "✅" if is_active else "❌"
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
        leaderboard_text += f"{medal} {i}. {nickname} - {score} баллов {status}\n"
    
    if stage < 3:
        leaderboard_text += f"\n⏳ <i>Перерыв 2 минуты перед следующим этапом...</i>"
    else:
        leaderboard_text += f"\n🎉 <i>Викторина завершена! Спасибо всем за участие!</i>"
    
    return leaderboard_text

def get_eliminated_users(stage):
    """
    Получает список пользователей, которые выбыли на указанном этапе
    """
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    if stage == 1:
        cursor.execute('SELECT user_id, nickname FROM users WHERE stage_1_score < 7 AND is_active = FALSE')
    elif stage == 2:
        cursor.execute('SELECT user_id, nickname FROM users WHERE total_score < 14 AND is_active = FALSE')
    else:
        cursor.execute('SELECT user_id, nickname FROM users WHERE is_active = FALSE')
    
    eliminated = cursor.fetchall()
    conn.close()
    return eliminated

# Функция для получения всех ID пользователей
def get_all_users():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    user_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    # Добавляем админов и убираем дубликаты
    all_users = list(set(user_ids + ADMIN_IDS))
    return all_users

# Добавляем функцию для получения всех пользователей
def get_all_users():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users + ADMIN_IDS  # Добавляем админов

async def finish_quiz():
    # Очищаем предыдущие сообщения
    for user_id in get_active_users():
        if user_id in last_bot_messages:
            for msg_id in last_bot_messages[user_id][:]:
                try:
                    await bot.delete_message(user_id, msg_id)
                except:
                    pass
            last_bot_messages[user_id] = []
    
    # Определяем победителей
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, nickname, total_score FROM users WHERE is_active = TRUE ORDER BY total_score DESC')
    winners = cursor.fetchall()
    conn.close()
    
    if winners:
        winner_text = "🎉 <b>ПОБЕДИТЕЛИ ВИКТОРИНЫ!</b>\n\n"
        for i, (user_id, nickname, score) in enumerate(winners, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
            winner_text += f"{medal} {i}. {nickname} - {score} баллов\n"
        
        # Рассчитываем награду
        prize_per_winner = 15000000 // len(winners)
        winner_text += f"\n💰 <b>Каждый победитель получает: {prize_per_winner:,} миллионов</b>"
        
        # Отправляем победителям личные сообщения
        winner_ids_sent = set()
        for user_id, nickname, score in winners:
            try:
                if user_id not in winner_ids_sent:  # Предотвращаем дублирование
                    personal_text = f"""
🎉 <b>ПОЗДРАВЛЯЕМ, {nickname}!</b>

Вы стали победителем викторины!
🏆 Ваш результат: {score} баллов
💰 Ваш выигрыш: {prize_per_winner:,} миллионов

Спасибо за участие!
                    """
                    await send_styled_message(user_id, personal_text)
                    winner_ids_sent.add(user_id)
            except Exception as e:
                print(f"Ошибка отправки поздравления {user_id}: {e}")
        
        # Отправляем общий список ВСЕМ участникам (только один раз)
        all_users = get_all_users()
        sent_to_users = set()
        
        for user_id in all_users:
            if user_id not in sent_to_users:
                try:
                    await send_styled_message(user_id, winner_text)
                    sent_to_users.add(user_id)
                    await asyncio.sleep(0.05)  # Анти-флуд
                except Exception as e:
                    print(f"Ошибка отправки списка победителей {user_id}: {e}")

# Обработчик инлайн кнопок с ответами
@dp.callback_query(lambda c: c.data.startswith('answer_'))
async def handle_answer_callback(callback: types.CallbackQuery):
    global current_question
    
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    if not user or not user[7]:  # is_active
        await callback.answer("Вы не участвуете в викторине!")
        return
    
    if current_state == QuizState.REGISTRATION:
        await callback.answer("Викторина еще не началась!")
        return
    
    # Получаем выбранный ответ
    answer = int(callback.data.split('_')[1])
    correct_answers = QUESTIONS.get(current_question, [])
    
    # Проверяем, является ли это вопросом со всеми правильными ответами
    is_all_correct_question = current_question in ALL_CORRECT_QUESTIONS if isinstance(ALL_CORRECT_QUESTIONS, list) else current_question == ALL_CORRECT_QUESTION
    
    if is_all_correct_question:
        # Для вопроса со всеми правильными ответами - любой ответ правильный
        is_correct = True
        # Обновляем правильные ответы чтобы включить все варианты
        correct_answers = [1, 2, 3, 4]
    else:
        # Для обычных вопросов проверяем правильность
        is_correct = answer in correct_answers
    
    # Сохраняем ответ
    save_answer(user_id, current_question, answer, is_correct)
    
    # Обновляем счет
    conn = sqlite3.connect(DATABASE_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    
    if current_question <= 10:
        cursor.execute('SELECT stage_1_score FROM users WHERE user_id = ?', (user_id,))
        current_score = cursor.fetchone()[0]
        if is_correct:
            cursor.execute('UPDATE users SET stage_1_score = ? WHERE user_id = ?', (current_score + 1, user_id))
    elif current_question <= 20:
        cursor.execute('SELECT stage_2_score FROM users WHERE user_id = ?', (user_id,))
        current_score = cursor.fetchone()[0]
        if is_correct:
            cursor.execute('UPDATE users SET stage_2_score = ? WHERE user_id = ?', (current_score + 1, user_id))
    else:
        cursor.execute('SELECT stage_3_score FROM users WHERE user_id = ?', (user_id,))
        current_score = cursor.fetchone()[0]
        if is_correct:
            cursor.execute('UPDATE users SET stage_3_score = ? WHERE user_id = ?', (current_score + 1, user_id))
    
    cursor.execute('UPDATE users SET total_score = stage_1_score + stage_2_score + stage_3_score WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    # Убираем кнопки у пользователя, который ответил
    if user_id in question_messages:
        try:
            await bot.edit_message_reply_markup(
                chat_id=user_id,
                message_id=question_messages[user_id],
                reply_markup=None
            )
        except Exception as e:
            print(f"Ошибка при удалении кнопок: {e}")
    
    if is_correct:
        if is_all_correct_question:
            await callback.answer("✅ Правильно! +1 балл")
        else:
            await callback.answer("✅ Правильно! +1 балл")
    else:
        await callback.answer("❌ Неправильно!")

@dp.message(Command("stats"))
async def stats_command(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        error_text = """
❌ <b>Вы не зарегистрированы!</b>
Для участия в викторине используйте /start
        """
        await send_styled_message(
            chat_id=user_id,
            text=error_text,
            reply_to_message_id=message.message_id
        )
        return
    
    stats_text = f"""
📊 <b>Ваша статистика</b>

🎮 <b>Ник:</b> <code>{user[2]}</code>
🏆 <b>Общий счет:</b> {user[6]} баллов

📈 <b>По этапам:</b>
• Этап 1: {user[3]} баллов
• Этап 2: {user[4]} баллов  
• Этап 3: {user[5]} баллов
    """
    await send_styled_message(
        chat_id=user_id,
        text=stats_text,
        reply_to_message_id=message.message_id
    )

@dp.message(Command("leaderboard"))
async def leaderboard_command(message: types.Message):
    leaders = get_leaderboard()
    
    if not leaders:
        error_text = """
📊 <b>ТАБЛИЦА ЛИДЕРОВ</b>

😔 Пока здесь пусто...
Будьте первым! Используйте /start
        """
        await send_styled_message(
            chat_id=message.chat.id,
            text=error_text,
            reply_to_message_id=message.message_id
        )
        return
    
    leaderboard_text = """
🏆 <b>ОБЩАЯ ТАБЛИЦА ЛИДЕРОВ</b>

"""
    
    for i, (user_id, nickname, score, is_active) in enumerate(leaders[:10], 1):
        status = "✅" if is_active else "❌"
        leaderboard_text += f"{i}. {nickname} - {score} баллов {status}\n"
    
    leaderboard_text += """
────────────────────
⭐ Только лучшие попадают в топ!
    """
    
    await send_styled_message(
        chat_id=message.chat.id,
        text=leaderboard_text,
        reply_to_message_id=message.message_id
    )

@dp.message(Command("status"))
async def status_command(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("Эта команда только для администратора!")
        return
    
    active_count = len(get_active_users())
    total_count = len(get_leaderboard())
    eliminated_count = total_count - active_count
    
    # Получаем список выбывших
    eliminated_users = []
    if current_state == QuizState.STAGE_2:
        eliminated_users = get_eliminated_users(1)
    elif current_state == QuizState.STAGE_3:
        eliminated_users = get_eliminated_users(2)
    elif current_state == QuizState.FINISHED:
        eliminated_users = get_eliminated_users(3)
    
    status_text = f"""
📈 Статус викторины:

Текущий этап: {current_state}
Текущий вопрос: {current_question}
Всего участников: {total_count}
Активных участников: {active_count}
Выбывших участников: {eliminated_count}
"""
    
    if eliminated_users:
        status_text += "\n📉 Выбывшие:\n"
        for user_id, nickname in eliminated_users[:10]:  # Показываем первые 10
            status_text += f"• {nickname} (ID: {user_id})\n"
        if len(eliminated_users) > 10:
            status_text += f"• ... и еще {len(eliminated_users) - 10}\n"
    
    await message.answer(status_text)



# Запуск бота
async def main():
    init_database()
    load_quiz_state()  # Загружаем состояние при старте
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())