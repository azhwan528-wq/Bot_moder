import json
import os
import re
import threading
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

from rubka import Robot, on_message

# ---------- توکن ----------
TOKEN = os.environ.get("BOT_TOKEN", "")
if not TOKEN:
    print("❌ BOT_TOKEN تنظیم نشده!")
    exit(1)

bot = Robot(token=TOKEN)
DATA_FILE = "bot_data.json"

# ---------- لیست فحش ----------
BAD_WORDS = [
    "کس", "کیر", "کص", "کون", "جنده", "حرومزاده", "حروم", "لاشی",
    "گوه", "گوز", "پدرسگ", "مادرسگ", "سگ", "سگی", "خارکسه", "خارکصه",
    "بی ناموس", "بی شرف", "بی غیرت", "دیوث", "کشکی", "اشغال",
    "احمق", "خنگ", "کودن", "نادان", "ابله", "کثافت", "عن",
    "fuck", "shit", "bitch", "ass", "dick", "pussy", "cunt",
]

LINK_PATTERN = re.compile(r'(https?://|www\.|t\.me/|rubika\.ir/|@[A-Za-z0-9_]{5,})', re.IGNORECASE)
ID_PATTERN = re.compile(r'(u0[0-9a-zA-Z]{10,}|@[A-Za-z0-9_]{5,})')

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"rules": {}, "warns": {}, "banned": {}, "welcome": {}, "locked": [], "silenced": {}, "owners": {}, "admins": {}, "msg_count": {}, "filters": {}}

def save_data(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

data = load_data()

# ---------- توابع کمکی (بدون تغییر) ----------
def is_owner(ck, uid):
    return str(data.get("owners", {}).get(ck, "")) == str(uid)

def is_admin(ck, uid):
    return str(uid) in [str(a) for a in data.get("admins", {}).get(ck, [])]

def is_owner_or_admin(ck, uid):
    if is_owner(ck, uid) or is_admin(ck, uid): return True
    if not data.get("owners", {}).get(ck):
        data.setdefault("owners", {})[ck] = str(uid)
        save_data(data)
        return True
    return False

def is_silenced(ck, uid):
    return str(uid) in [str(u) for u in data.get("silenced", {}).get(ck, [])]

def has_bad(text):
    return any(w.lower() in text.lower() for w in BAD_WORDS)

def inc_count(ck, uid):
    mc = data.setdefault("msg_count", {}).setdefault(ck, {})
    mc[str(uid)] = mc.get(str(uid), 0) + 1
    save_data(data)

HELP = """📚 **راهنمای ربات**

🔹 start / راهنما — نمایش این راهنما
🔹 ping / پینگ — سرعت پاسخ‌دهی
🔹 time / زمان — ساعت فعلی
🔹 id / شناسه — آیدی شما
🔹 rules / قوانین — نمایش قوانین
🔹 setrules / تنظیم قوانین <متن>
🔹 stats / آمار — آمار گروه
🔹 admins / ادمین‌ها — لیست ادمین‌ها
🔹 lock / قفل کردن گروه — بستن گروه
🔹 unlock / باز کردن گروه — باز کردن گروه
🔹 delete / حذف — با ریپلای
🔹 ban / بن — با ریپلای
🔹 kick / اخراج — با ریپلای
🔹 warn / اخطار — با ریپلای
🔹 unwarn / حذف اخطار — با ریپلای
🔹 silence / سکوت — با ریپلای
🔹 unsilence / حذف سکوت — با ریپلای
🔹 admin / ادمین — با ریپلای
🔹 demote / برکنار — با ریپلای
🔹 clear / پاک <تعداد> — ۱ تا ۵۰۰
🔹 locklink / لینک قفل
🔹 unlocklink / لینک باز
🔹 lockid / آیدی قفل
🔹 unlockid / آیدی باز
🔹 lockbad / فحش قفل
🔹 unlockbad / فحش باز
🔹 setwelcome / تنظیم پیام خوش آمدی <متن>
🔹 delwelcome / حذف پیام خوش آمدی
"""

# ---------- HTTP Health Check ----------
class HC(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
    def log_message(self, *a): pass

def run_http():
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 8080))), HC).serve_forever()

