
import os
import json
import datetime
from flask import Flask, request
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters, ContextTypes
)

# === 环境变量与初始化 ===
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH", "myhook")
PORT = int(os.environ.get("PORT", 10000))
BASE_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}"

flask_app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()

DATA_FILE = "expenses.json"
UNITS = [
    "Danga Bay 16A-01-02",
    "Danga Bay 7A-18-03A",
    "Danga Bay 17C-19-02",
    "RNF 6A-13A-09",
    "RNF B1-1 23-06"
]
user_state = {}

# === 辅助函数 ===
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def current_month():
    return datetime.datetime.now().strftime("%Y-%m")

# === /start 菜单 ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📂 查看账单", callback_data="view_records")],
        [InlineKeyboardButton("📝 记录消费", callback_data="add_expense")],
        [InlineKeyboardButton("📅 切换月份", callback_data="switch_month")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("欢迎使用 Short Escape Telegram Bot!

请选择操作：", reply_markup=reply_markup)

application.add_handler(CommandHandler("start", start))

# === 按钮处理 ===
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    user_id = str(query.from_user.id)

    if action == "view_records":
        data = load_data()
        summary = {}
        for key, records in data.items():
            unit, month = key.split("|")
            if month != current_month():
                continue
            if unit not in summary:
                summary[unit] = []
            summary[unit].extend(records)

        if not summary:
            await query.edit_message_text("暂无记录。")
            return

        text = f"📅 {current_month()} 消费记录汇总：
"
        total_all = 0
        for unit, records in summary.items():
            text += f"
🏘️ {unit}：
"
            unit_total = 0
            for record in records:
                text += f" - {record}
"
                try:
                    amount = float(record.split("RM")[-1])
                    unit_total += amount
                except:
                    pass
            total_all += unit_total
            text += f"✅ 小计：RM{unit_total:.2f}
"
        text += f"
📊 总消费：RM{total_all:.2f}"
        await query.edit_message_text(text)

    elif action == "add_expense":
        keyboard = [[InlineKeyboardButton(unit, callback_data=f"unit_{i}")] for i, unit in enumerate(UNITS)]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("请选择房源单位：", reply_markup=reply_markup)

    elif action.startswith("unit_"):
        index = int(action.split("_")[1])
        user_state[user_id] = {"unit": UNITS[index], "step": "waiting_expense"}
        await query.edit_message_text(f"请发送消费内容，例如：换灯泡 RM100")

application.add_handler(CallbackQueryHandler(handle_button))

# === 消息处理 ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in user_state or user_state[user_id].get("step") != "waiting_expense":
        return
    unit = user_state[user_id]["unit"]
    text = update.message.text.strip()
    month = current_month()
    key = f"{unit}|{month}"

    data = load_data()
    if key not in data:
        data[key] = []
    data[key].append(text)
    save_data(data)

    user_state[user_id] = {}
    await update.message.reply_text("✅ 消费记录成功！")

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# === Webhook入口 ===
@flask_app.route(f"/{WEBHOOK_SECRET_PATH}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "ok"

# === 启动 ===
if __name__ == "__main__":
    import asyncio
    async def run():
        print(f"==> Setting webhook to {BASE_URL}/{WEBHOOK_SECRET_PATH}")
        await application.bot.set_webhook(url=f"{BASE_URL}/{WEBHOOK_SECRET_PATH}")
        flask_app.run(host="0.0.0.0", port=PORT)
    asyncio.run(run())
