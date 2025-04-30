import os
import asyncio
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# === 环境变量设置 ===
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH", "webhook")
PORT = int(os.environ.get("PORT", 10000))
BASE_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}"

# === Flask + Telegram ===
flask_app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()

# === /start 按钮菜单 ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["📋 查看账单", "📝 记录消费"],
        ["📅 切换月份"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "欢迎使用 Short Escape Telegram Bot!\n\n请选择操作：",
        reply_markup=reply_markup
    )

# === 按钮选择处理 ===
async def handle_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "📋 查看账单":
        await update.message.reply_text("👉 功能开发中：将显示每月账单")
    elif text == "📝 记录消费":
        await update.message.reply_text("请输入消费内容，例如：电费 RM100")
    elif text == "📅 切换月份":
        await update.message.reply_text("👉 功能开发中：将显示月份选择菜单")
    else:
        await update.message.reply_text("❗️请点击上方菜单按钮操作。")

# === 注册 Handler ===
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_selection))

# === Webhook 路由 ===
@flask_app.route(f"/{WEBHOOK_SECRET_PATH}", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    if not application.running:
        await application.initialize()
    await application.process_update(update)
    return "ok"

# === 启动程序 ===
if __name__ == "__main__":
    async def run():
        print(f"==> Setting webhook to {BASE_URL}/{WEBHOOK_SECRET_PATH}")
        await application.bot.set_webhook(url=f"{BASE_URL}/{WEBHOOK_SECRET_PATH}")
        flask_app.run(host="0.0.0.0", port=PORT)

    asyncio.run(run())