# ---------- هندلر اصلی ----------
# در rubka، دکوراتور on_message پارامترهای (bot, chat_id, message_id, text, sender_id) را پاس می‌دهد.
@on_message
def handle_message(bot, chat_id, message_id, text, sender_id):
    try:
        if not text: return
        raw = text.strip()
        cmd = raw.lstrip("/")
        ck = str(chat_id)
        uid = str(sender_id)

        inc_count(ck, uid)

        # فیلترها (فقط در گروه‌ها)
        if ck.startswith("c") or ck.startswith("g"):
            f = data.get("filters", {}).get(ck, {})
            if f.get("link") and LINK_PATTERN.search(cmd):
                bot.delete_message(chat_id, message_id); return
            if f.get("id") and ID_PATTERN.search(cmd):
                bot.delete_message(chat_id, message_id); return
            if f.get("bad") and has_bad(cmd):
                bot.delete_message(chat_id, message_id); return
            if ck in data.get("locked", []) and not is_owner_or_admin(ck, uid):
                bot.delete_message(chat_id, message_id); return
            if is_silenced(ck, uid) and not is_owner_or_admin(ck, uid):
                bot.delete_message(chat_id, message_id); return

        # ---------- دستورات ----------
        if cmd in ("start", "راهنما", "help"):
            bot.send_message(chat_id, HELP, reply_to_message_id=message_id); return

        if cmd in ("ping", "پینگ"):
            start = time.time()
            bot.send_message(chat_id, "🏓 ...", reply_to_message_id=message_id)
            elapsed = int((time.time() - start) * 1000)
            bot.send_message(chat_id, f"🏓 Pong! {elapsed}ms"); return

        if cmd in ("time", "زمان"):
            bot.send_message(chat_id, f"🕐 {datetime.now():%Y/%m/%d - %H:%M:%S}", reply_to_message_id=message_id); return

        if cmd in ("setowner", "ثبت مالک"):
            if ck not in data.get("owners", {}):
                data["owners"][ck] = uid; save_data(data); bot.send_message(chat_id, f"✅ مالک: `{uid}`")
            else:
                bot.send_message(chat_id, f"ℹ️ مالک: `{data['owners'][ck]}`")
            return

        if cmd in ("id", "شناسه"):
            # در rubka، sender_id همان کاربری است که پیام را فرستاده
            bot.send_message(chat_id, f"🆔 `{uid}`", reply_to_message_id=message_id); return

        if cmd in ("delete", "حذف"):
            # در rubka راه مستقیمی برای گرفتن reply_to_message_id از رویداد نداریم
            # اما می‌توانیم از API خام استفاده کنیم. فعلاً به آیدی دستی بسنده می‌کنیم.
            bot.send_message(chat_id, "❌ این دستور در حال حاضر با ریپلای پشتیبانی نمی‌شود.", reply_to_message_id=message_id); return

        # ---------- بن، اخراج، اخطار و ... ----------
        # این دستورات در rubka با استفاده از ریپلای پشتیبانی نمی‌شوند.
        # باید از آیدی دستی استفاده کنید.
        if cmd.startswith("ban") or cmd.startswith("بن"):
            t = re.search(r'\b([uc]0[0-9a-zA-Z]{10,})\b', cmd or "")
            if not t: bot.send_message(chat_id, "❌ بنویس: بن u0...", reply_to_message_id=message_id); return
            target = t.group(1)
            try:
                bot.ban_member(chat_id, target)
                data["banned"].setdefault(ck, []).append(target); save_data(data)
                bot.send_message(chat_id, f"🔨 {target} بن شد.", reply_to_message_id=message_id)
            except Exception as e:
                bot.send_message(chat_id, f"❌ {e}", reply_to_message_id=message_id)
            return

        # ... (سایر دستورات مشابه، با استفاده از bot.send_message و reply_to_message_id=message_id)

    except Exception as e:
        print(f"❌ خطا: {e}")

# ---------- اجرا ----------
if __name__ == "__main__":
    threading.Thread(target=run_http, daemon=True).start()
    print("✅ ربات فعال شد!")
    # rubka خودش حلقه دریافت آپدیت را اجرا می‌کند
    while True:
        time.sleep(1)
