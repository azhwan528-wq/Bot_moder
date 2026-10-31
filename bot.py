from robobot import Bot
import json
import os
import re
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# ---------- توکن ----------
TOKEN = os.environ.get("BOT_TOKEN", "")
if not TOKEN:
    print("❌ BOT_TOKEN تنظیم نشده!")
    exit(1)

bot = Bot(TOKEN)
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

# ---------- توابع کمکی ----------
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
    # پشتیبانی از ریپلای (اگر robobot اطلاعاتش رو بده)
    if event.reply_to_message_id:
        # robobot معمولاً sender_id پیام ریپلای‌شده رو مستقیم نمی‌ده
        # ولی اگر بخوایم، باید از API بگیریم. فعلاً فقط آیدی دستی.
        pass
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

🔹 حذف / بن / اخراج / اخطار / حذف اخطار — با آیدی یا لینک
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

# ---------- HTTP Health Check ----------
class HC(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
    def log_message(self, *a): pass

def run_http():
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 8080))), HC).serve_forever()

# ---------- دستورات ----------
@bot.on_command(["start", "راهنما", "help"])
async def cmd_help(bot, event):
    await event.reply(HELP)

@bot.on_command(["پینگ", "ping"])
async def cmd_ping(bot, event):
    await event.reply("🏓 پونگ!")

@bot.on_command(["زمان", "time"])
async def cmd_time(bot, event):
    await event.reply(f"🕐 {datetime.now():%Y/%m/%d - %H:%M:%S}")

@bot.on_command(["ثبت مالک", "setowner"])
async def cmd_setowner(bot, event):
    ck = str(event.chat_id)
    if ck not in data.get("owners", {}):
        data["owners"][ck] = str(event.author_id); save_data(data)
        await event.reply(f"✅ مالک: `{event.author_id}`")
    else:
        await event.reply(f"ℹ️ مالک: `{data['owners'][ck]}`")

@bot.on_command(["شناسه", "id"])
async def cmd_id(bot, event):
    t = get_target(event.text or "", event)
    await event.reply(f"🆔 `{t or event.author_id}`")

@bot.on_command(["حذف", "delete"])
async def cmd_delete(bot, event):
    if not event.reply_to_message_id:
        await event.reply("❌ روی یک پیام ریپلای کن.")
        return
    try:
        await bot.delete_message(event.chat_id, event.reply_to_message_id)
        await event.reply("✅ حذف شد.")
    except Exception as e:
        await event.reply(f"❌ {e}")

@bot.on_command(["بن", "ban"])
async def cmd_ban(bot, event):
    t = get_target(event.text or "", event)
    if not t:
        await event.reply("❌ آیدی/لینک بده.")
        return
    try:
        await bot.ban_member(chat_id=event.chat_id, sender_id=t)
        ck = str(event.chat_id)
        data["banned"].setdefault(ck, []).append(t); save_data(data)
        await event.reply(f"🔨 {t} بن شد.")
    except Exception as e:
        await event.reply(f"❌ {e}")

@bot.on_command(["اخراج", "kick"])
async def cmd_kick(bot, event):
    t = get_target(event.text or "", event)
    if not t:
        await event.reply("❌ آیدی/لینک بده.")
        return
    try:
        await bot.ban_member(chat_id=event.chat_id, sender_id=t)
        await bot.unban_member(chat_id=event.chat_id, sender_id=t)
        await event.reply("👢 اخراج شد.")
    except Exception as e:
        await event.reply(f"❌ {e}")

@bot.on_command(["اخطار", "warn"])
async def cmd_warn(bot, event):
    t = get_target(event.text or "", event)
    if not t:
        await event.reply("❌ آیدی/لینک بده.")
        return
    ck = str(event.chat_id)
    w = data["warns"].setdefault(ck, {}); w[t] = w.get(t, 0) + 1; save_data(data)
    if w[t] >= 3:
        try:
            await bot.ban_member(chat_id=event.chat_id, sender_id=t)
            await event.reply(f"🔨 {t} بن شد (۳ اخطار).")
        except Exception as e:
            await event.reply(f"⚠️ {e}")
    else:
        await event.reply(f"⚠️ اخطار {w[t]}/۳ برای {t}.")

