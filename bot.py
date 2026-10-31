from robobot import Bot
import json
import os
import re
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

TOKEN = os.environ.get("BOT_TOKEN", "")
if not TOKEN:
    print("❌ BOT_TOKEN تنظیم نشده!")
    exit(1)

bot = Bot(TOKEN)
DATA_FILE = "bot_data.json"

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

def get_target(text, event):
    m = re.search(r'rubika\.ir/([uc]0[0-9a-zA-Z]{10,})', text or "")
    if m: return m.group(1)
    m = re.search(r'\b([uc]0[0-9a-zA-Z]{10,})\b', text or "")
    if m: return m.group(1)
    return None

def inc_count(ck, uid):
    mc = data.setdefault("msg_count", {}).setdefault(ck, {})
    mc[str(uid)] = mc.get(str(uid), 0) + 1
    save_data(data)

HELP = """📚 **راهنمای ربات**

🔹 /start یا راهنما
🔹 /ping یا پینگ
🔹 /time یا زمان
🔹 /id یا شناسه
🔹 /rules یا قوانین
🔹 /stats یا آمار
🔹 /admins یا ادمین‌ها
🔹 /lock یا قفل کردن گروه
🔹 /unlock یا باز کردن گروه
🔹 /delete یا حذف (با ریپلای)
🔹 /ban یا بن (با آیدی)
🔹 /kick یا اخراج (با آیدی)
🔹 /warn یا اخطار (با آیدی)
🔹 /unwarn یا حذف اخطار (با آیدی)
🔹 /silence یا سکوت (با آیدی)
🔹 /unsilence یا حذف سکوت (با آیدی)
🔹 /admin یا ادمین (با آیدی)
🔹 /demote یا برکنار (با آیدی)
🔹 /clear یا پاک (مثلاً پاک ۵)
🔹 /locklink یا لینک قفل
🔹 /unlocklink یا لینک باز
🔹 /lockid یا آیدی قفل
🔹 /unlockid یا آیدی باز
🔹 /lockbad یا فحش قفل
🔹 /unlockbad یا فحش باز
🔹 /setrules یا تنظیم قوانین <متن>
🔹 /setwelcome یا تنظیم پیام خوش آمدی <متن>
🔹 /delwelcome یا حذف پیام خوش آمدی
"""

class HC(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
    def log_message(self, *a): pass

def run_http():
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 8080))), HC).serve_forever()

