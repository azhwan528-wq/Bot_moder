from rubpy.bot import BotClient, filters
from rubpy.bot.models import Update
import json
import os
import re
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# ---------- توکن از Environment Variable ----------
TOKEN = os.environ.get("BOT_TOKEN", "")
if not TOKEN:
    print("❌ متغیر BOT_TOKEN تنظیم نشده!")
    exit(1)

app = BotClient(TOKEN)

DATA_FILE = "bot_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"rules": {}, "warns": {}, "banned": {}}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

def get_chat_key(chat_id):
    return str(chat_id)

def get_target_from_command(text, update):
    """استخراج آیدی از ریپلای یا متن"""
    msg = update.new_message
    if not msg:
        return None

    # ۱. ریپلای
    if getattr(msg, 'reply_to_message_id', None):
        if hasattr(msg, 'reply_to_message') and msg.reply_to_message:
            replied = msg.reply_to_message
            if hasattr(replied, 'sender_id'):
                return str(replied.sender_id)

    # ۲. آیدی فرمت‌شده از متن (u0... یا c0...)
    match = re.search(r'\b([uc]0[0-9a-zA-Z]{10,})\b', text or "")
    if match:
        return match.group(1)

    # ۳. عدد خالی
    match = re.search(r'\b(\d{10,20})\b', text or "")
    if match:
        return match.group(1)

    return None

HELP_TEXT = """📚 **راهنمای ربات مدیریت گروه**

🔹 **حذف** — با ریپلای روی پیام
🔹 **بن** — با ریپلای یا آیدی (مثل u0xxxx)
🔹 **اخراج** — با ریپلای یا آیدی
🔹 **اخطار** — با ریپلای یا آیدی
🔹 **حذف اخطار** — با ریپلای یا آیدی
🔹 **شناسه** — نمایش شناسه کاربر (با ریپلای)
🔹 **قوانین** — نمایش قوانین
🔹 **تنظیم قوانین <متن>** — تعیین قوانین
🔹 **آمار** — آمار گروه
🔹 **راهنما** — نمایش این راهنما
"""

# ---------- HTTP Health Check برای UptimeRobot ----------
class HealthCheck(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *args):
        pass

def run_http():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheck)
    print(f"🌐 HTTP health check on port {port}")
    server.serve_forever()

