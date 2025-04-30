import os
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH", "webhook")
PORT = int(os.environ.get("PORT", 10000))
BASE_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}"

application = ApplicationBuilder().token(TOKEN).build()

# 处理 /start 指令
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("欢迎使用 Airbnb 每月消费记录 Ai Bot！")

application.add_handler(CommandHandler("start", start))

# Flask 应用
flask_app = Flask(__name__)

@flask_app.route(f"/{WEBHOOK_SECRET_PATH}", methods=["POST"])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), application.bot)
        application.update_queue.put_nowait(update)
    return "ok"

if __name__ == "__main__":
    # 设置 Telegram Webhook
    import telegram
    bot = telegram.Bot(TOKEN)
    bot.set_webhook(url=f"{BASE_URL}/{WEBHOOK_SECRET_PATH}")
    
    # 启动 Flask
    flask_app.run(host="0.0.0.0", port=PORT)
