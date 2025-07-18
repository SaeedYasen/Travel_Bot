import logging

import requests
import telebot
from telebot import types
import json
from datetime import datetime
import bot_secrets  # חייב להכיל את TOKEN שלך
import re
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from datetime import datetime

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from promptic import llm
from pydantic import BaseModel
from bot_secrets import GEMINI_API_KEY,API_WHETHER

class GeminiAnswer(BaseModel):
    answer: str


@llm(
    model="gemini/gemini-1.5-flash",
    api_key=GEMINI_API_KEY,
)
def ask_gemini_about_trip(title: str, place: str,temp:int) -> str:
    """
    כתוב תקציר קצר ומעניין בעברית על אתר הטיול הבא:

    כותרת: {title}
    מיקום: {place}
    טמפרטורה: {temp}

    השתמש במידע הזה וכתוב תיאור ב-5 שורות לכל היותר, בפורמט של בולטים עם אימוג'ים.
    כלול בקצרה:
    - קצת היסטוריה על המקום
    - מה אפשר לראות ולעשות שם (רק הדברים הכי חשובים)
    - למה כדאי לבקר בו
    - שעות פתיחה אם יש
    - אל תשכח להחזיר את הפלט בפורמט טקסט שמתאים לטלגרם.
    """


def get_temp(city, api_wether):
    url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_wether}&units=metric'
    r = requests.get(url)
    data = r.json()
    if r.status_code == 200 and 'main' in data and 'temp' in data['main']:
        return f"{data['main']['temp']}°C"
    elif 'message' in data:
        return f"Weather API error: {data['message']}"
    else:
        return "Temperature info not available"

def escape_markdown(text):
    """
    בורחת תווים בעייתיים עבור parse_mode="Markdown"
    """
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)


# Bot setup
bot = telebot.TeleBot(bot_secrets.TOKEN)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state
user_state = {}  # user_id -> { "area": ..., "index": ..., "history": [...] }

# Load trip data once
with open("db.json", "r", encoding="utf-8") as f:
    all_trips = json.load(f)

area_map = {
    "North": "North",
    "Centre": "Centre",
    "South": "South",

}



# ----------- Feedback handler for 👍 / 👎 -----------

@bot.callback_query_handler(func=lambda call: call.data in ["like", "dislike"])
def handle_feedback(call):
    user_id = call.message.chat.id
    logger.info(f"[User {user_id}] feedback: {call.data}")

    state = user_state.get(user_id)

    # בדיקה שהמשתמש התחיל עם /start ובחר אזור
    if not state or not state.get("area"):
        bot.send_message(user_id, "Please start by selecting an area using /start.")
        return

    # קבלת רשימת טיולים לפי האזור הנבחר
    area_trips = [t for t in all_trips if t["area"] == state["area"]]
    index = state.get("index", 0)

    if index >= len(area_trips):
        bot.send_message(user_id, "No more suggestions available.")
        return

    trip = area_trips[index]
    temp = state.get("last_temp", "N/A")

    # פעולת "אהבתי" בלבד - שמירת הטיול בהיסטוריה והצגת תוכן מורחב
    if call.data == "like":
        saved = {
            "title": trip["title"],
            "area": trip["area"],
            "date": datetime.now().strftime("%B %d")
        }

        saved_json = json.dumps(saved, sort_keys=True)

        # שמירה למבנה היסטוריה ומניעת כפילויות
        state.setdefault("history", [])
        state.setdefault("history_set", set())

        if saved_json not in state["history_set"]:
            state["history_set"].add(saved_json)
            state["history"].append(saved)
            bot.send_message(user_id, f"✅ {trip['title']} saved to your trip history!")
        else:
            bot.send_message(user_id, f"ℹ️ {trip['title']} is already in your trip history.")

        # ניסיון לשלוף מידע מורחב מג'מיני, fallback במקרה של שגיאה
        try:
            gemini_text = ask_gemini_about_trip(trip["title"], trip["place"], temp)
        except Exception as e:
            print("Gemini error:", e)
            gemini_text = trip.get("expanded_description", "No additional description available.")

        # שליחת תגובה עם מידע נוסף וכפתור "עוד הרפתקאות"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Show More Adventures", callback_data="show_more"))

        bot.send_message(
            user_id,
            f"📍 {trip['title']}\n\nמזג האוויר היום: {temp}\n\n{gemini_text}",
            reply_markup=markup
        )

    else:
        state["index"] += 1
        suggest_trip(call.message)
    bot.answer_callback_query(call.id)


# ----------- when clicking "Show More Adventures" Inline button -----------
@bot.callback_query_handler(func=lambda call: call.data == "show_more")
def handle_show_more_callback(call):
    user_id = call.message.chat.id
    state = user_state.get(user_id)
    if not state:
        bot.send_message(user_id, "Please start with /start")
        return

    state["index"] += 1
    bot.answer_callback_query(call.id)
    suggest_trip(call.message)