@bot.on_command(["حذف اخطار", "unwarn"])
async def cmd_unwarn(bot, event):
    t = get_target(event.text or "", event)
    if not t:
        await event.reply("❌ آیدی/لینک بده.")
        return
    ck = str(event.chat_id); w = data["warns"].get(ck, {})
    if t in w: del w[t]; save_data(data); await event.reply("✅ پاک شد.")
    else: await event.reply("ℹ️ نداشت.")

@bot.on_command(["قوانین", "rules"])
async def cmd_rules(bot, event):
    ck = str(event.chat_id); r = data["rules"].get(ck)
    await event.reply(f"📜 {r}" if r else "📜 تنظیم نشده.")

@bot.on_command(["تنظیم قوانین", "setrules"])
async def cmd_setrules(bot, event):
    r = (event.text or "").replace("تنظیم قوانین", "").replace("setrules", "").strip()
    if not r: await event.reply("❌ متن بده."); return
    data["rules"][str(event.chat_id)] = r; save_data(data); await event.reply("✅ تنظیم شد.")

@bot.on_command(["تنظیم پیام خوش آمدی", "setwelcome"])
async def cmd_setwelcome(bot, event):
    w = (event.text or "").replace("تنظیم پیام خوش آمدی", "").replace("setwelcome", "").strip()
    if not w: await event.reply("❌ متن بده."); return
    data["welcome"][str(event.chat_id)] = w; save_data(data); await event.reply("✅ تنظیم شد.")

@bot.on_command(["حذف پیام خوش آمدی", "delwelcome"])
async def cmd_delwelcome(bot, event):
    ck = str(event.chat_id)
    if ck in data["welcome"]: del data["welcome"][ck]; save_data(data); await event.reply("✅ حذف شد.")
    else: await event.reply("ℹ️ تنظیم نشده بود.")

@bot.on_command(["قفل کردن گروه", "lock"])
async def cmd_lock(bot, event):
    ck = str(event.chat_id)
    if ck not in data["locked"]: data["locked"].append(ck); save_data(data)
    await event.reply("🔒 قفل شد.")

@bot.on_command(["باز کردن گروه", "unlock"])
async def cmd_unlock(bot, event):
    ck = str(event.chat_id)
    if ck in data["locked"]: data["locked"].remove(ck); save_data(data)
    await event.reply("🔓 باز شد.")

@bot.on_command(["سکوت", "silence"])
async def cmd_silence(bot, event):
    t = get_target(event.text or "", event)
    if not t: await event.reply("❌ بنویس: سکوت u0..."); return
    ck = str(event.chat_id); s = data.setdefault("silenced", {}).setdefault(ck, [])
    if t not in s: s.append(t); save_data(data)
    await event.reply(f"🤐 {t} سکوت شد.")

@bot.on_command(["حذف سکوت", "unsilence"])
async def cmd_unsilence(bot, event):
    t = get_target(event.text or "", event)
    if not t: await event.reply("❌ بنویس: حذف سکوت u0..."); return
    ck = str(event.chat_id); s = data.setdefault("silenced", {}).setdefault(ck, [])
    if t in s: s.remove(t); save_data(data); await event.reply(f"🔊 {t} آزاد شد.")
    else: await event.reply("ℹ️ سکوت نبود.")

# فیلترها
@bot.on_command(["لینک قفل", "locklink"])
async def cmd_locklink(bot, event):
    data.setdefault("filters", {}).setdefault(str(event.chat_id), {})["link"] = True; save_data(data)
    await event.reply("🔗 فیلتر لینک فعال شد.")

@bot.on_command(["لینک باز", "unlocklink"])
async def cmd_unlocklink(bot, event):
    data.setdefault("filters", {}).setdefault(str(event.chat_id), {})["link"] = False; save_data(data)
    await event.reply("🔓 فیلتر لینک غیرفعال شد.")

@bot.on_command(["آیدی قفل", "lockid"])
async def cmd_lockid(bot, event):
    data.setdefault("filters", {}).setdefault(str(event.chat_id), {})["id"] = True; save_data(data)
    await event.reply("🆔 فیلتر آیدی فعال شد.")

