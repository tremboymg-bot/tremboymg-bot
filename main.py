from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os
TOKEN = os.environ.get("TOKEN")
async def start(u,c): await u.message.reply_text("🚂 TREMBOYMG online!")
async def regras(u,c): await u.message.reply_text("📜 REGRAS: sem golpe, sem porn, respeita geral")
async def welcome(u,c):
 for m in u.message.new_chat_members:
  await u.message.reply_text(f"🚂 OLHA O TREM, {m.first_name}! Bem-vindo ao TREMBOYMG MG 🔥")
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("regras", regras))
app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
app.run_polling()
