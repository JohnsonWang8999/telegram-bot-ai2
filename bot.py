import os
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

TOKEN = os.getenv("TOKEN")
WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH")

app = Flask(__name__)

application = ApplicationBuilder().token(TOKEN).build()

@app.route(f"/{WEBHOOK_SECRET_PATH}", methods=["POST"])
async def webhook() -> str:
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "OK"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📘 Hello! Bot is working.")

application.add_handler(CommandHandler("start", start))

if __name__ == "__main__":
    application.run_webhook(
        listen="0.0.0.0",
        port=10000,
        webhook_url=f"https://your-domain.com/{WEBHOOK_SECRET_PATH}"
    )
