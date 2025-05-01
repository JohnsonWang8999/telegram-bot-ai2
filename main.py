import os
import re
import json
import datetime
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# === 基础配置 ===
TOKEN = "7138174010:AAFAkeXS1marlcputUOQ9aNUPYBoHrtU44s"
WEBHOOK_SECRET_PATH = "myhook"
PORT = int(os.environ.get("PORT", 10000))
BASE_URL = f"https://telegram-bot-ai2.onrender.com"

# === 数据存储路径 ===
DATA_FILE = "records.json"

# === 初始化 Flask 和 Telegram 应用 ===
flask_app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()

# === 初始化变量 ===
user_states = {}
current_month = datetime.datetime.now().strftime("%Y-%m")
units = [
    "Danga Bay 16A-01-02",
    "Danga Bay 7A-18-03A",
    "Danga Bay 17C-19-02",
    "RNF 6A-13A-09",
    "RNF B1-1 23-06",
]

# === 工具函数 ===
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# === /start 指令 ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📂 查看账单", callback_data="view_records")],
        [InlineKeyboardButton("📝 记录消费", callback_data="add_expense")],
        [InlineKeyboardButton("📅 切换月份", callback_data="switch_month")],
    ]
    await update.message.reply_text(
        "欢迎使用 Short Escape Telegram Bot!

请选择操作：",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

# === 处理按钮点击 ===
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "add_expense":
        keyboard = [[InlineKeyboardButton(unit, callback_data=f"unit_{i}")] for i, unit in enumerate(units)]
        await query.edit_message_text("请选择消费的房源单位：", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("unit_"):
        index = int(data.split("_")[1])
        unit = units[index]
        user_states[query.from_user.id] = {"mode": "record", "unit": unit}
        await query.edit_message_text("请发送消费内容，例如：换灯泡 29.9")
    elif data == "view_records":
        await show_summary(update, context)
    elif data == "switch_month":
        keyboard = []
        now = datetime.datetime.now()
        for i in range(0, 6):
            month = (now - datetime.timedelta(days=30 * i)).strftime("%Y-%m")
            keyboard.append([InlineKeyboardButton(month, callback_data=f"month_{month}")])
        await query.edit_message_text("请选择要查看的月份：", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("month_"):
        global current_month
        current_month = data.split("_")[1]
        await query.edit_message_text(f"✅ 已切换至 {current_month}")

# === 处理输入文本 ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_states or user_states[user_id].get("mode") != "record":
        return

    content = update.message.text
    match = re.search(r"([\d.]+)$", content)
    if not match:
        await update.message.reply_text("⚠️ 格式错误，请以：内容 金额，例如：换灯泡 29.9")
        return

    amount = match.group(1)
    description = content.replace(amount, "").strip()
    unit = user_states[user_id]["unit"]

    key = (unit, current_month)
    data = load_data()
    data.setdefault(key[0], {})
    data[key[0]].setdefault(key[1], [])
    data[key[0]][key[1]].append(f"{description} RM{amount}")
    save_data(data)

    user_states.pop(user_id)
    await update.message.reply_text("✅ 记录成功！")

# === 查看账单汇总 ===
async def show_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    text = f"📅 {current_month} 消费记录汇总：\n"
    total_all = 0
    for unit in units:
        if current_month not in data.get(unit, {}):
            continue
        text += f"\n🏘️ {unit}：\n"
        unit_total = 0
        for record in data[unit][current_month]:
            text += f" - {record}\n"
            try:
                unit_total += float(record.split("RM")[-1])
            except:
                pass
        total_all += unit_total
        text += f"总支出：RM{unit_total:.2f}\n"
    text += f"\n💰 全部单位总支出：RM{total_all:.2f}"
    await update.callback_query.edit_message_text(text)

# === 路由绑定 ===
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(handle_button))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@flask_app.route(f"/{WEBHOOK_SECRET_PATH}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.create_task(application.process_update(update))
    return "ok"

# === 启动 Webhook ===
if __name__ == "__main__":
    import asyncio
    async def run():
        print(f"==> Setting webhook to {BASE_URL}/{WEBHOOK_SECRET_PATH}")
        await application.bot.set_webhook(url=f"{BASE_URL}/{WEBHOOK_SECRET_PATH}")
        flask_app.run(host="0.0.0.0", port=PORT)
    asyncio.run(run())
