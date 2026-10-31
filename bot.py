from rubpy.bot import BotClient, filters
from rubpy.bot.models import Update
import json
import os
import re
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

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
    return {"rules": {}, "warns": {}, "banned": {}, "welcome": {}, "locked": [], "msg_count": {}}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

def get_chat_key(chat_id):
    return str(chat_id)

def get_target_from_command(text, update):
    msg = update.new_message
    if not msg:
        return None
    if getattr(msg, 'reply_to_message_id', None):
        if hasattr(msg, 'reply_to_message') and msg.reply_to_message:
            replied = msg.reply_to_message
            if hasattr(replied, 'sender_id'):
                return str(replied.sender_id)
    match = re.search(r'\b([uc]0[0-9a-zA-Z]{10,})\b', text or "")
    if match:
        return match.group(1)
    match = re.search(r'\b(\d{10,20})\b', text or "")
    if match:
        return match.group(1)
    return None

HELP_TEXT = """📚 **راهنمای ربات مدیریت گروه**

🔹 **حذف** — با ریپلای روی پیام
🔹 **بن** — با ریپلای یا آیدی (u0...)
🔹 **اخراج** — با ریپلای یا آیدی
🔹 **اخطار** — با ریپلای یا آیدی
🔹 **حذف اخطار** — با ریپلای یا آیدی
🔹 **شناسه** — نمایش شناسه کاربر
🔹 **قوانین** — نمایش قوانین
🔹 **تنظیم قوانین <متن>** — تعیین قوانین
🔹 **خوش‌آمد <متن>** — تنظیم پیام خوش‌آمد
🔹 **حذف خوش‌آمد** — حذف پیام خوش‌آمد
🔹 **قفل** — بستن گروه (فقط ادمین‌ها)
🔹 **باز کردن** — باز کردن گروه
🔹 **پاک <تعداد>** — پاک کردن پیام‌های اخیر (۱ تا ۵۰۰)
🔹 **زمان** — نمایش ساعت
🔹 **پینگ** — تست سرعت
🔹 **آمار** — آمار گروه
🔹 **راهنما** — این پیام
"""

# ---------- HTTP Health Check ----------
class HealthCheck(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *args):
        pass

def run_http():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(("0.0.0.0", port), HealthCheck).serve_forever()

# ---------- شمارش پیام ----------
def inc_msg_count(chat_key, sender):
    mc = data.setdefault("msg_count", {}).setdefault(chat_key, {})
    mc[str(sender)] = mc.get(str(sender), 0) + 1
    save_data(data)

