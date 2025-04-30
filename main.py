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
    ContextTypes,
)

# === 环境设置 ===
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH", "webhook")
PORT = int(os.environ.get("PORT", 10000))
BASE_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}"

# === Flask + Telegram ===
flask_app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()

# === /start 指令处理 ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("\U0001F4C2 查看账单", callback_data="view_records")],
        [InlineKeyboardButton("\U0001F4DD 记录消费", callback_data="add_expense")],
        [InlineKeyboardButton("\U0001F4C5 切换月份", callback_data="switch_month")],
        [InlineKeyboardButton("\U0001F4CA 总消费", callback_data="total")],
        [InlineKeyboardButton("\u274C 删除记录", callback_data="delete")],
        [InlineKeyboardButton("\U0001F4E5 下载Excel", callback_data="download")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "欢迎使用 Short Escape Telegram Bot!\n\n请选择操作：",
        reply_markup=reply_markup
    )

application.add_handler(CommandHandler("start", start))

# === 处理按钮点击 ===
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "view_records":
        await query.edit_message_text("\U0001F4C2 功能开发中：将显示当月账单")
    elif data == "add_expense":
        await query.edit_message_text("\U0001F4DD 请输入消费内容，例如：电费 RM100")
    elif data == "switch_month":
        await query.edit_message_text("\U0001F4C5 功能开发中：将允许选择月份")
    elif data == "total":
        await query.edit_message_text("\U0001F4CA 功能开发中：查看总消费")
    elif data == "delete":
        await query.edit_message_text("\u274C 功能开发中：删除记录")
    elif data == "download":
        await query.edit_message_text("\U0001F4E5 功能开发中：下载 Excel")

application.add_handler(CallbackQueryHandler(handle_button))

# === Webhook 入口 ===
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
