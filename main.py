
import os
import asyncio
from flask import Flask, request
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# === 环境设置 ===
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH", "webhook")
PORT = int(os.environ.get("PORT", 10000))
BASE_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}"

# === 房源单位列表 ===
UNITS = [
    ("1", "Danga Bay 16A-01-02"),
    ("2", "Danga Bay 7A-18-03A"),
    ("3", "Danga Bay 17C-19-02"),
    ("4", "RNF 6A-13A-09"),
    ("5", "RNF B1-1 23-06"),
    ("6", "testing（测试专用）"),
]

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
        "欢迎使用 Short Escape Telegram Bot!\n\n请选择操作:",
        reply_markup=reply_markup
    )

application.add_handler(CommandHandler("start", start))

# === 按钮点击处理 ===
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "add_expense":
        context.user_data["expecting_expense"] = True
        await query.edit_message_text("\U0001F4DD 请输入消费内容，例如：电费 RM100")
    else:
        await query.edit_message_text(f"\u26A0\ufe0f 功能 [{data}] 暂未完成")

application.add_handler(CallbackQueryHandler(handle_button))

# === 用户输入处理 ===
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("expecting_expense"):
        context.user_data["last_expense_text"] = update.message.text
        context.user_data["expecting_expense"] = False

        keyboard = [[
            InlineKeyboardButton(name, callback_data=f"save_{uid}")
        ] for uid, name in UNITS]

        await update.message.reply_text(
            "请选择记录消费的单位：",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

# === Webhook 入口（同步） ===
@flask_app.route(f"/{WEBHOOK_SECRET_PATH}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    if not application.running:
        asyncio.run(application.initialize())
    asyncio.run(application.process_update(update))
    return "ok"

# === 启动入口 ===
if __name__ == "__main__":
    async def run():
        print(f"==> Setting webhook to {BASE_URL}/{WEBHOOK_SECRET_PATH}")
        await application.bot.set_webhook(url=f"{BASE_URL}/{WEBHOOK_SECRET_PATH}")
        flask_app.run(host="0.0.0.0", port=PORT)

    asyncio.run(run())
