import os
import asyncio
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from datetime import datetime
import pandas as pd
from collections import defaultdict

# === 配置 ===
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH", "myhook")
PORT = int(os.environ.get("PORT", 10000))
BASE_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}"

# === 数据结构 ===
expenses = defaultdict(lambda: defaultdict(list))  # expenses[month][unit] = list of expenses
user_states = {}

UNITS = [
    "Danga Bay 16A-01-02",
    "Danga Bay 7A-18-03A",
    "Danga Bay 17C-19-02",
    "RNF 6A-13A-09",
    "RNF B1-1 23-06",
]
current_month = datetime.now().strftime("%Y-%m")

# === Flask + Telegram 应用 ===
flask_app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()

# === 指令 /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📂 查看账单", callback_data="view")],
        [InlineKeyboardButton("📝 记录消费", callback_data="record")],
        [InlineKeyboardButton("📅 切换月份", callback_data="switch_month")]
    ]
    await update.message.reply_text(
        "欢迎使用 Short Escape Telegram Bot!\n\n请选择操作：",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

application.add_handler(CommandHandler("start", start))

# === 按钮处理 ===
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    user_id = query.from_user.id

    if data == "record":
        user_states[user_id] = {"action": "record"}
        buttons = [[InlineKeyboardButton(unit, callback_data=f"unit_{unit}")] for unit in UNITS]
        await query.edit_message_text("请选择房源单位：", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("unit_"):
        unit = data.replace("unit_", "")
        user_states[user_id]["unit"] = unit
        user_states[user_id]["awaiting_expense"] = True
        await query.edit_message_text(f"请输入消费内容，例如：换灯泡 RM100")

    elif data == "view":
        text = f"月份：{current_month}\n\n"
        total_all = 0
        for unit, records in expenses[current_month].items():
            total = sum(float(r.split("RM")[-1]) for r in records)
            total_all += total
            text += f"【{unit}】\n" + "\n".join(records) + f"\n小计：RM{total:.2f}\n\n"
        text += f"总计：RM{total_all:.2f}"
        await query.edit_message_text(text)

    elif data == "switch_month":
        months = pd.date_range("2025-01-01", periods=24, freq='MS').strftime("%Y-%m").tolist()
        buttons = [[InlineKeyboardButton(m, callback_data=f"month_{m}")] for m in months]
        await query.edit_message_text("请选择月份：", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("month_"):
        global current_month
        current_month = data.replace("month_", "")
        await query.edit_message_text(f"已切换至 {current_month}。")

application.add_handler(CallbackQueryHandler(handle_buttons))

# === 消息处理 ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in user_states and user_states[user_id].get("awaiting_expense"):
        unit = user_states[user_id]["unit"]
        expenses[current_month][unit].append(update.message.text)
        await update.message.reply_text("✅ 消费记录成功！")
        user_states[user_id]["awaiting_expense"] = False

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# === Webhook Endpoint ===
@flask_app.route(f"/{WEBHOOK_SECRET_PATH}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.create_task(application.process_update(update))
    return "ok"

# === 设定 Webhook 并启动 Flask ===
async def set_webhook():
    await application.bot.set_webhook(f"{BASE_URL}/{WEBHOOK_SECRET_PATH}")

asyncio.get_event_loop().create_task(set_webhook())

import threading
threading.Thread(target=lambda: flask_app.run(host="0.0.0.0", port=PORT)).start()
