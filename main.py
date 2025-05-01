import os
import asyncio
from flask import Flask, request
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler,
    ContextTypes, filters
)
from datetime import datetime
from collections import defaultdict

# === 基础设置 ===
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH", "myhook")
PORT = int(os.getenv("PORT", 10000))
BASE_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}"

flask_app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()

# === 数据结构 ===
records = defaultdict(lambda: defaultdict(list))  # (unit, month) => [records]
current_month = datetime.now().strftime("%Y-%m")
user_state = {}  # user_id => {"action": ..., "unit": ...}

UNITS = [
    "Danga Bay 16A-01-02",
    "Danga Bay 7A-18-03A",
    "Danga Bay 17C-19-02",
    "RNF 6A-13A-09",
    "RNF B1-1 23-06"
]

# === /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📂 查看账单", callback_data="view_records")],
        [InlineKeyboardButton("✏️ 记录消费", callback_data="add_expense")],
        [InlineKeyboardButton("📅 切换月份", callback_data="switch_month")]
    ]
    await update.message.reply_text(
        "欢迎使用 Short Escape Telegram Bot!\n\n请选择操作：",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

application.add_handler(CommandHandler("start", start))

# === 按钮处理 ===
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    user_id = query.from_user.id

    if action in ["view_records", "add_expense"]:
        user_state[user_id] = {"action": action}
        buttons = [[InlineKeyboardButton(unit, callback_data=f"unit_{unit}")]
                   for unit in UNITS]
        await query.edit_message_text(
            "请选择单位：", reply_markup=InlineKeyboardMarkup(buttons)
        )
    elif action == "switch_month":
        await query.edit_message_text("请输入新的月份，例如：2025-06")

    elif action.startswith("unit_"):
        unit = action[5:]
        state = user_state.get(user_id, {})
        if state.get("action") == "add_expense":
            state["unit"] = unit
            await query.edit_message_text("请发送消费内容，例如：换灯泡 RM100")
        elif state.get("action") == "view_records":
            month = current_month
            key = (unit, month)
            unit_records = records.get(key, [])
            if unit_records:
                total = 0
                text = f"📄 {unit} - {month} 消费记录：\n"
                for record in unit_records:
                    text += f"- {record}\n"
                    try:
                        amount = float(record.split("RM")[-1])
                        total += amount
                    except:
                        pass
                text += f"\n💰 总消费：RM{total:.2f}"
            else:
                text = f"{unit} 暂无记录"
            await query.edit_message_text(text)

application.add_handler(CallbackQueryHandler(handle_button))

# === 消息处理 ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message.text
    global current_month

    # 切换月份
    if message.strip().startswith("20"):
        current_month = message.strip()
        await update.message.reply_text(f"✅ 已切换月份为：{current_month}")
        return

    state = user_state.get(user_id, {})
    if state.get("action") == "add_expense" and "unit" in state:
        unit = state["unit"]
        amount = 0
        try:
            if "RM" in message.upper():
                amount = float(message.upper().split("RM")[-1])
            else:
                # 尝试提取最后一个数字作为金额
                amount = float(message.strip().split()[-1])
        except:
            await update.message.reply_text("❌ 消费金额识别失败，请重新输入")
            return

        final_message = message if "RM" in message.upper() else f"{message} RM{amount:.2f}"
        records[(unit, current_month)].append(final_message)
        await update.message.reply_text("✅ 消费记录成功！")
        user_state.pop(user_id, None)

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# === Webhook 入口 ===
@flask_app.route(f"/{WEBHOOK_SECRET_PATH}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run(application.process_update(update))
    return "ok"

# === 启动入口 ===
if __name__ == "__main__":
    async def run():
        print(f"==> Setting webhook to {BASE_URL}/{WEBHOOK_SECRET_PATH}")
        await application.bot.set_webhook(url=f"{BASE_URL}/{WEBHOOK_SECRET_PATH}")
        flask_app.run(host="0.0.0.0", port=PORT)

    asyncio.run(run())
