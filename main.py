import os
import re
import json
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from datetime import datetime

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH", "myhook")
PORT = int(os.environ.get("PORT", 10000))
BASE_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}"

flask_app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()

DATA_FOLDER = "data"
os.makedirs(DATA_FOLDER, exist_ok=True)

units = [
    "Danga Bay 16A-01-02",
    "Danga Bay 7A-18-03A",
    "Danga Bay 17C-19-02",
    "RNF 6A-13A-09",
    "RNF B1-1 23-06",
    "testing"
]

user_states = {}
current_month = "2025-05"

def get_data_file():
    return os.path.join(DATA_FOLDER, f"records_{current_month}.json")

def load_data():
    try:
        with open(get_data_file(), "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(get_data_file(), "w") as f:
        json.dump(data, f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📂 查看账单", callback_data="view_records")],
        [InlineKeyboardButton("📝 记录消费", callback_data="add_expense")],
        [InlineKeyboardButton("📅 切换月份", callback_data="switch_month")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("欢迎使用 Short Escape Telegram Bot!\n\n请选择操作：", reply_markup=reply_markup)

application.add_handler(CommandHandler("start", start))

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data

    if data == "view_records":
        records = load_data()
        summary = {}
        for (unit, month), record_list in records.items():
            if month == current_month:
                if unit not in summary:
                    summary[unit] = []
                summary[unit].extend(record_list)

        text = f"📅 {current_month} 消费记录汇总：\n"
        total_all = 0
        for unit, records in summary.items():
            text += f"\n🏘️ {unit}："
            unit_total = 0
            for record in records:
                text += f"\n - {record}"
                match = re.search(r"RM(\d+(\.\d+)?)", record)
                if match:
                    unit_total += float(match.group(1))
            total_all += unit_total
            text += f"\n 总支出： RM{unit_total:.2f}\n"

        text += f"\n📊 所有单位总支出：RM{total_all:.2f}"
        await query.edit_message_text(text)
    elif data == "add_expense":
        keyboard = [[InlineKeyboardButton(unit, callback_data=f"unit_{unit}")] for unit in units]
        await query.edit_message_text("请选择房源单位：", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("unit_"):
        unit_name = data.replace("unit_", "")
        user_states[user_id] = {"action": "adding", "unit": unit_name}
        await query.edit_message_text("请发送消费内容，例如：换灯泡 RM100")
    elif data == "switch_month":
        await query.edit_message_text("请输入新月份（格式：2025-05）：")
        user_states[user_id] = {"action": "switch_month"}

application.add_handler(CallbackQueryHandler(handle_buttons))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_month
    user_id = str(update.effective_user.id)
    message = update.message.text
    state = user_states.get(user_id)

    if state:
        if state["action"] == "adding":
            unit = state["unit"]
            amount_match = re.search(r"(\d+(\.\d+)?)", message)
            if not amount_match:
                await update.message.reply_text("⚠️ 未找到金额，请确保格式正确，例如：换灯泡 100")
                return

            amount = amount_match.group(1)
            record = f"{message if 'RM' in message else message + ' RM' + amount}"
            data = load_data()
            key = (unit, current_month)
            if key not in data:
                data[key] = []
            data[key].append(record)
            save_data(data)
            await update.message.reply_text("✅ 记录成功！")
            del user_states[user_id]
        elif state["action"] == "switch_month":
            current_month = message.strip()
            await update.message.reply_text(f"✅ 已切换至月份：{current_month}")
            del user_states[user_id]

application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

@flask_app.route(f"/{WEBHOOK_SECRET_PATH}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "ok"

if __name__ == "__main__":
    import asyncio
    async def run():
        await application.bot.set_webhook(url=f"{BASE_URL}/{WEBHOOK_SECRET_PATH}")
        flask_app.run(host="0.0.0.0", port=PORT)

    asyncio.run(run())
