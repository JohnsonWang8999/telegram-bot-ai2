import os
import json
import asyncio
import datetime
from flask import Flask, request
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
import pandas as pd
from pathlib import Path

# === 环境变量 ===
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH", "myhook")
PORT = int(os.environ.get("PORT", 10000))
BASE_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}"

flask_app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()

# === 常量配置 ===
RECORD_FILE = "records.json"
UNIT_MAP = {
    "1": "Danga Bay 16A-01-02",
    "2": "Danga Bay 7A-18-03A",
    "3": "Danga Bay 17C-19-02",
    "4": "RNF 6A-13A-09",
    "5": "RNF B1-1 23-06",
    "6": "testing（测试专用）",
}

# === 全局缓存 ===
user_state = {}

# === 工具方法 ===
def load_data():
    if Path(RECORD_FILE).exists():
        with open(RECORD_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(RECORD_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def current_ym():
    return datetime.datetime.now().strftime("%Y-%m")

# === /start 指令 ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📂 查看账单", callback_data="view")],
        [InlineKeyboardButton("📝 记录消费", callback_data="add")],
        [InlineKeyboardButton("📅 切换月份", callback_data="switch")],
    ]
    await update.message.reply_text(
        "欢迎使用 Short Escape Telegram Bot!\n\n请选择操作：",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# === 按钮逻辑 ===
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "add":
        # 弹出单位列表
        buttons = [
            [InlineKeyboardButton(name, callback_data=f"unit_{uid}")]
            for uid, name in UNIT_MAP.items()
        ]
        await query.edit_message_text("请选择房源单位：", reply_markup=InlineKeyboardMarkup(buttons))

    elif query.data.startswith("unit_"):
        unit_id = query.data.split("_")[1]
        user_state[user_id] = {"unit": UNIT_MAP[unit_id], "step": "waiting_expense"}
        await query.edit_message_text(f"请输入消费内容，例如：换灯泡 RM100")

    elif query.data == "view":
        data = load_data()
        ym = current_ym()
        summary = f"📆 {ym} 账单汇总：\n"
        all_records = data.get(ym, {})
        total = 0
        for unit, records in all_records.items():
            unit_total = sum([int(r["amount"]) for r in records])
            summary += f"\n🏠 {unit}:\n"
            for r in records:
                summary += f"  - {r['item']} RM{r['amount']}\n"
            summary += f"  💰小计：RM{unit_total}\n"
            total += unit_total
        summary += f"\n📊 总消费：RM{total}"
        await query.edit_message_text(summary or "暂无数据。")

    elif query.data == "switch":
        await query.edit_message_text("📅 功能开发中：将支持手动切换月份")

# === 处理文本 ===
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id in user_state and user_state[user_id].get("step") == "waiting_expense":
        unit = user_state[user_id]["unit"]
        ym = current_ym()
        data = load_data()
        data.setdefault(ym, {}).setdefault(unit, [])
        # 自动识别金额（默认最后一个数字是金额）
        parts = text.strip().rsplit(" RM", 1)
        if len(parts) != 2 or not parts[1].isdigit():
            await update.message.reply_text("❌ 格式错误，请用 '事项 RM金额' 格式。")
            return
        item, amount = parts
        data[ym][unit].append({"item": item.strip(), "amount": int(amount)})
        save_data(data)
        del user_state[user_id]
        await update.message.reply_text("✅ 记录成功！")

# === 注册 ===
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(handle_button))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

# === webhook ===
@flask_app.route(f"/{WEBHOOK_SECRET_PATH}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    if not application.running:
        asyncio.run(application.initialize())
    asyncio.run(application.process_update(update))
    return "ok"

# === 启动 ===
if __name__ == "__main__":
    async def run():
        print(f"==> Setting webhook to {BASE_URL}/{WEBHOOK_SECRET_PATH}")
        await application.bot.set_webhook(url=f"{BASE_URL}/{WEBHOOK_SECRET_PATH}")
        flask_app.run(host="0.0.0.0", port=PORT)

    asyncio.run(run())
