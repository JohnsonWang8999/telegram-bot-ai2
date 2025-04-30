import os
import asyncio
from datetime import datetime
from flask import Flask, request
from telegram import (Update, InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters)

# === Globals ===
current_month = datetime.now().strftime("%Y-%m")
current_unit = None
pending_action = None
records = {}

# === Setup ===
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH", "myhook")
PORT = int(os.environ.get("PORT", 10000))
BASE_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}"

flask_app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()

UNITS = [
    "Danga Bay 16A-01-02",
    "Danga Bay 7A-18-03A",
    "Danga Bay 17C-19-02",
    "RNF 6A-13A-09",
    "RNF B1-1 23-06"
]

# === Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("\U0001F4C2 查看账单", callback_data="view")],
        [InlineKeyboardButton("\U0001F4DD 记录消费", callback_data="add")],
        [InlineKeyboardButton("\U0001F4C5 切换月份", callback_data="switch")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("欢迎使用 Short Escape Telegram Bot!\n\n请选择操作：", reply_markup=reply_markup)

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global pending_action
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == "add":
        pending_action = "add"
        await query.edit_message_text("请选择房源：", reply_markup=unit_keyboard())
    elif action == "view":
        pending_action = "view"
        await query.edit_message_text("请选择房源：", reply_markup=unit_keyboard(include_all=True))
    elif action == "switch":
        pending_action = "switch"
        await query.edit_message_text("请选择月份：", reply_markup=month_keyboard())
    elif action.startswith("unit_"):
        global current_unit
        current_unit = action[5:]
        if pending_action == "add":
            await query.edit_message_text("请发送消费内容，例如：换灯泡 RM100")
        elif pending_action == "view":
            await show_records(query, current_unit)
    elif action.startswith("month_"):
        global current_month
        current_month = action[6:]
        await query.edit_message_text(f"月份已切换为：{current_month}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_unit, current_month
    if not current_unit:
        await update.message.reply_text("请先选择房源")
        return
    text = update.message.text
    key = (current_unit, current_month)
    if key not in records:
        records[key] = []
    records[key].append(text)
    await update.message.reply_text("记录成功！")

async def show_records(query, unit):
    global current_month
    text = f"\U0001F4C5 {current_month} 消费记录汇总：\n"
    total_all = 0
    if unit == "all":
        for u in UNITS:
            key = (u, current_month)
            unit_records = records.get(key, [])
            if unit_records:
                text += f"\n\U0001F3E1 {u}："
                unit_total = 0
                for record in unit_records:
                    text += f"\n - {record}"
                    try:
                        amount = float(record.split("RM")[-1])
                        unit_total += amount
                    except:
                        pass
                total_all += unit_total
                text += f"\n 小计：RM{unit_total:.2f}\n"
        text += f"\n\uD83D\uDCB0 总支出：RM{total_all:.2f}"
    else:
        key = (unit, current_month)
        unit_records = records.get(key, [])
        unit_total = 0
        if unit_records:
            text += f"\n\U0001F3E1 {unit}："
            for record in unit_records:
                text += f"\n - {record}"
                try:
                    amount = float(record.split("RM")[-1])
                    unit_total += amount
                except:
                    pass
            text += f"\n 总支出：RM{unit_total:.2f}"
        else:
            text += "\n无记录"
    await query.edit_message_text(text)

# === Keyboards ===
def unit_keyboard(include_all=False):
    buttons = [[InlineKeyboardButton(unit, callback_data=f"unit_{unit}")] for unit in UNITS]
    if include_all:
        buttons.insert(0, [InlineKeyboardButton("全部单位", callback_data="unit_all")])
    return InlineKeyboardMarkup(buttons)

def month_keyboard():
    now = datetime.now()
    months = [(now.year, now.month), (now.year, now.month - 1)]
    buttons = []
    for y, m in months:
        if m <= 0:
            y -= 1
            m += 12
        month_str = f"{y}-{m:02}"
        buttons.append([InlineKeyboardButton(month_str, callback_data=f"month_{month_str}")])
    return InlineKeyboardMarkup(buttons)

# === Telegram + Flask Webhook ===
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(handle_button))
application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

@flask_app.route(f"/{WEBHOOK_SECRET_PATH}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run(application.process_update(update))
    return "ok"

if __name__ == "__main__":
    async def run():
        await application.initialize()
        await application.bot.set_webhook(url=f"{BASE_URL}/{WEBHOOK_SECRET_PATH}")
        flask_app.run(host="0.0.0.0", port=PORT)

    asyncio.run(run())
