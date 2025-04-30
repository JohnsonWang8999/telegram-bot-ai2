import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH", "webhook")

application = ApplicationBuilder().token(TOKEN).build()

# 定义指令
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Hello! Your bot is working via webhook!")

application.add_handler(CommandHandler("start", start))

# 初始化 Flask 应用
flask_app = Flask(__name__)

@flask_app.route(f"/{WEBHOOK_SECRET_PATH}", methods=["POST"])
async def webhook():
    if request.method == "POST":
        data = request.get_json(force=True)
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
    return "ok"

# 启动入口
if __name__ == "__main__":
    # 必须初始化应用
    async def main():
        await application.initialize()
        await application.start()
        await application.updater.start_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", 10000)),
            webhook_url=f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{WEBHOOK_SECRET_PATH}"
        )

    asyncio.run(main())
