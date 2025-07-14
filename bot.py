import logging

import bot_secrets
import telebot

logging.basicConfig(
    format="[%(levelname)s %(asctime)s %(module)s:%(lineno)d] %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

bot = telebot.TeleBot(bot_secrets.TOKEN)


@bot.message_handler(commands=["start"])
def send_welcome(message: telebot.types.Message):
    logger.info(f"+ Start chat #{message.chat.id} from {message.chat.username}")
    bot.reply_to(message, "🤖 Welcome! 🤖")


@bot.message_handler(func=lambda m: True)
def echo_all(message: telebot.types.Message):
    logger.info(f"[#{message.chat.id}.{message.message_id} {message.chat.username!r}] {message.text!r}")
    bot.reply_to(message, f"You said: {message.text}")


logger.info("> Starting bot")
bot.infinity_polling()
logger.info("< Goodbye!")
