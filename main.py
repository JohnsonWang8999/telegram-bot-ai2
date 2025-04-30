import os
import asyncio
from flask import Flask, request
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from datetime import datetime

# === 设置 ===
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH", "myhook")
PORT = int(os.environ.get("PORT", 10000))
BASE_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}"

flask_app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()

# === 状态缓存 ===
user_states = {}
user_records = {}
available_units = [
    "Danga Bay 16A-01-02",
    "Danga Bay 7A-18-03A",
    "Danga Bay 17C-19-02",
    "RNF 6A-13A-09",
    "RNF B1-1 23-06",
    "testing"
]

# === 当前月份 ===
current_month = datetime.now().strftime("%Y-%m")

# === 指令 /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📂 查看账单", callback_data="view_records")],
        [InlineKeyboardButton("📝 记录消费", callback_data="add_expense")],
        [InlineKeyboardButton("📅 切换月份", callback_data="switch_month")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "欢迎使用 Short Escape Telegram Bot!请选择操作：",reply_markup=reply_markup
    )

application.add_handler(CommandHandler("start", start))

# === 处理按钮 ===
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    action = query.data

    if action == "view_records":
        summary = {}
        for key, records in user_records.items():
            if key.startswith(current_month):
                _, unit = key.split("::")
                if unit not in summary:
                    summary[unit] = []
                summary[unit].extend(records)

        if not summary:
            await query.edit_message_text("📂 当前月份尚无记录。")
            return

        text = f"📅 {current_month} 消费记录汇总："
        total_all = 0
        for unit, records in summary.items():
            text += f"🏘️ {unit}："
            unit_total = 0
            for record in records:
                text += f" - {record}\n"
                amount = float(record.split("RM")[-1])
                unit_total += amount
            text += f" ➕ 小计：RM{unit_total:.2f}\n"
            total_all += unit_total
        text = f"📅 {current_month} 消费记录汇总：\n\n"
total_all = 0

for unit, records in summary.items():
    text += f"🏘️ {unit}：\n"
    unit_total = 0
    for record in records:
        text += f" - {record}\n"
        try:
            amount = float(record.split("RM")[-1])
            unit_total += amount
        except:
            pass
    text += f"💰 总计：RM{unit_total}\n\n"
    total_all += unit_total

text += f"🧾 所有单位总消费：RM{total_all}"

await query.edit_message_text(text)
    elif action == "add_expense":
        keyboard = [[InlineKeyboardButton(unit, callback_data=f"unit::{unit}")]
                    for unit in available_units]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("请选择消费单位：", reply_markup=reply_markup)
    elif action == "switch_month":
        await query.edit_message_text("📅 功能开发中，当前仅支持当前月份。")

# === 选择房源单位 ===
async def handle_unit_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    unit_name = query.data.split("::")[1]
    user_states[query.from_user.id] = {"state": "awaiting_expense", "unit": unit_name}
    await query.edit_message_text(f"请输入消费内容，例如：换灯泡 RM100")

# === 消费输入 ===
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_states or user_states[user_id]["state"] != "awaiting_expense":
        return

    unit = user_states[user_id]["unit"]
    record = update.message.text
    key = f"{current_month}::{unit}"
    user_records.setdefault(key, []).append(record)
    del user_states[user_id]
    await update.message.reply_text("✅ 记录成功！")

# === 添加处理器 ===
application.add_handler(CallbackQueryHandler(handle_unit_select, pattern="^unit::"))
application.add_handler(CallbackQueryHandler(handle_button))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

# === Webhook ===
@flask_app.route(f"/{WEBHOOK_SECRET_PATH}", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    if not application.running:
        await application.initialize()
    await application.process_update(update)
    return "ok"

# === 启动入口 ===
if __name__ == "__main__":
    async def run():
        print(f"==> Setting webhook to {BASE_URL}/{WEBHOOK_SECRET_PATH}")
        await application.bot.set_webhook(url=f"{BASE_URL}/{WEBHOOK_SECRET_PATH}")
        flask_app.run(host="0.0.0.0", port=PORT)

    asyncio.run(run())
