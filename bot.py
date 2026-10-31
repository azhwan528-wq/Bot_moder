from rubpy.bot import BotClient, filters
from rubpy.bot.models import Update
import json
import os
import re
import threading
import asyncio
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

TOKEN = os.environ.get("BOT_TOKEN", "")
if not TOKEN:
    print("❌ متغیر BOT_TOKEN تنظیم نشده!")
    exit(1)

app = BotClient(TOKEN)
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

def is_old_message(update, threshold=120):
    try:
        msg = update.new_message
        if not msg: return True
        t = getattr(msg, 'time', None)
        if not t: return False
        return (datetime.now() - datetime.fromtimestamp(int(t))).total_seconds() > threshold
    except: return False

def get_target(text, update):
    msg = update.new_message
    if getattr(msg, 'reply_to_message_id', None) and hasattr(msg, 'reply_to_message') and msg.reply_to_message:
        r = msg.reply_to_message
        if hasattr(r, 'sender_id'): return str(r.sender_id)
    m = re.search(r'rubika\.ir/([uc]0[0-9a-zA-Z]{10,})', text or "")
    if m: return m.group(1)
    m = re.search(r'\b([uc]0[0-9a-zA-Z]{10,})\b', text or "")
    if m: return m.group(1)
    return None

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

HELP = """📚 **راهنمای ربات**

🔹 حذف / بن / اخراج / اخطار / حذف اخطار — با ریپلای یا آیدی
🔹 شناسه — نمایش آیدی شما
🔹 قوانین / تنظیم قوانین <متن>
🔹 تنظیم پیام خوش آمدی <متن> / حذف پیام خوش آمدی
🔹 قفل کردن گروه / باز کردن گروه
🔹 سکوت u0... / حذف سکوت u0...
🔹 پاک <تعداد> (۱ تا ۵۰۰)
🔹 لینک قفل / لینک باز
🔹 آیدی قفل / آیدی باز
🔹 فحش قفل / فحش باز
🔹 ادمین u0... / برکنار u0... / ادمین‌ها
🔹 زمان / پینگ / آمار / راهنما
"""

class HC(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
    def log_message(self, *a): pass

def run_http():
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 8080))), HC).serve_forever()

def inc_count(ck, uid):
    mc = data.setdefault("msg_count", {}).setdefault(ck, {})
    mc[str(uid)] = mc.get(str(uid), 0) + 1
    save_data(data)

