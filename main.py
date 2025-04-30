
import os
import json
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

# 环境变量设置
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH", "myhook")
PORT = int(os.environ.get("PORT", 10000))
BASE_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}"

# 初始化 Flask 和 Telegram
flask_app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()

# 房源单位表
UNITS = {
    "1": "Danga Bay 16A-01-02",
    "2": "Danga Bay 7A-18-03A",
    "3": "Danga Bay 17C-19-02",
    "4": "RNF 6A-13A-09",
    "5": "RNF B1-1 23-06",
    "6": "testing（测试专用）"
}

# 指令 /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📂 查看账单", callback_data="view_records")],
        [InlineKeyboardButton("📝 记录消费", callback_data="add_expense")],
        [InlineKeyboardButton("📅 切换月份", callback_data="switch_month")],
        [InlineKeyboardButton("📊 总消费", callback_data="total")],
        [InlineKeyboardButton("❌ 删除记录", callback_data="delete")],
        [InlineKeyboardButton("📥 下载Excel", callback_data="download")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("欢迎使用 Short Escape Telegram Bot！")

请选择操作：", reply_markup=reply_markup)

application.add_handler(CommandHandler("start", start))

# 按钮处理
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    msg = {
        "view_records": "📂 功能开发中：将显示当月账单",
        "add_expense": "📝 请输入消费内容，例如：电费 RM100",
        "switch_month": "📅 功能开发中：将允许选择月份",
        "total": "📊 功能开发中：查看总消费",
        "delete": "❌ 功能开发中：删除记录",
        "download": "📥 功能开发中：下载 Excel"
    }.get(data, "暂未识别的指令")
    await query.edit_message_text(msg)

application.add_handler(CallbackQueryHandler(handle_button))

# Webhook（同步）
@flask_app.route(f"/{WEBHOOK_SECRET_PATH}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    if not application.running:
        asyncio.run(application.initialize())
    asyncio.run(application.process_update(update))
    return "ok"

# 启动入口
if __name__ == "__main__":
    async def run():
        print(f"==> Setting webhook to {BASE_URL}/{WEBHOOK_SECRET_PATH}")
        await application.bot.set_webhook(url=f"{BASE_URL}/{WEBHOOK_SECRET_PATH}")
        flask_app.run(host="0.0.0.0", port=PORT)
    asyncio.run(run())
