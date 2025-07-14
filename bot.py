import logging
import telebot
from telebot import types
import json
from datetime import datetime
import bot_secrets  # חייב להכיל את TOKEN שלך

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
    "Center": "Centre",
    "South": "South",
    "Nearby": "Centre"
}


# ----------- /start -----------
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("North", "Centre", "South", "Nearby")
    bot.send_message(
        user_id,
        "Welcome to Saeed, Raz and Yara's TravelBot! 🌍\nLet’s plan your next trip.\nChoose a travel area:",
        reply_markup=markup,
    )
    user_state[user_id] = {"area": None, "index": 0, "history": []}


# ----------- area selection -----------
@bot.message_handler(func=lambda m: m.text in area_map)
def select_area(message):
    user_id = message.chat.id
    selected_area = area_map[message.text]
    user_state[user_id]["area"] = selected_area
    user_state[user_id]["index"] = 0
    bot.send_message(user_id, f"Great! You chose the {selected_area} 🌄\nLooking for a great trail for you...")

    # מייד שולח המלצה
    suggest_trip(message)


# ----------- /suggestions -----------
@bot.message_handler(commands=["suggestions"])
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
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("👍", "👎")

    message_text = f"""Here are some trip options in the {state["area"]}:

{trip['title']}
{trip['description']}
{trip['image_url']}
{trip['place']}

"""
    bot.send_message(user_id, message_text, parse_mode="Markdown", reply_markup=markup)


# ----------- feedback on suggestion (👍 / 👎) -----------
@bot.message_handler(func=lambda m: m.text in ["👍", "👎"])
def handle_feedback(message):
    user_id = message.chat.id
    state = user_state.get(user_id)
    if not state or not state["area"]:
        bot.send_message(user_id, "Please start by selecting an area using /start.")
        return

    area_trips = [t for t in all_trips if t["area"] == state["area"]]
    index = state["index"]
    if index >= len(area_trips):
        bot.send_message(user_id, "No more suggestions available.")
        return

    trip = area_trips[index]

    if message.text == "👍":
        saved = {
            "title": trip["title"],
            "area": trip["area"],
            "date": datetime.now().strftime("%B %d")
        }
        state["history"].append(saved)
        bot.send_message(user_id, f"✅ {trip['title']} saved to your trip history!")
        bot.send_message(user_id, f" gemini text")
    else:
        bot.send_message(user_id, "skipped")
        state["index"] += 1
        suggest_trip(message)


# ----------- /history -----------
@bot.message_handler(commands=["history"])
def show_history(message):
    user_id = message.chat.id
    state = user_state.get(user_id)
    if not state or not state["history"]:
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
    bot.send_message(user_id, "✅ All saved trips have been cleared.")


@bot.message_handler(func=lambda m: m.text == "No")
def cancel_clear(message):
    bot.send_message(message.chat.id, "❎ Trip history was not deleted.")


# ----------- Run bot -----------
logger.info("> Bot is running...")
bot.infinity_polling()
