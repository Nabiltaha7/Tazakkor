from .config import TOKEN
import telebot

if not TOKEN:
    raise ValueError("❌ TOKEN is missing! Check environment variables")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
bot_username = None