@bot.on_command(["آیدی باز", "unlockid"])
async def cmd_unlockid(bot, event):
    data.setdefault("filters", {}).setdefault(str(event.chat_id), {})["id"] = False; save_data(data)
    await event.reply("🔓 فیلتر آیدی غیرفعال شد.")

@bot.on_command(["فحش قفل", "lockbad"])
async def cmd_lockbad(bot, event):
    data.setdefault("filters", {}).setdefault(str(event.chat_id), {})["bad"] = True; save_data(data)
    await event.reply("🤬 فیلتر فحش فعال شد.")

@bot.on_command(["فحش باز", "unlockbad"])
async def cmd_unlockbad(bot, event):
    data.setdefault("filters", {}).setdefault(str(event.chat_id), {})["bad"] = False; save_data(data)
    await event.reply("🔓 فیلتر فحش غیرفعال شد.")

# ادمین
@bot.on_command(["ادمین", "admin"])
async def cmd_admin(bot, event):
    t = get_target(event.text or "", event)
    if not t: await event.reply("❌ ادمین u0..."); return
    ck = str(event.chat_id); a = data.setdefault("admins", {}).setdefault(ck, [])
    if t not in a: a.append(t); save_data(data)
    await event.reply(f"👑 {t} ادمین شد.")

@bot.on_command(["برکنار", "demote"])
async def cmd_demote(bot, event):
    t = get_target(event.text or "", event)
    if not t: await event.reply("❌ برکنار u0..."); return
    ck = str(event.chat_id); a = data.setdefault("admins", {}).setdefault(ck, [])
    if t in a: a.remove(t); save_data(data); await event.reply(f"🚫 {t} برکنار شد.")
    else: await event.reply("ℹ️ ادمین نبود.")

@bot.on_command(["ادمین‌ها", "admins"])
async def cmd_admins(bot, event):
    ck = str(event.chat_id); a = data.get("admins", {}).get(ck, []); o = data.get("owners", {}).get(ck, "—")
    await event.reply(f"👑 مالک: `{o}`\n\n**ادمین‌ها:**\n" + ("\n".join(f"• `{x}`" for x in a) if a else "—"))

@bot.on_command(["پاک", "clear"])
async def cmd_clear(bot, event):
    p = (event.text or "").replace("پاک", "").replace("clear", "").strip().split()
    if not p or not p[0].isdigit(): await event.reply("❌ پاک <۱-۵۰۰>"); return
    n = int(p[0])
    if not 1 <= n <= 500: await event.reply("❌ ۱ تا ۵۰۰."); return
    d = 0
    for i in range(1, n+1):
        tid = event.message_id - i
        if tid <= 0: break
        try: await bot.delete_message(event.chat_id, tid); d += 1
        except: pass
    await event.reply(f"🧹 {d} پیام پاک شد.")

@bot.on_command(["آمار", "stats"])
async def cmd_stats(bot, event):
    ck = str(event.chat_id); w = data["warns"].get(ck, {}); b = data["banned"].get(ck, []); mc = data.get("msg_count", {}).get(ck, {})
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
    )

# ---------- هندلر پیام‌های معمولی (فیلترها) ----------
@bot.on_message()
async def handle_message(bot, event):
    try:
        if not event.text: return
        ck = str(event.chat_id)
        uid = str(event.author_id)
        inc_count(ck, uid)

        # فیلترها
        f = data.get("filters", {}).get(ck, {})
        if f.get("link") and LINK_PATTERN.search(event.text):
            await bot.delete_message(event.chat_id, event.message_id)
            return
        if f.get("id") and ID_PATTERN.search(event.text):
            await bot.delete_message(event.chat_id, event.message_id)
            return
        if f.get("bad") and has_bad(event.text):
            await bot.delete_message(event.chat_id, event.message_id)
            return
        if ck in data.get("locked", []) and not is_owner_or_admin(ck, uid):
            await bot.delete_message(event.chat_id, event.message_id)
            return
        if is_silenced(ck, uid) and not is_owner_or_admin(ck, uid):
            await bot.delete_message(event.chat_id, event.message_id)
            return
    except Exception as e:
        print(f"❌ خطا در handle_message: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_http, daemon=True).start()
    print("✅ ربات فعال شد!")
    bot.run()
