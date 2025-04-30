import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# 环境变量读取
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH", "myhook")

# 创建 bot 应用
application = ApplicationBuilder().token(TOKEN).build()

# /start 命令
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Hello! Bot is running via webhook.")

# 添加指令处理器
application.add_handler(CommandHandler("start", start))

# 创建 Flask app
flask_app = Flask(__name__)

@flask_app.route(f"/{WEBHOOK_SECRET_PATH}", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, application.bot)
        asyncio.create_task(application.process_update(update))  # ✅关键步骤
    except Exception as e:
        print(f"❌ Webhook error: {e}")
    return "ok"

# 初始化 telegram bot（✅必须执行一次）
asyncio.run(application.initialize())