@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.chat.id
    previous_state = user_state.get(user_id, {})
    previous_history = previous_state.get("history", [])
    previous_index = previous_state.get("index", 0)

    user_state[user_id] = {
        "area": None,
        "index": previous_index,  # שמירה על ההתקדמות הקודמת
        "history": previous_history,
        "history_set": set(
            json.dumps(item, sort_keys=True) for item in previous_history
        )
    }

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("North", callback_data="area_North"),
        InlineKeyboardButton("Centre", callback_data="area_Centre"),
        InlineKeyboardButton("South", callback_data="area_South")
    )
    bot.send_message(
        user_id,
        "Welcome to Saeed, Raz and Yara's TravelBot! 🌍\nLet’s plan your next trip.\nChoose a travel area:",
        reply_markup=markup
    )




@bot.callback_query_handler(func=lambda call: call.data.startswith("area_"))
def handle_area_selection(call):
    user_id = call.message.chat.id
    selected_area = call.data.split("_")[1]
    logger.info(f"[User {user_id}] selected area: {selected_area}")

    state = user_state.get(user_id)

    state["area"] = selected_area

    # מיון כל הטיולים של האזור שנבחר
    area_trips = [t for t in all_trips if t["area"] == selected_area]

    # חישוב index לפי כמות טיולים שנשמרו מהאזור הזה
    seen_titles = {item["title"] for item in state.get("history", []) if item["area"] == selected_area}
    for i, trip in enumerate(area_trips):
        if trip["title"] not in seen_titles:
            state["index"] = i
            break
    else:
        # אם כל הטיולים כבר נראו - נעבור לסוף הרשימה
        state["index"] = len(area_trips)

    bot.answer_callback_query(call.id)
    bot.send_message(user_id, f"Great! You chose the {selected_area} 🌄\nLooking for a great trail for you...")
    suggest_trip(call.message)



# ----------- send trip suggestion with inline like/dislike -----------
def suggest_trip(message):
    user_id = message.chat.id
    state = user_state.get(user_id)
    if not state or not state["area"]:
        bot.send_message(user_id, "Please select a travel area first using /start.")
        return

    area_trips = [t for t in all_trips if t["area"] == state["area"]]
    index = state["index"]

    if index >= len(area_trips):
        bot.send_message(user_id, "✅ You’ve seen all trip suggestions in this area.")
        return

    trip = area_trips[index]
    try:
        temp = get_temp(trip.get('place', 'israel'), api_wether=API_WHETHER)
        state["last_temp"] = temp
    except Exception as e:
        temp = f"Temperature info not available ({e})"

    bot.send_photo(
        chat_id=user_id,
        photo=trip.get('image_url', '')
    )

    message_text = (
        f"Here are some trip options in the {state.get('area', 'unknown area')}:\n\n"
        f"{trip.get('title', 'No title')}\n"
        f"{temp}\n"
        f"{trip.get('description', '')}\n"
        f"{trip.get('place', '')}"
    )

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("👍", callback_data="like"),
        InlineKeyboardButton("👎", callback_data="dislike")
    )

    bot.send_message(user_id, message_text, reply_markup=markup)



# ----------- area selection -----------
@bot.message_handler(func=lambda m: m.text in area_map)
def select_area(message):
    user_id = message.chat.id
    selected_area = area_map[message.text]
    user_state[user_id]["area"] = selected_area
    user_state[user_id]["index"] = 0
    bot.send_message(user_id, f"Great! You chose the {selected_area} 🌄\nLooking for a great trail for you...")
    suggest_trip(message)

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton



def save_trip(user_id, trip, area):
    if user_id not in user_state:
        user_state[user_id] = {"history": [], "history_set": set()}

    saved = {
        "title": trip["title"],
        "area": area,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    saved_json = json.dumps(saved, sort_keys=True)

    if saved_json not in user_state[user_id]["history_set"]:
        user_state[user_id]["history"].append(saved)
        user_state[user_id]["history_set"].add(saved_json)



# ----------- /history -----------

@bot.message_handler(commands=["history"])
def show_history(message):
    user_id = message.chat.id
    state = user_state.get(user_id)

    if not state or not state.get("history"):
        bot.send_message(user_id, "📭 No saved trips yet.")
        return

    history = state["history"]
    response = "🗺️ Saved Trips:\n"
    for i, trip in enumerate(history, 1):
        response += f"{i}. {trip['title']} – {trip['area']} – saved on {trip['date']}\n"

    bot.send_message(user_id, response)


# ----------- /clear -----------
@bot.message_handler(commands=["clear"])
def clear_history(message):
    user_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Yes", "No")
    bot.send_message(user_id, "⚠️ Are you sure you want to delete your entire trip history?", reply_markup=markup)


@bot.message_handler(func=lambda m: m.text == "Yes")
def confirm_clear(message):
    user_id = message.chat.id
    if user_id in user_state:
        user_state[user_id]["history"] = []
        user_state[user_id]["history_set"] = set()
    bot.send_message(user_id, "✅ All saved trips have been cleared.")


@bot.message_handler(func=lambda m: m.text == "No")
def cancel_clear(message):
    bot.send_message(message.chat.id, "❎ Trip history was not deleted.")
@bot.message_handler(func=lambda m: True)
def log_user_message(message):
    user_id = message.chat.id
    user_text = message.text
    logger.info(f"[User {user_id}] sent message: {user_text}")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# ----------- Run bot -----------
logger.info("> Bot is running...")
bot.infinity_polling()
