
import os
import json
import asyncio
from flask import Flask, request
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from datetime import datetime
import pandas as pd

# === 环境设置 ===
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH", "webhook")
PORT = int(os.environ.get("PORT", 10000))
BASE_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}"

# === Flask + Telegram ===
flask_app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()

# === 常量定义 ===
DATA_PATH = "data/expenses.json"
os.makedirs("data", exist_ok=True)

UNITS = {
    "1": "Danga Bay 16A-01-02",
    "2": "Danga Bay 7A-18-03A",
    "3": "Danga Bay 17C-19-02",
    "4": "RNF 6A-13A-09",
    "5": "RNF B1-1 23-06",
    "6": "testing（测试专用）"
}
MONTH_CONTEXT = {}

def load_data():
    if Path(DATA_PATH).exists():
        with open(DATA_PATH, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# === /start 指令处理 ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in MONTH_CONTEXT:
        MONTH_CONTEXT[user_id] = datetime.now().strftime("%Y-%m")

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

# === 按钮逻辑 ===
STATE = {}

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    await query.answer()
    data = query.data

    if data == "add_expense":
        STATE[user_id] = "awaiting_expense"
        await query.edit_message_text("请输入消费内容，例如：电费 RM100")
    elif data == "view_records":
        STATE[user_id] = "choose_view_unit"
        keyboard = [[InlineKeyboardButton(v, callback_data=f"view_{k}")] for k, v in UNITS.items()]
        await query.edit_message_text("请选择要查看账单的单位：", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("view_"):
        unit_id = data.split("_")[1]
        month = MONTH_CONTEXT.get(user_id, datetime.now().strftime("%Y-%m"))
        all_data = load_data()
        unit_data = all_data.get(month, {}).get(unit_id, [])
        if not unit_data:
            await query.edit_message_text(f"{UNITS[unit_id]} 在 {month} 没有记录。")
        else:
            text = f"📂 {UNITS[unit_id]} 的 {month} 记录：\n"
            for i, item in enumerate(unit_data, 1):
                text += f"{i}. {item['item']} - RM{item['amount']}\n"
            await query.edit_message_text(text)
    elif data == "switch_month":
        STATE[user_id] = "switching_month"
        await query.edit_message_text("请输入月份（格式如 2024-12）：")
    elif data == "total":
        all_data = load_data()
        month = MONTH_CONTEXT.get(user_id, datetime.now().strftime("%Y-%m"))
        month_data = all_data.get(month, {})
        total = sum(item["amount"] for unit in month_data.values() for item in unit)
        await query.edit_message_text(f"{month} 总消费为：RM{total:.2f}")
    elif data == "download":
        await handle_excel_download(update, context, user_id)

application.add_handler(CallbackQueryHandler(handle_button))

# === 处理文本回复 ===
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()

    if STATE.get(user_id) == "awaiting_expense":
        await handle_expense_record(update, user_id, text)
    elif STATE.get(user_id) == "switching_month":
        MONTH_CONTEXT[user_id] = text
        STATE[user_id] = None
        await update.message.reply_text(f"✅ 当前查询月份已切换为 {text}")
    else:
        await update.message.reply_text("❓ 请输入 /start 开始")

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

async def handle_expense_record(update, user_id, text):
    if "RM" not in text:
        await update.message.reply_text("⚠️ 格式错误，应包含 RM，例如：水费 RM50")
        return

    parts = text.split("RM")
    item = parts[0].strip()
    try:
        amount = float(parts[1].strip())
    except ValueError:
        return await update.message.reply_text("金额格式错误，请输入数字")

    keyboard = [[InlineKeyboardButton(v, callback_data=f"save_{k}_{item}_{amount}")] for k, v in UNITS.items()]
    await update.message.reply_text("请选择单位：", reply_markup=InlineKeyboardMarkup(keyboard))

@application.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.data.startswith("save_")))
async def confirm_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_", 3)
    unit_id, item, amount = parts[1], parts[2], float(parts[3])
    user_id = str(query.from_user.id)
    month = MONTH_CONTEXT.get(user_id, datetime.now().strftime("%Y-%m"))

    all_data = load_data()
    all_data.setdefault(month, {}).setdefault(unit_id, []).append({"item": item, "amount": amount})
    save_data(all_data)
    await query.edit_message_text(f"✅ 已记录：{UNITS[unit_id]} - {item} RM{amount:.2f}")

# === 生成 Excel ===
async def handle_excel_download(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    month = MONTH_CONTEXT.get(user_id, datetime.now().strftime("%Y-%m"))
    all_data = load_data()
    data = all_data.get(month, {})

    if not data:
        await update.callback_query.edit_message_text("❌ 当前月份没有数据")
        return

    rows = []
    for uid, records in data.items():
        for rec in records:
            rows.append({"Unit": UNITS[uid], "Item": rec["item"], "Amount": rec["amount"]})

    df = pd.DataFrame(rows)
    filename = f"data/{month}_summary.xlsx"
    df.to_excel(filename, index=False)

    await update.callback_query.message.reply_document(InputFile(filename), filename=filename)

# === Webhook 修复版（同步） ===
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
