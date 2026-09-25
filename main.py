import os, re, feedparser
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler

TOKEN = os.getenv("TOKEN")
RSS_URL = "https://cointelegraph.com.br/rss"
CANAL_ID = "@tremboymgoficial"
LINK = "https://t.me/tremboymgoficial"

def limpar(t):
    t = re.sub(r'<[^>]+>', '', t)
    return t.replace('&nbsp;',' ').replace('&quot;','"').strip()[:700]

async def enviar(context):
    try:
        feed = feedparser.parse(RSS_URL)
        post = feed.entries[0]
        titulo = limpar(post.title)
        resumo = limpar(post.get("summary",""))
        texto = f"🚂 TREMBOYMG CRIPTO NEWS 🚂\n\n📰 {titulo}\n\n{resumo}\n\n👉 Fonte no botão"
        botoes = [[InlineKeyboardButton("📖 LER COMPLETO", url=post.link)], [InlineKeyboardButton("🚀 TREM VIP", url=LINK)]]
        await context.bot.send_message(chat_id=CANAL_ID, text=texto, reply_markup=InlineKeyboardMarkup(botoes))
    except Exception as e:
        print(e)

async def start(update, context):
    await enviar(context)
    await update.message.reply_text("✅ Limpo e em PT-BR!")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.job_queue.run_repeating(enviar, interval=3600, first=10)
app.run_polling()
