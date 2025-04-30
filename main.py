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

# === 房源列表 ===
UNITS = {
    "1": "Danga Bay 16A-01-02",
    "2": "Danga Bay 7A-18-03A",
    "3": "Danga Bay 17C-19-02",
    "4": "RNF 6A-13A-09",
    "5": "RNF B1-1 23-06",
    "6": "testing（测试专用）"
}

# === 消费记录数据库 ===
records = {}
current_month = "2025-04"

# === Flask + Telegram ===
flask_app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()

# === /start 指令 ===
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
    await update.message.reply_text(
        "欢迎使用 Short Escape Telegram Bot!\n\n请选择操作：",
        reply_markup=reply_markup
    )

application.add_handler(CommandHandler("start", start))

# === 按钮交互逻辑 ===
user_action = {}

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_month
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    action = query.data
    user_action[user_id] = action

    if action == "add_expense":
        # 选择房源
        keyboard = [[InlineKeyboardButton(name, callback_data=f"unit_{id_}")] for id_, name in UNITS.items()]
        await query.edit_message_text("请选择消费所属房源：", reply_markup=InlineKeyboardMarkup(keyboard))
    elif action == "view_records":
        summary = {}
        for (uid, month), logs in records.items():
            if month != current_month:
                continue
            summary.setdefault(uid, []).extend(logs)

        text = f"📅 {current_month} 消费记录汇总：\n\n"
        total_all = 0
        for unit, logs in summary.items():
            text += f"🏘️ {UNITS[unit]}：\n"
            unit_total = 0
            for record in logs:
                text += f" - {record}\n"
                try:
                    amount = float(record.split("RM")[-1])
                    unit_total += amount
                except:
                    pass
            text += f"💰 小计：RM{unit_total}\n\n"
            total_all += unit_total

        text += f"🧾 总消费：RM{total_all}"
        await query.edit_message_text(text)

    elif action == "switch_month":
        await query.edit_message_text("请输入月份，例如：2025-05")
    elif action == "total":
        await query.edit_message_text("功能开发中：查看总消费")
    elif action == "delete":
        await query.edit_message_text("功能开发中：删除记录")
    elif action == "download":
        await query.edit_message_text("功能开发中：下载 Excel")
    elif action.startswith("unit_"):
        unit_id = action.split("_")[1]
        user_action[user_id] = f"record_unit_{unit_id}"
        await query.edit_message_text(f"请发送消费内容，例如：换灯泡 RM100")

application.add_handler(CallbackQueryHandler(handle_button))

# === 文本输入处理 ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in user_action:
        await update.message.reply_text("请先点击 /start 开始操作")
        return

    action = user_action[user_id]

    if action.startswith("record_unit_"):
        unit_id = action.split("_")[-1]
        key = (unit_id, current_month)
        records.setdefault(key, []).append(text)
        del user_action[user_id]
        await update.message.reply_text(f"✅ 消费已记录在 {UNITS[unit_id]}：{text}")
    elif user_action[user_id] == "switch_month":
        current_month = text
        del user_action[user_id]
        await update.message.reply_text(f"✅ 已切换至月份：{current_month}")
    else:
        await update.message.reply_text("⚠️ 无效输入，请从按钮选择操作")

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(handle_button))
application.add_handler(CommandHandler("switch", handle_button))
application.add_handler(CommandHandler("record", handle_button))
application.add_handler(CommandHandler("view", handle_button))
application.add_handler(CommandHandler("total", handle_button))
application.add_handler(CommandHandler("delete", handle_button))
application.add_handler(CommandHandler("download", handle_button))
application.add_handler(CommandHandler("unit", handle_button))
application.add_handler(CommandHandler("unit_", handle_button))
application.add_handler(CommandHandler("help", start))
application.add_handler(CommandHandler("reset", start))
application.add_handler(CommandHandler("back", start))
application.add_handler(CommandHandler("return", start))
application.add_handler(CommandHandler("home", start))

from telegram.ext import MessageHandler, filters
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# === Webhook 路由 ===
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
