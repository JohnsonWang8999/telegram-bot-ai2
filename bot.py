import os
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# 从环境变量获取 Bot Token 与 Webhook 路径
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH", "webhook")

# 创建 Flask 应用
flask_app = Flask(__name__)

# 初始化 Telegram Bot 应用
application = ApplicationBuilder().token(TOKEN).build()

# 注册指令处理器
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Hello! Bot is running via webhook.")

application.add_handler(CommandHandler("start", start))

# 初始化一次（很关键，不然 application.bot 是空的）
import asyncio
asyncio.run(application.initialize())

# 设置 webhook 路由
@flask_app.route(f"/{WEBHOOK_SECRET_PATH}", methods=["POST"])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), application.bot)
        asyncio.create_task(application.process_update(update))
    return "ok"