# ✅ همه دستورات از on_message استفاده می‌کنند و با/بدون اسلش کار می‌کنند
@bot.on_message()
async def handle_all(bot, event):
    try:
        if not event.text: return
        raw = event.text.strip()
        # ✅ حذف اسلش از ابتدای متن (اگر بود)
        text = raw.lstrip("/")
        ck = str(event.chat_id)
        uid = str(event.author_id)

        inc_count(ck, uid)

        # فیلترها (فقط در گروه)
        if ck.startswith("c") or ck.startswith("g"):
            f = data.get("filters", {}).get(ck, {})
            if f.get("link") and LINK_PATTERN.search(text):
                await bot.delete_message(event.chat_id, event.message_id); return
            if f.get("id") and ID_PATTERN.search(text):
                await bot.delete_message(event.chat_id, event.message_id); return
            if f.get("bad") and has_bad(text):
                await bot.delete_message(event.chat_id, event.message_id); return
            if ck in data.get("locked", []) and not is_owner_or_admin(ck, uid):
                await bot.delete_message(event.chat_id, event.message_id); return
            if is_silenced(ck, uid) and not is_owner_or_admin(ck, uid):
                await bot.delete_message(event.chat_id, event.message_id); return

        # ---------- دستورات (با/بدون اسلش) ----------
        if text in ("start", "راهنما", "help"):
            await event.reply(HELP); return
        if text in ("ping", "پینگ"):
            await event.reply("🏓 پونگ!"); return
        if text in ("time", "زمان"):
            await event.reply(f"🕐 {datetime.now():%Y/%m/%d - %H:%M:%S}"); return
        if text in ("setowner", "ثبت مالک"):
            if ck not in data.get("owners", {}):
                data["owners"][ck] = uid; save_data(data); await event.reply(f"✅ مالک: `{uid}`")
            else: await event.reply(f"ℹ️ مالک: `{data['owners'][ck]}`")
            return
        if text in ("id", "شناسه"):
            t = get_target(text, event); await event.reply(f"🆔 `{t or uid}`"); return
        if text in ("delete", "حذف"):
            if not event.reply_to_message_id: await event.reply("❌ ریپلای کن."); return
            try: await bot.delete_message(event.chat_id, event.reply_to_message_id); await event.reply("✅ حذف شد.")
            except Exception as e: await event.reply(f"❌ {e}")
            return
        if text.startswith("ban") or text.startswith("بن"):
            t = get_target(text, event)
            if not t: await event.reply("❌ آیدی/لینک بده."); return
            try: await bot.ban_member(chat_id=event.chat_id, sender_id=t); data["banned"].setdefault(ck, []).append(t); save_data(data); await event.reply(f"🔨 {t} بن شد.")
            except Exception as e: await event.reply(f"❌ {e}")
            return
        if text.startswith("kick") or text.startswith("اخراج"):
            t = get_target(text, event)
            if not t: await event.reply("❌ آیدی/لینک بده."); return
            try: await bot.ban_member(chat_id=event.chat_id, sender_id=t); await bot.unban_member(chat_id=event.chat_id, sender_id=t); await event.reply("👢 اخراج شد.")
            except Exception as e: await event.reply(f"❌ {e}")
            return
        if text.startswith("warn") or text.startswith("اخطار"):
            t = get_target(text, event)
            if not t: await event.reply("❌ آیدی/لینک بده."); return
            w = data["warns"].setdefault(ck, {}); w[t] = w.get(t, 0) + 1; save_data(data)
            if w[t] >= 3:
                try: await bot.ban_member(chat_id=event.chat_id, sender_id=t); await event.reply(f"🔨 {t} بن شد (۳ اخطار).")
                except Exception as e: await event.reply(f"⚠️ {e}")
            else: await event.reply(f"⚠️ اخطار {w[t]}/۳ برای {t}.")
            return
        if text.startswith("unwarn") or text.startswith("حذف اخطار"):
            t = get_target(text, event)
            if not t: await event.reply("❌ آیدی/لینک بده."); return
            w = data["warns"].get(ck, {})
            if t in w: del w[t]; save_data(data); await event.reply("✅ پاک شد.")
            else: await event.reply("ℹ️ نداشت.")
            return
        if text in ("rules", "قوانین"):
            r = data["rules"].get(ck); await event.reply(f"📜 {r}" if r else "📜 تنظیم نشده."); return
        if text.startswith("setrules") or text.startswith("تنظیم قوانین"):
            r = text.replace("setrules", "").replace("تنظیم قوانین", "").strip()
            if not r: await event.reply("❌ متن بده."); return
            data["rules"][ck] = r; save_data(data); await event.reply("✅ تنظیم شد."); return
        if text.startswith("setwelcome") or text.startswith("تنظیم پیام خوش آمدی"):
            w = text.replace("setwelcome", "").replace("تنظیم پیام خوش آمدی", "").strip()
            if not w: await event.reply("❌ متن بده."); return
            data["welcome"][ck] = w; save_data(data); await event.reply("✅ تنظیم شد."); return
        if text in ("delwelcome", "حذف پیام خوش آمدی"):
            if ck in data["welcome"]: del data["welcome"][ck]; save_data(data); await event.reply("✅ حذف شد.")
            else: await event.reply("ℹ️ تنظیم نشده بود.")
            return
        if text in ("lock", "قفل کردن گروه"):
            if ck not in data["locked"]: data["locked"].append(ck); save_data(data)
            await event.reply("🔒 قفل شد."); return
        if text in ("unlock", "باز کردن گروه"):
            if ck in data["locked"]: data["locked"].remove(ck); save_data(data)
            await event.reply("🔓 باز شد."); return
        if text.startswith("silence") or text.startswith("سکوت"):
            t = get_target(text, event)
            if not t: await event.reply("❌ بنویس: سکوت u0..."); return
            s = data.setdefault("silenced", {}).setdefault(ck, [])
            if t not in s: s.append(t); save_data(data)
            await event.reply(f"🤐 {t} سکوت شد."); return
        if text.startswith("unsilence") or text.startswith("حذف سکوت"):
            t = get_target(text, event)
            if not t: await event.reply("❌ بنویس: حذف سکوت u0..."); return
            s = data.setdefault("silenced", {}).setdefault(ck, [])
            if t in s: s.remove(t); save_data(data); await event.reply(f"🔊 {t} آزاد شد.")
            else: await event.reply("ℹ️ سکوت نبود.")
            return
        if text in ("locklink", "لینک قفل"):
            data.setdefault("filters", {}).setdefault(ck, {})["link"] = True; save_data(data); await event.reply("🔗 فیلتر لینک فعال شد."); return
        if text in ("unlocklink", "لینک باز"):
            data.setdefault("filters", {}).setdefault(ck, {})["link"] = False; save_data(data); await event.reply("🔓 فیلتر لینک غیرفعال شد."); return
        if text in ("lockid", "آیدی قفل"):
            data.setdefault("filters", {}).setdefault(ck, {})["id"] = True; save_data(data); await event.reply("🆔 فیلتر آیدی فعال شد."); return
        if text in ("unlockid", "آیدی باز"):
            data.setdefault("filters", {}).setdefault(ck, {})["id"] = False; save_data(data); await event.reply("🔓 فیلتر آیدی غیرفعال شد."); return
        if text in ("lockbad", "فحش قفل"):
            data.setdefault("filters", {}).setdefault(ck, {})["bad"] = True; save_data(data); await event.reply("🤬 فیلتر فحش فعال شد."); return
        if text in ("unlockbad", "فحش باز"):
            data.setdefault("filters", {}).setdefault(ck, {})["bad"] = False; save_data(data); await event.reply("🔓 فیلتر فحش غیرفعال شد."); return
        if text.startswith("admin") and not text.startswith("admins") or text.startswith("ادمین") and not text.startswith("ادمین‌ها"):
            t = get_target(text, event)
            if not t: await event.reply("❌ ادمین u0..."); return
            a = data.setdefault("admins", {}).setdefault(ck, [])
            if t not in a: a.append(t); save_data(data)
            await event.reply(f"👑 {t} ادمین شد."); return
        if text.startswith("demote") or text.startswith("برکنار"):
            t = get_target(text, event)
            if not t: await event.reply("❌ برکنار u0..."); return
            a = data.setdefault("admins", {}).setdefault(ck, [])
            if t in a: a.remove(t); save_data(data); await event.reply(f"🚫 {t} برکنار شد.")
            else: await event.reply("ℹ️ ادمین نبود.")
            return
        if text in ("admins", "ادمین‌ها"):
            a = data.get("admins", {}).get(ck, []); o = data.get("owners", {}).get(ck, "—")
            await event.reply(f"👑 مالک: `{o}`\n\n**ادمین‌ها:**\n" + ("\n".join(f"• `{x}`" for x in a) if a else "—")); return
        if text.startswith("clear") or text.startswith("پاک"):
            p = text.replace("clear", "").replace("پاک", "").strip().split()
            if not p or not p[0].isdigit(): await event.reply("❌ پاک <۱-۵۰۰>"); return
            n = int(p[0])
            if not 1 <= n <= 500: await event.reply("❌ ۱ تا ۵۰۰."); return
            d = 0
            for i in range(1, n+1):
                tid = event.message_id - i
                if tid <= 0: break
                try: await bot.delete_message(event.chat_id, tid); d += 1
                except: pass
            await event.reply(f"🧹 {d} پیام پاک شد."); return
        if text in ("stats", "آمار"):
            w = data["warns"].get(ck, {}); b = data["banned"].get(ck, []); mc = data.get("msg_count", {}).get(ck, {})
            top = sorted(mc.items(), key=lambda x: -x[1])[:10]
            top_s = "\n".join(f"{i}. [{u}](https://rubika.ir/{u}) — {c} پیام" for i, (u, c) in enumerate(top, 1)) or "—"
            f = data.get("filters", {}).get(ck, {})
            await event.reply(
                f"📊 **آمار**\n👤 مالک: `{data.get('owners',{}).get(ck,'—')}`\n"
                f"👑 ادمین‌ها: {len(data.get('admins',{}).get(ck,[]))}\n"
                f"🔒 گروه: {'بسته' if ck in data.get('locked',[]) else 'باز'}\n"
                f"فیلترها: 🔗{'✅' if f.get('link') else '❌'} 🆔{'✅' if f.get('id') else '❌'} 🤬{'✅' if f.get('bad') else '❌'}\n"
                f"🤐 سکوت: {len(data.get('silenced',{}).get(ck,[]))} | 👥 بن: {len(b)} | ⚠️ اخطار: {len(w)}\n"
                f"💬 کل: {sum(mc.values())}\n\n🏆 **۱۰ نفر اول:**\n{top_s}"
            ); return
    except Exception as e:
        print(f"❌ خطا: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_http, daemon=True).start()
    print("✅ ربات فعال شد!")
    bot.run()