# ---------- هندلر گروه ----------
@app.on_update(filters.text, filters.group)
async def group_handler(client, update: Update):
    # ✅ بررسی امن
    if not update.new_message or not getattr(update.new_message, 'text', None):
        return

    text = update.new_message.text.strip()
    chat_id = update.chat_id
    chat_key = get_chat_key(chat_id)

    if text in ("راهنما", "help", "/help", "/start"):
        await update.reply(HELP_TEXT)
        return

    # ---------- شناسه ----------
    if text in ("شناسه", "/id"):
        target = get_target_from_command("", update)
        if target:
            await update.reply(f"🆔 شناسه: `{target}`")
        else:
            sender = update.new_message.sender_id
            await update.reply(f"🆔 شناسه شما: `{sender}`\n(برای گرفتن شناسه دیگران، روی پیامشون ریپلای کن و بنویس «شناسه»)")
        return

    # ---------- حذف ----------
    if text in ("حذف", "/delete"):
        reply_to = update.new_message.reply_to_message_id
        if not reply_to:
            await update.reply("❌ روی یک پیام ریپلای کن و بنویس «حذف»")
            return
        try:
            await client.delete_message(chat_id, reply_to)
            await update.reply("✅ پیام حذف شد.")
        except Exception as e:
            await update.reply(f"❌ خطا: {e}")
        return

    # ---------- بن ----------
    if text.startswith("بن") or text.startswith("/ban"):
        target = get_target_from_command(text, update)
        if not target:
            await update.reply(
                "❌ روی پیام کاربر ریپلای کن یا آیدی (u0...) را بنویس:\n"
                "مثال: بن u0K3IcG022879863e80113fb41d469ba"
            )
            return
        try:
            await client.ban_chat_member(chat_id, target)
            if chat_key not in data["banned"]:
                data["banned"][chat_key] = []
            if target not in data["banned"][chat_key]:
                data["banned"][chat_key].append(target)
            save_data(data)
            await update.reply(f"🔨 کاربر {target} بن شد.")
        except Exception as e:
            await update.reply(f"❌ خطا در بن: {e}")
        return

    # ---------- اخراج ----------
    if text.startswith("اخراج") or text.startswith("/kick"):
        target = get_target_from_command(text, update)
        if not target:
            await update.reply("❌ روی پیام کاربر ریپلای کن یا آیدی (u0...) را بنویس.")
            return
        try:
            await client.ban_chat_member(chat_id, target)
            await client.unban_chat_member(chat_id, target)
            await update.reply("👢 کاربر اخراج شد (می‌تواند برگردد).")
        except Exception as e:
            await update.reply(f"❌ خطا: {e}")
        return

    # ---------- اخطار ----------
    if text.startswith("اخطار") or text.startswith("/warn"):
        target = get_target_from_command(text, update)
        if not target:
            await update.reply("❌ روی پیام کاربر ریپلای کن یا آیدی را بنویس.")
            return
        warns = data["warns"].setdefault(chat_key, {})
        warns[str(target)] = warns.get(str(target), 0) + 1
        count = warns[str(target)]
        save_data(data)

        if count >= 3:
            try:
                await client.ban_chat_member(chat_id, target)
                await update.reply(f"🔨 کاربر {target} به‌خاطر ۳ اخطار بن شد.")
            except Exception as e:
                await update.reply(f"⚠️ اخطار ۳/۳ ولی بن نشد: {e}")
        else:
            await update.reply(f"⚠️ اخطار {count}/۳ برای کاربر {target}.")
        return

    # ---------- حذف اخطار ----------
    if text.startswith("حذف اخطار") or text.startswith("/unwarn"):
        target = get_target_from_command(text, update)
        if not target:
            await update.reply("❌ روی پیام کاربر ریپلای کن یا آیدی را بنویس.")
            return
        warns = data["warns"].get(chat_key, {})
        if str(target) in warns:
            del warns[str(target)]
            data["warns"][chat_key] = warns
            save_data(data)
            await update.reply("✅ اخطارهای کاربر پاک شد.")
        else:
            await update.reply("ℹ️ این کاربر اخطاری نداشت.")
        return

    # ---------- قوانین ----------
    if text in ("قوانین", "/rules"):
        rules = data["rules"].get(chat_key)
        if not rules:
            await update.reply("📜 هنوز قوانینی تعیین نشده.\nبرای تنظیم: «تنظیم قوانین <متن>»")
        else:
            await update.reply(f"📜 **قوانین گروه:**\n\n{rules}")
        return

    if text.startswith("تنظیم قوانین") or text.startswith("/setrules"):
        rules_text = text.replace("تنظیم قوانین", "").replace("/setrules", "").strip()
        if not rules_text:
            await update.reply("❌ بنویس: تنظیم قوانین <متن قوانین>")
            return
        data["rules"][chat_key] = rules_text
        save_data(data)
        await update.reply("✅ قوانین گروه تنظیم شد.")
        return

    # ---------- آمار ----------
    if text in ("آمار", "/stats"):
        warns = data["warns"].get(chat_key, {})
        banned = data["banned"].get(chat_key, [])
        msg = f"📊 **آمار گروه**\n\n👥 بن‌شده‌ها: {len(banned)}\n⚠️ کاربران اخطاردار: {len(warns)}"
        await update.reply(msg)
        return

# ---------- هندلر خصوصی ----------
@app.on_update(filters.text, filters.private)
async def private_handler(client, update: Update):
    # ✅ بررسی امن
    if not update.new_message or not getattr(update.new_message, 'text', None):
        return

    await update.reply(
        "👋 سلام!\n\n"
        "من یک ربات مدیریت گروه هستم.\n"
        "برای استفاده، من رو به گروه اضافه کن و **ادمین** کن.\n"
        "بعد توی گروه بنویس «راهنما» تا لیست دستورات رو ببینی."
    )

if __name__ == "__main__":
    # HTTP server در thread جدا برای UptimeRobot
    threading.Thread(target=run_http, daemon=True).start()
    print("✅ ربات مدیریت گروه فعال شد!")
    print("📋 دستورات: حذف، بن، اخراج، اخطار، شناسه، قوانین، آمار، راهنما")
    app.run()