# ---------- هندلر گروه ----------
@app.on_update(filters.text, filters.group)
async def group_handler(client, update: Update):
    if not update.new_message or not getattr(update.new_message, 'text', None):
        return

    text = update.new_message.text.strip()
    chat_id = update.chat_id
    chat_key = get_chat_key(chat_id)
    sender = str(update.new_message.sender_id)
    msg_id = update.new_message.message_id

    # شمارش پیام (همه‌ی پیام‌ها)
    inc_msg_count(chat_key, sender)

    # ---------- قفل گروه: اگر قفل است و کاربر ادمین نیست، پیامش را پاک کن ----------
    if chat_key in data.get("locked", []):
        # rubpy چک ادمین ندارد، پس فرض می‌کنیم sender_type اگر Admin نبود، پاک شود
        sender_type = getattr(update.new_message, 'sender_type', 'User')
        if sender_type != 'Admin':
            try:
                await client.delete_message(chat_id, msg_id)
            except Exception:
                pass
            return

    # ---------- راهنما ----------
    if text in ("راهنما", "help", "/help", "/start"):
        await update.reply(HELP_TEXT)
        return

    # ---------- پینگ ----------
    if text in ("پینگ", "/ping"):
        await update.reply("🏓 پونگ! ربات فعال است.")
        return

    # ---------- زمان ----------
    if text in ("زمان", "/time"):
        now = datetime.now().strftime("%Y/%m/%d - %H:%M:%S")
        await update.reply(f"🕐 {now}")
        return

    # ---------- شناسه ----------
    if text in ("شناسه", "/id"):
        target = get_target_from_command("", update)
        if target:
            await update.reply(f"🆔 شناسه: `{target}`")
        else:
            await update.reply(f"🆔 شناسه شما: `{sender}`\n(برای گرفتن شناسه دیگران، ریپلای کن و بنویس «شناسه»)")
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
            await update.reply("❌ روی پیام کاربر ریپلای کن یا آیدی (u0...) را بنویس.")
            return
        try:
            await client.ban_chat_member(chat_id, target)
            data["banned"].setdefault(chat_key, []).append(target)
            save_data(data)
            await update.reply(f"🔨 کاربر {target} بن شد.")
        except Exception as e:
            await update.reply(f"❌ خطا در بن: {e}")
        return

    # ---------- اخراج ----------
    if text.startswith("اخراج") or text.startswith("/kick"):
        target = get_target_from_command(text, update)
        if not target:
            await update.reply("❌ روی پیام کاربر ریپلای کن یا آیدی را بنویس.")
            return
        try:
            await client.ban_chat_member(chat_id, target)
            await client.unban_chat_member(chat_id, target)
            await update.reply("👢 کاربر اخراج شد.")
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
            await update.reply(f"⚠️ اخطار {count}/۳ برای {target}.")
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
            await update.reply("✅ اخطارها پاک شد.")
        else:
            await update.reply("ℹ️ اخطاری نداشت.")
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
            await update.reply("❌ بنویس: تنظیم قوانین <متن>")
            return
        data["rules"][chat_key] = rules_text
        save_data(data)
        await update.reply("✅ قوانین تنظیم شد.")
        return

    # ---------- خوش‌آمد ----------
    if text.startswith("خوش‌آمد") or text.startswith("/welcome"):
        welcome_text = text.replace("خوش‌آمد", "").replace("/welcome", "").strip()
        if not welcome_text:
            await update.reply("❌ بنویس: خوش‌آمد <متن پیام>\nمثال: خوش‌آمد سلام {name} عزیز! 🌹")
            return
        data["welcome"][chat_key] = welcome_text
        save_data(data)
        await update.reply("✅ پیام خوش‌آمد تنظیم شد.")
        return

    if text in ("حذف خوش‌آمد", "/unwelcome"):
        if chat_key in data["welcome"]:
            del data["welcome"][chat_key]
            save_data(data)
            await update.reply("✅ پیام خوش‌آمد حذف شد.")
        else:
            await update.reply("ℹ️ پیام خوش‌آمدی تنظیم نشده بود.")
        return

    # ---------- قفل گروه ----------
    if text in ("قفل", "/lock"):
        if chat_key not in data["locked"]:
            data["locked"].append(chat_key)
            save_data(data)
        await update.reply("🔒 گروه قفل شد. فقط ادمین‌ها می‌توانند پیام بدهند. (پیام کاربران عادی پاک می‌شود)")
        return

    if text in ("باز کردن", "/unlock"):
        if chat_key in data["locked"]:
            data["locked"].remove(chat_key)
            save_data(data)
        await update.reply("🔓 گروه باز شد. همه می‌توانند پیام بدهند.")
        return

    # ---------- پاک <تعداد> ----------
    if text.startswith("پاک") or text.startswith("/clear"):
        # استخراج عدد از متن
        parts = text.replace("/clear", "").replace("پاک", "").strip().split()
        if not parts or not parts[0].isdigit():
            await update.reply("❌ بنویس: پاک <تعداد>\nمثال: پاک ۳۰\n(حداقل ۱، حداکثر ۵۰۰)")
            return
        count = int(parts[0])
        if count < 1 or count > 500:
            await update.reply("❌ تعداد باید بین ۱ تا ۵۰۰ باشد.")
            return

        # حذف پیام‌های اخیر (از پیام فعلی به عقب)
        deleted = 0
        for i in range(1, count + 1):
            target_id = msg_id - i
            if target_id <= 0:
                break
            try:
                await client.delete_message(chat_id, target_id)
                deleted += 1
            except Exception:
                # اگر پیامی وجود نداشت یا قابل حذف نبود، ادامه بده
                continue

        await update.reply(f"🧹 {deleted} پیام اخیر پاک شد. (از {count} درخواست‌شده)")
        return

    # ---------- آمار ----------
    if text in ("آمار", "/stats"):
        warns = data["warns"].get(chat_key, {})
        banned = data["banned"].get(chat_key, [])
        msg_count = data.get("msg_count", {}).get(chat_key, {})
        total_msgs = sum(msg_count.values())
        top = sorted(msg_count.items(), key=lambda x: -x[1])[:3]
        top_str = "\n".join([f"• {uid}: {cnt} پیام" for uid, cnt in top]) or "—"
        locked = "🔒 بسته" if chat_key in data.get("locked", []) else "🔓 باز"
        msg = (
            f"📊 **آمار گروه**\n\n"
            f"وضعیت: {locked}\n"
            f"👥 بن‌شده‌ها: {len(banned)}\n"
            f"⚠️ اخطاردارها: {len(warns)}\n"
            f"💬 کل پیام‌ها: {total_msgs}\n\n"
            f"🏆 **پرتکلم‌ترین‌ها:**\n{top_str}"
        )
        await update.reply(msg)
        return

# ---------- هندلر خصوصی ----------
@app.on_update(filters.text, filters.private)
async def private_handler(client, update: Update):
    if not update.new_message or not getattr(update.new_message, 'text', None):
        return
    await update.reply(
        "👋 سلام!\n\n"
        "من یک ربات مدیریت گروه هستم.\n"
        "برای استفاده، من رو به گروه اضافه کن و **ادمین** کن.\n"
        "بعد توی گروه بنویس «راهنما»."
    )

if __name__ == "__main__":
    threading.Thread(target=run_http, daemon=True).start()
    print("✅ ربات مدیریت گروه فعال شد!")
    print("📋 دستورات: حذف، بن، اخراج، اخطار، شناسه، قوانین، خوش‌آمد، قفل، باز کردن، پاک <تعداد>، آمار، راهنما")
    app.run()
