import os
import io
import pandas as pd
import asyncio
from flask import Flask, request
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from datetime import datetime

# 读取环境变量
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH", "webhook")
BASE_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}"
PORT = int(os.getenv("PORT", 10000))

# 单位映射
UNITS = {
    "1": "Danga Bay 16A-01-02",
    "2": "Danga Bay 7A-18-03A",
    "3": "Danga Bay 17C-19-02",
    "4": "RNF 6A-13A-09",
    "5": "RNF B1-1 23-06",
    "6": "testing（测试专用）"
}

# 消费记录结构：{ user_id: [ {date, unit, amount, note} ] }
expenses = {}

flask_app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()

### ✅ Helper
def get_unit_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(name, callback_data=f"select_unit_{id}")]
        for id, name in UNITS.items()
    ])

### ✅ /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "请选择一个单位来记录消费：", reply_markup=get_unit_keyboard()
    )

### ✅ 选择单位后输入金额
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("select_unit_"):
        unit_id = query.data.split("_")[2]
        context.user_data["unit_id"] = unit_id
        await query.edit_message_text(
            f"已选择单位：{UNITS[unit_id]}，请输入消费金额（数字）："
        )

### ✅ 输入金额
async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if not text.replace(".", "", 1).isdigit():
        await update.message.reply_text("请输入正确的金额，例如：123.45")
        return

    amount = float(text)
    unit_id = context.user_data.get("unit_id")
    if not unit_id:
        await update.message.reply_text("请先使用 /start 选择单位")
        return

    context.user_data["amount"] = amount
    await update.message.reply_text("请输入备注（例如：电费、清洁、补货等）：")

### ✅ 输入备注
async def handle_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    note = update.message.text.strip()
    unit_id = context.user_data.get("unit_id")
    amount = context.user_data.get("amount")

    if not unit_id or amount is None:
        await update.message.reply_text("请先输入金额")
        return

    record = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "unit": UNITS[unit_id],
        "amount": amount,
        "note": note
    }

    expenses.setdefault(user_id, []).append(record)

    await update.message.reply_text(
        f"✅ 消费记录成功：\n\n🏘️ 单位：{record['unit']}\n💰 金额：RM {record['amount']:.2f}\n📝 备注：{record['note']}"
    )

    context.user_data.clear()

### ✅ 下载 Excel
async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in expenses or not expenses[user_id]:
        await update.message.reply_text("暂无记录")
        return

    df = pd.DataFrame(expenses[user_id])
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Expenses")

    buffer.seek(0)
    await update.message.reply_document(document=buffer, filename="expenses.xlsx")

### ✅ 查看总金额
async def total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in expenses or not expenses[user_id]:
        await update.message.reply_text("暂无消费记录")
        return

    total_amount = sum(r["amount"] for r in expenses[user_id])
    await update.message.reply_text(f"💸 总消费金额：RM {total_amount:.2f}")

### ✅ 删除所有记录
async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    expenses[user_id] = []
    await update.message.reply_text("✅ 已清空所有记录")

### ✅ 加入 handler
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("download", download))
application.add_handler(CommandHandler("total", total))
application.add_handler(CommandHandler("clear", clear))
application.add_handler(CallbackQueryHandler(handle_callback))
application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_amount))
application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_note))

### ✅ Webhook
@flask_app.route(f"/{WEBHOOK_SECRET_PATH}", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    if not application.running:
        await application.initialize()
    await application.process_update(update)
    return "ok"

### ✅ 启动 bot
if __name__ == "__main__":
    async def run():
        print(f"==> Setting webhook to {BASE_URL}/{WEBHOOK_SECRET_PATH}")
        await application.bot.set_webhook(url=f"{BASE_URL}/{WEBHOOK_SECRET_PATH}")
        flask_app.run(host="0.0.0.0", port=PORT)

    asyncio.run(run())
