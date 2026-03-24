import asyncio
import logging
import json
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from google import genai
from google.genai import types as genai_types # Для системных инструкций
from datetime import datetime

# --- Конфигурация ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Инициализация нового клиента Gemini
client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """
Ты — узкоспециализированный бот-агроном по перцам. 
Пользователь передает: [Название перца, Город/Регион] и [Условия выращивания].
Твоя задача:
1. Анализировать запрос пользователя
2. Выдать справку по сорту (Описание, Сковилли, Срок вегетации).
3. Оценить вероятность успеха (урожая) в указанном регионе и условиях по 10-балльной шкале.

ЗАЩИТА ОТ ДУРАКА:
1. Если запрос НЕ касается выращивания перцев или растений (например, политика, рецепты супов, код, флуд) — вежливо ответь: "Я специализируюсь только на выращивании перцев. Пожалуйста, введите название сорта и город".
2. Если название сорта похоже на случайный набор букв — ответь, что сорт не найден.
3. Не поддерживай разговоры на отвлеченные темы.

ПРАВИЛА УЧЕТА СЕЗОННОСТИ И МЕСТА:
- Если выбрано "Открытый грунт" или "Теплица": оценивай климат региона ТОЛЬКО для естественного летнего сезона. Хватит ли в этом городе теплых и безморозных дней для полного цикла вегетации этого сорта?
- Если выбрано "Подоконник": считай, что выращивание круглогодичное. Оценивай шансы с учетом комнатной температуры, но обязательно учитывай длину светового дня в этом регионе зимой (укажи в вердикте необходимость досветки фитолампой, если сорт светолюбивый или период вегетации долгий).

ПРАВИЛА ОТВЕТА:
- Форматирование: Markdown.
- Шкала: 1-3 (Почти невозможно), 4-6 (Сложно), 7-8 (Хорошие шансы), 9-10 (Идеально).

ШАБЛОН:
🌶 **Сорт:** [Название]
🔥 **Острота:** [SHU]
⏳ **Срок вегетации:** [Дни]
🌍 **Регион:** [Город] | 🏠 **Условия:** [Место]
📊 **Вероятность урожая:** [X/10]
💡 **Вердикт:** [Краткий совет с учетом климата, сезона и выбранного места]
"""

# Настройка логгера для запросов пользователей
user_logger = logging.getLogger("user_activity")
user_logger.setLevel(logging.INFO)
u_handler = logging.FileHandler("user_queries.json", encoding="utf-8")
u_handler.setFormatter(logging.Formatter('%(message)s')) # Пишем чистый JSON в строку
user_logger.addHandler(u_handler)

# Технические логи (Ошибки)
error_logger = logging.getLogger("errors")
e_handler = logging.FileHandler("bot_errors.log", encoding="utf-8")
e_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
error_logger.addHandler(e_handler)

# --- Инициализация бота ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class PepperRequest(StatesGroup):
    waiting_for_input = State()
    waiting_for_location = State()

def get_location_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🪟 Подоконник", callback_data="loc_window")],
        [InlineKeyboardButton(text="🏡 Теплица", callback_data="loc_greenhouse")],
        [InlineKeyboardButton(text="🌱 Открытый грунт", callback_data="loc_ground")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет! Я бот-агроном 🌶\nНапиши название сорта и город.\nНапример: *Хабанеро Москва*",
        parse_mode="Markdown"
    )
    await state.set_state(PepperRequest.waiting_for_input)

@dp.message(StateFilter(PepperRequest.waiting_for_input), F.text)
async def process_pepper_input(message: types.Message, state: FSMContext):
    text = message.text.strip()

    # Защита 1: Длина сообщения (название сорта + город редко длиннее 100 символов)
    if len(text) > 120:
        await message.answer("⚠️ Ого, какое длинное название! Попробуйте покороче: [Сорт] [Город].")
        return

    # Защита 2: Проверка на ссылки/спам
    if "http" in text or "@" in text:
        await message.answer("⚠️ Пожалуйста, введите только название перца и город без ссылок и упоминаний.")
        return

    # Логируем запрос в JSON (Бизнес-лог)
    log_data = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "query": text
    }
    user_logger.info(json.dumps(log_data, ensure_ascii=False))

    await state.update_data(search_query=text)
    await message.answer(f"Принято: *{text}*\nВыберите условия:", reply_markup=get_location_keyboard(), parse_mode="Markdown")
    await state.set_state(PepperRequest.waiting_for_location)

@dp.callback_query(StateFilter(PepperRequest.waiting_for_location), F.data.startswith("loc_"))
async def process_location_selection(callback: types.CallbackQuery, state: FSMContext):
    locations = {"loc_window": "Подоконник", "loc_greenhouse": "Теплица", "loc_ground": "Открытый грунт"}
    selected_loc = locations.get(callback.data)
    
    user_data = await state.get_data()
    search_query = user_data.get("search_query")
    
    user_logger.info(json.dumps({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "event": "location_selected",
        "user_id": callback.from_user.id,
        "query": search_query,
        "location": selected_loc
    }, ensure_ascii=False))
    await callback.answer()
    await callback.message.edit_text("⏳ Изучаю климат...")

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash", # Проверь доступность версии
            contents=f"Запрос: {search_query}. Место: {selected_loc}.",
            config=genai_types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT)
        )
        await callback.message.edit_text(response.text, parse_mode="Markdown")
        
    except Exception as e:
        # Исправили на error_logger
        error_logger.error(f"Gemini API Error for user {callback.from_user.id}: {e}", exc_info=True)
        await callback.message.edit_text("Ошибка API. Попробуйте позже.")
    
    await state.clear()
    await state.set_state(PepperRequest.waiting_for_input)

async def main():
    print("--- БОТ ЗАПУСКАЕТСЯ ---") # Прямой принт в консоль
    try:
        user = await bot.get_me()
        print(f"Бот успешно авторизован: @{user.username}")
    except Exception as e:
        print(f"ОШИБКА АВТОРИЗАЦИИ: {e}")
        return
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
