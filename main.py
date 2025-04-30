# 以下是修复过 global 声明顺序错误的完整 main.py 程序

main_py_content = """
import os
import json
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from datetime import datetime

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH", "myhook")
PORT = int(os.environ.get("PORT", 10000))
BASE_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}"

flask_app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()

EXPENSE_FILE = "expenses.json"
UNITS = [
    "Danga Bay 16A-01-02", "Danga Bay 7A-18-03A", "Danga Bay 17C-19-02",
    "RNF 6A-13A-09", "RNF B1-1 23-06", "testing"
]
months = [datetime.now().strftime("%Y-%m"), "2025-05", "2025-06"]
current_month = datetime.now().strftime("%Y-%m")
user_states = {}

def load_expenses():
    if not os.path.exists(EXPENSE_FILE):
        return {}
    with open(EXPENSE_FILE, "r") as f:
        return json.load(f)

def save_expenses(data):
    with open(EXPENSE_FILE, "w") as f:
        json.dump(data, f, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📂 查看账单", callback_data="view_records")],
        [InlineKeyboardButton("📝 记录消费", callback_data="add_expense")],
        [InlineKeyboardButton("📅 切换月份", callback_data="switch_month")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("欢迎使用 Short Escape Telegram Bot!\\n\\n请选择操作：", reply_markup=reply_markup)

application.add_handler(CommandHandler("start", start))

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_month
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "add_expense":
        unit_keyboard = [
            [InlineKeyboardButton(unit, callback_data=f"unit_{unit}")] for unit in UNITS
        ]
        user_states[user_id] = {"state": "awaiting_unit"}
        await query.edit_message_text("请选择房源单位：", reply_markup=InlineKeyboardMarkup(unit_keyboard))

    elif data.startswith("unit_"):
        selected_unit = data.replace("unit_", "")
        user_states[user_id] = {"state": "awaiting_expense", "unit": selected_unit}
        await query.edit_message_text("请输入消费内容，例如：换灯泡 RM100")

    elif data == "view_records":
        expenses = load_expenses()
        monthly_data = expenses.get(current_month, {})
        total_all = 0
        result = [f"📅 当前月份：{current_month}"]
        for unit, items in monthly_data.items():
            result.append(f"🏠 {unit}")
            subtotal = 0
            for record in items:
                result.append(f"- {record}")
                try:
                    subtotal += float(record.split("RM")[-1])
                except:
                    pass
            result.append(f"  总额：RM{subtotal:.2f}\\n")
            total_all += subtotal
        result.append(f"💰 所有单位总额：RM{total_all:.2f}")
        await query.edit_message_text("\\n".join(result))

    elif data == "switch_month":
        month_keyboard = [
            [InlineKeyboardButton(m, callback_data=f"month_{m}")] for m in months
        ]
        await query.edit_message_text("请选择月份：", reply_markup=InlineKeyboardMarkup(month_keyboard))

    elif data.startswith("month_"):
        current_month = data.replace("month_", "")
        await query.edit_message_text(f"✅ 已切换至 {current_month}")

application.add_handler(CallbackQueryHandler(handle_buttons))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_states:
        state = user_states[user_id]
        if state["state"] == "awaiting_expense":
            expenses = load_expenses()
            unit = state["unit"]
            text = update.message.text
            expenses.setdefault(current_month, {}).setdefault(unit, []).append(text)
            save_expenses(expenses)
            await update.message.reply_text("✅ 记录成功！")
            del user_states[user_id]
        else:
            await update.message.reply_text("请先选择房源单位。")
    else:
        await update.message.reply_text("请点击 /start 开始操作")

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

@flask_app.route(f"/{WEBHOOK_SECRET_PATH}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.process_update(update)
    return "ok"

if __name__ == "__main__":
    import asyncio
    async def run():
        print(f"==> Setting webhook to {BASE_URL}/{WEBHOOK_SECRET_PATH}")
        await application.bot.set_webhook(url=f"{BASE_URL}/{WEBHOOK_SECRET_PATH}")
        flask_app.run(host="0.0.0.0", port=PORT)
    asyncio.run(run())
"""

with open("/mnt/data/main.py", "w") as f:
    f.write(main_py_content)

"/mnt/data/main.py"