@app.on_update(filters.text, filters.group)
async def group_handler(client, update: Update):
    try:
        if not update.new_message or not getattr(update.new_message, 'text', None): return
        if is_old_message(update): return

        text = update.new_message.text.strip()
        cid = update.chat_id
        ck = str(cid)
        uid = str(update.new_message.sender_id)
        mid = update.new_message.message_id

        inc_count(ck, uid)

        # فیلترها
        del_reason = None
        if data.get("filters", {}).get(ck, {}).get("link") and LINK_PATTERN.search(text): del_reason = "لینک"
        elif data.get("filters", {}).get(ck, {}).get("id") and ID_PATTERN.search(text): del_reason = "آیدی"
        elif data.get("filters", {}).get(ck, {}).get("bad") and has_bad(text): del_reason = "فحش"
        elif ck in data.get("locked", []) and not is_owner_or_admin(ck, uid): del_reason = "قفل"
        elif is_silenced(ck, uid) and not is_owner_or_admin(ck, uid): del_reason = "سکوت"

        if del_reason:
            try: await client.delete_message(cid, mid)
            except: pass
            return

        # دستورات
        if text in ("راهنما", "help", "/help", "/start"): await update.reply(HELP); return
        if text in ("پینگ", "/ping"): await update.reply("🏓 پونگ!"); return
        if text in ("زمان", "/time"): await update.reply(f"🕐 {datetime.now():%Y/%m/%d - %H:%M:%S}"); return
        if text in ("ثبت مالک", "/setowner"):
            if ck not in data.get("owners", {}):
                data["owners"][ck] = uid; save_data(data); await update.reply(f"✅ مالک: `{uid}`")
            else: await update.reply(f"ℹ️ مالک: `{data['owners'][ck]}`")
            return
        if text in ("شناسه", "/id"):
            t = get_target("", update); await update.reply(f"🆔 `{t or uid}`"); return
        if text in ("حذف", "/delete"):
            if not update.new_message.reply_to_message_id: await update.reply("❌ ریپلای کن."); return
            try: await client.delete_message(cid, update.new_message.reply_to_message_id); await update.reply("✅ حذف شد.")
            except Exception as e: await update.reply(f"❌ {e}")
            return
        if text.startswith("بن") or text.startswith("/ban"):
            t = get_target(text, update)
            if not t: await update.reply("❌ ریپلای یا آیدی/لینک."); return
            try: await client.ban_chat_member(cid, t); data["banned"].setdefault(ck, []).append(t); save_data(data); await update.reply(f"🔨 {t} بن شد.")
            except Exception as e: await update.reply(f"❌ {e}")
            return
        if text.startswith("اخراج") or text.startswith("/kick"):
            t = get_target(text, update)
            if not t: await update.reply("❌ ریپلای یا آیدی."); return
            try: await client.ban_chat_member(cid, t); await client.unban_chat_member(cid, t); await update.reply("👢 اخراج شد.")
            except Exception as e: await update.reply(f"❌ {e}")
            return
        if text.startswith("اخطار") or text.startswith("/warn"):
            t = get_target(text, update)
            if not t: await update.reply("❌ ریپلای یا آیدی."); return
            w = data["warns"].setdefault(ck, {}); w[t] = w.get(t, 0) + 1; save_data(data)
            if w[t] >= 3:
                try: await client.ban_chat_member(cid, t); await update.reply(f"🔨 {t} بن شد (۳ اخطار).")
                except Exception as e: await update.reply(f"⚠️ {e}")
            else: await update.reply(f"⚠️ اخطار {w[t]}/۳ برای {t}.")
            return
        if text.startswith("حذف اخطار") or text.startswith("/unwarn"):
            t = get_target(text, update)
            if not t: await update.reply("❌ ریپلای یا آیدی."); return
            w = data["warns"].get(ck, {})
            if t in w: del w[t]; save_data(data); await update.reply("✅ پاک شد.")
            else: await update.reply("ℹ️ نداشت.")
            return
        if text in ("قوانین", "/rules"):
            r = data["rules"].get(ck); await update.reply(f"📜 {r}" if r else "📜 تنظیم نشده."); return
        if text.startswith("تنظیم قوانین") or text.startswith("/setrules"):
            r = text.replace("تنظیم قوانین", "").replace("/setrules", "").strip()
            if not r: await update.reply("❌ متن بده."); return
            data["rules"][ck] = r; save_data(data); await update.reply("✅ تنظیم شد."); return
        if text.startswith("تنظیم پیام خوش آمدی") or text.startswith("/setwelcome"):
            w = text.replace("تنظیم پیام خوش آمدی", "").replace("/setwelcome", "").strip()
            if not w: await update.reply("❌ متن بده."); return
            data["welcome"][ck] = w; save_data(data); await update.reply("✅ تنظیم شد."); return
        if text in ("حذف پیام خوش آمدی", "/delwelcome"):
            if ck in data["welcome"]: del data["welcome"][ck]; save_data(data); await update.reply("✅ حذف شد.")
            else: await update.reply("ℹ️ تنظیم نشده بود.")
            return
        if text in ("قفل کردن گروه", "/lock"):
            if ck not in data["locked"]: data["locked"].append(ck); save_data(data)
            await update.reply("🔒 قفل شد."); return
        if text in ("باز کردن گروه", "/unlock"):
            if ck in data["locked"]: data["locked"].remove(ck); save_data(data)
            await update.reply("🔓 باز شد."); return
        if text.startswith("سکوت") or text.startswith("/silence"):
            t = get_target(text, update)
            if not t: await update.reply("❌ بنویس: سکوت u0..."); return
            s = data.setdefault("silenced", {}).setdefault(ck, [])
            if t not in s: s.append(t); save_data(data)
            await update.reply(f"🤐 {t} سکوت شد."); return
        if text.startswith("حذف سکوت") or text.startswith("/unsilence"):
            t = get_target(text, update)
            if not t: await update.reply("❌ بنویس: حذف سکوت u0..."); return
            s = data.setdefault("silenced", {}).setdefault(ck, [])
            if t in s: s.remove(t); save_data(data); await update.reply(f"🔊 {t} آزاد شد.")
            else: await update.reply("ℹ️ سکوت نبود.")
            return
        # فیلترها
        for cmd, key, msg in [
            ("لینک قفل", "link", "🔗 فعال شد"), ("لینک باز", "link", "🔓 غیرفعال شد"),
            ("آیدی قفل", "id", "🆔 فعال شد"), ("آیدی باز", "id", "🔓 غیرفعال شد"),
            ("فحش قفل", "bad", "🤬 فعال شد"), ("فحش باز", "bad", "🔓 غیرفعال شد"),
        ]:
            if text in (cmd, f"/{cmd.replace(' ', '')}"):
                data.setdefault("filters", {}).setdefault(ck, {})[key] = "قفل" in cmd
                save_data(data); await update.reply(msg); return
        # ادمین
        if text.startswith("ادمین") and not text.startswith("ادمین‌ها") or text.startswith("/admin"):
            t = get_target(text, update)
            if not t: await update.reply("❌ ادمین u0..."); return
            a = data.setdefault("admins", {}).setdefault(ck, [])
            if t not in a: a.append(t); save_data(data)
            await update.reply(f"👑 {t} ادمین شد."); return
        if text.startswith("برکنار") or text.startswith("/demote"):
            t = get_target(text, update)
            if not t: await update.reply("❌ برکنار u0..."); return
            a = data.setdefault("admins", {}).setdefault(ck, [])
            if t in a: a.remove(t); save_data(data); await update.reply(f"🚫 {t} برکنار شد.")
            else: await update.reply("ℹ️ ادمین نبود.")
            return
        if text in ("ادمین‌ها", "/admins"):
            a = data.get("admins", {}).get(ck, []); o = data.get("owners", {}).get(ck, "—")
            await update.reply(f"👑 مالک: `{o}`\n\n**ادمین‌ها:**\n" + ("\n".join(f"• `{x}`" for x in a) if a else "—"))
            return
        if text.startswith("پاک") or text.startswith("/clear"):
            p = text.replace("/clear", "").replace("پاک", "").strip().split()
            if not p or not p[0].isdigit(): await update.reply("❌ پاک <۱-۵۰۰>"); return
            n = int(p[0])
            if not 1 <= n <= 500: await update.reply("❌ ۱ تا ۵۰۰."); return
            d = 0
            for i in range(1, n+1):
                tid = mid - i
                if tid <= 0: break
                try: await client.delete_message(cid, tid); d += 1
                except: pass
            await update.reply(f"🧹 {d} پیام پاک شد."); return
        if text in ("آمار", "/stats"):
            w = data["warns"].get(ck, {}); b = data["banned"].get(ck, []); mc = data.get("msg_count", {}).get(ck, {})
            top = sorted(mc.items(), key=lambda x: -x[1])[:10]
            top_s = "\n".join(f"{i}. [{u}](https://rubika.ir/{u}) — {c} پیام" for i, (u, c) in enumerate(top, 1)) or "—"
            f = data.get("filters", {}).get(ck, {})
            await update.reply(
                f"📊 **آمار**\n👤 مالک: `{data.get('owners',{}).get(ck,'—')}`\n"
                f"👑 ادمین‌ها: {len(data.get('admins',{}).get(ck,[]))}\n"
                f"🔒 گروه: {'بسته' if ck in data.get('locked',[]) else 'باز'}\n"
                f"فیلترها: 🔗{'✅' if f.get('link') else '❌'} 🆔{'✅' if f.get('id') else '❌'} 🤬{'✅' if f.get('bad') else '❌'}\n"
                f"🤐 سکوت: {len(data.get('silenced',{}).get(ck,[]))} | 👥 بن: {len(b)} | ⚠️ اخطار: {len(w)}\n"
                f"💬 کل: {sum(mc.values())}\n\n🏆 **۱۰ نفر اول:**\n{top_s}"
            ); return
    except Exception as e:
        print(f"❌ خطا: {e}")

@app.on_update(filters.text, filters.private)
async def private_handler(client, update: Update):
    try:
        if not update.new_message or not getattr(update.new_message, 'text', None): return
        if is_old_message(update): return
        await update.reply("👋 سلام!\nمن رو به گروه اضافه کن و ادمین کن. بعد بنویس «راهنما».")
    except Exception as e: print(f"❌ {e}")

if __name__ == "__main__":
    threading.Thread(target=run_http, daemon=True).start()
    print("✅ ربات فعال شد!")
    app.run()
