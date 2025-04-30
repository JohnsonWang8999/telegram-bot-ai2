import os
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)
import asyncio

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH", "webhook")
PORT = int(os.environ.get("PORT", 10000))
BASE_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}"

flask_app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()

# 处理 /start 指令
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("欢迎使用 Short Escape Telegram Bot!")

application.add_handler(CommandHandler("start", start))

@flask_app.route(f"/{WEBHOOK_SECRET_PATH}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.create_task(application.process_update(update))
    return "ok"


# webhook 只接收 POST
@flask_app.route(f"/{WEBHOOK_SECRET_PATH}", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "ok"

# 启动入口
if __name__ == "__main__":
    async def run():
        print(f"==> Setting webhook to {BASE_URL}/{WEBHOOK_SECRET_PATH}")
        await application.bot.set_webhook(url=f"{BASE_URL}/{WEBHOOK_SECRET_PATH}")
        flask_app.run(host="0.0.0.0", port=PORT)
    asyncio.run(run())
