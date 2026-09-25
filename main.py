import os, sqlite3, httpx
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ["BOT_TOKEN"]
PUSH_TOKEN = os.environ["PUSH_TOKEN"]
CANAL_ID = -1000000000000 # << TROCA AQUI PELO ID DO SEU CANAL VIP

PLANOS = {
    "15dias": {"nome": "15 DIAS", "valor": 711, "dias": 15},
    "mensal": {"nome": "1 MÊS", "valor": 1440, "dias": 30},
    "anual": {"nome": "1 ANO", "valor": 7000, "dias": 365}
}

def db():
    con = sqlite3.connect("vips.db", check_same_thread=False)
    con.execute("CREATE TABLE IF NOT EXISTS vendas (pix_id TEXT PRIMARY KEY, user_id INTEGER, plano TEXT, status TEXT, expira TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS acessos (user_id INTEGER PRIMARY KEY, expira TEXT)")
    con.commit()
    return con

async def criar_pix(v):
    async with httpx.AsyncClient() as c:
        r = await c.post("https://api.pushinpay.com.br/api/pix/cashIn", headers={"Authorization": f"Bearer {PUSH_TOKEN}"}, json={"value": v}, timeout=20)
        j = r.json()
        if r.status_code!=200 or not j.get("qr_code"): raise Exception(str(j))
        return j

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton(f"{v['nome']} - R$ {v['valor']/100:.2f}", callback_data=k)] for k,v in PLANOS.items()]
    await update.message.reply_text("Escolha seu VIP 👇", reply_markup=InlineKeyboardMarkup(kb))

async def gerar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    pix = await criar_pix(PLANOS[q.data]["valor"])
    con = db(); con.execute("INSERT OR REPLACE INTO vendas VALUES (?,?,?,?,?)", (pix["id"], q.from_user.id, q.data, "pendente", None)); con.commit(); con.close()
    context.user_data["pix_id"] = pix["id"]
    await q.message.reply_text(f"`{pix['qr_code']}`", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ JÁ PAGUEI", callback_data="ver")]]))

async def verificar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    pix_id = context.user_data.get("pix_id")
    if not pix_id: return
    con = db()
    row = con.execute("SELECT user_id, plano, status FROM vendas WHERE pix_id=?", (pix_id,)).fetchone()
    if not row or row[2]=="liberado": con.close(); return
    async with httpx.AsyncClient() as c:
        r = await c.get(f"https://api.pushinpay.com.br/api/transactions/{pix_id}", headers={"Authorization": f"Bearer {PUSH_TOKEN}"}, timeout=20)
        if r.json().get("status")!="paid": con.close(); await q.message.reply_text("Ainda não caiu"); return
        link = await context.bot.create_chat_invite_link(chat_id=CANAL_ID, member_limit=1)
        user_id, plano_key = row[0], row[1]
        atual = con.execute("SELECT expira FROM acessos WHERE user_id=?", (user_id,)).fetchone()
        base = datetime.fromisoformat(atual[0]) if atual and datetime.fromisoformat(atual[0]) > datetime.now() else datetime.now()
        nova_expira = base + timedelta(days=PLANOS[plano_key]["dias"])
        con.execute("UPDATE vendas SET status='liberado', expira=? WHERE pix_id=?", (nova_expira.isoformat(), pix_id))
        con.execute("INSERT OR REPLACE INTO acessos VALUES (?,?)", (user_id, nova_expira.isoformat())); con.commit()
        await q.message.reply_text(f"LIBERADO até {nova_expira.strftime('%d/%m/%Y')}\n{link.invite_link}")
    con.close(); context.user_data.clear()

async def checar_vencidos(context: ContextTypes.DEFAULT_TYPE):
    con = db()
    vencidos = con.execute("SELECT user_id FROM acessos WHERE expira <=?", (datetime.now().isoformat(),)).fetchall()
    for (uid,) in vencidos:
        try:
            await context.bot.ban_chat_member(CANAL_ID, uid); await context.bot.unban_chat_member(CANAL_ID, uid); con.execute("DELETE FROM acessos WHERE user_id=?", (uid,))
        except: pass
    con.commit(); con.close()

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(gerar, pattern="^(15dias|mensal|anual)$"))
app.add_handler(CallbackQueryHandler(verificar, pattern="^ver$"))
app.job_queue.run_repeating(checar_vencidos, interval=300, first=10)
app.run_polling()
