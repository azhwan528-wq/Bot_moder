import json
import os
import re
import threading
import time
import aiohttp
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

from rubka import Robot, Message

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

def inc_count(ck, uid):
    mc = data.setdefault("msg_count", {}).setdefault(ck, {})
    mc[str(uid)] = mc.get(str(uid), 0) + 1
    save_data(data)

async def get_sender_id_from_reply(chat_id: str, message_id: str):
    """استخراج sender_id از پیام ریپلای‌شده با API خام روبیکا"""
    url = f"https://botapi.rubika.ir/v3/{TOKEN}/getMessage"
    payload = {"chat_id": chat_id, "message_id": message_id}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=10) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("status") == "OK":
                        msg = result.get("data", {}).get("message", {})
                        return str(msg.get("sender_id"))
    except Exception as e:
        print(f"⚠️ خطا در getMessage: {e}")
    return None

async def get_target(cmd_text: str, message: Message):
    """استخراج آیدی هدف از متن، لینک، یا ریپلای"""
    # ۱. از ریپلای (با API خام)
    if getattr(message, 'reply_to_message_id', None):
        t = await get_sender_id_from_reply(message.chat_id, message.reply_to_message_id)
        if t:
            return t

    # ۲. از لینک پروفایل
    m = re.search(r'rubika\.ir/([uc]0[0-9a-zA-Z]{10,})', cmd_text or "")
    if m: return m.group(1)

    # ۳. از آیدی مستقیم
    m = re.search(r'\b([uc]0[0-9a-zA-Z]{10,})\b', cmd_text or "")
    if m: return m.group(1)

    return None

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
🔹 ban / بن — با ریپلای یا آیدی
🔹 kick / اخراج — با ریپلای یا آیدی
🔹 warn / اخطار — با ریپلای یا آیدی
🔹 unwarn / حذف اخطار — با ریپلای یا آیدی
🔹 silence / سکوت — با ریپلای یا آیدی
🔹 unsilence / حذف سکوت — با ریپلای یا آیدی
🔹 admin / ادمین — با ریپلای یا آیدی
🔹 demote / برکنار — با ریپلای یا آیدی
🔹 clear / پاک <تعداد> — ۱ تا ۵۰۰
🔹 locklink / لینک قفل — فیلتر لینک
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
@bot.on_message()
async def handle_all(bot: Robot, message: Message):
    try:
        if not message.text: return
        raw = message.text.strip()
        cmd = raw.lstrip("/")
        ck = str(message.chat_id)
        uid = str(message.sender_id)

        inc_count(ck, uid)

        # فیلترها (فقط در گروه)
        if ck.startswith("c") or ck.startswith("g"):
            f = data.get("filters", {}).get(ck, {})
            if f.get("link") and LINK_PATTERN.search(cmd):
                await bot.delete_message(message.chat_id, message.message_id); return
            if f.get("id") and ID_PATTERN.search(cmd):
                await bot.delete_message(message.chat_id, message.message_id); return
            if f.get("bad") and has_bad(cmd):
                await bot.delete_message(message.chat_id, message.message_id); return
            if ck in data.get("locked", []) and not is_owner_or_admin(ck, uid):
                await bot.delete_message(message.chat_id, message.message_id); return
            if is_silenced(ck, uid) and not is_owner_or_admin(ck, uid):
                await bot.delete_message(message.chat_id, message.message_id); return

        # ---------- دستورات ----------
        if cmd in ("start", "راهنما", "help"):
            await message.reply(HELP); return

        if cmd in ("ping", "پینگ"):
            start = time.time()
            await message.reply("🏓 ...")
            elapsed = int((time.time() - start) * 1000)
            await message.reply(f"🏓 Pong! {elapsed}ms")
            return

        if cmd in ("time", "زمان"):
            await message.reply(f"🕐 {datetime.now():%Y/%m/%d - %H:%M:%S}"); return

        if cmd in ("setowner", "ثبت مالک"):
            if ck not in data.get("owners", {}):
                data["owners"][ck] = uid; save_data(data)
                await message.reply(f"✅ مالک: `{uid}`")
            else:
                await message.reply(f"ℹ️ مالک: `{data['owners'][ck]}`")
            return

        if cmd in ("id", "شناسه"):
            t = await get_target(cmd, message)
            await message.reply(f"🆔 `{t or uid}`"); return

        if cmd in ("delete", "حذف"):
            if not message.reply_to_message_id:
                await message.reply("❌ روی یک پیام ریپلای کن.")
                return
            try:
                await bot.delete_message(message.chat_id, message.reply_to_message_id)
                await message.reply("✅ پیام حذف شد.")
            except Exception as e:
                await message.reply(f"❌ {e}")
            return

        if cmd.startswith("ban") or cmd.startswith("بن"):
            t = await get_target(cmd, message)
            if not t:
                await message.reply("❌ ریپلای کن یا آیدی/لینک بده."); return
            try:
                await bot.ban_member(chat_id=message.chat_id, sender_id=t)
                data["banned"].setdefault(ck, []).append(t); save_data(data)
                await message.reply(f"🔨 {t} بن شد.")
            except Exception as e:
                await message.reply(f"❌ {e}")
            return

        if cmd.startswith("kick") or cmd.startswith("اخراج"):
            t = await get_target(cmd, message)
            if not t:
                await message.reply("❌ ریپلای کن یا آیدی/لینک بده."); return
            try:
                await bot.ban_member(chat_id=message.chat_id, sender_id=t)
                await bot.unban_member(chat_id=message.chat_id, sender_id=t)
                await message.reply("👢 کاربر اخراج شد.")
            except Exception as e:
                await message.reply(f"❌ {e}")
            return

        if cmd.startswith("warn") or cmd.startswith("اخطار"):
            t = await get_target(cmd, message)
            if not t:
                await message.reply("❌ ریپلای کن یا آیدی/لینک بده."); return
            w = data["warns"].setdefault(ck, {}); w[t] = w.get(t, 0) + 1; save_data(data)
            if w[t] >= 3:
                try:
                    await bot.ban_member(chat_id=message.chat_id, sender_id=t)
                    await message.reply(f"🔨 {t} بن شد (۳ اخطار).")
                except Exception as e:
                    await message.reply(f"⚠️ {e}")
            else:
                await message.reply(f"⚠️ اخطار {w[t]}/۳ برای {t}.")
            return

        if cmd.startswith("unwarn") or cmd.startswith("حذف اخطار"):
            t = await get_target(cmd, message)
            if not t:
                await message.reply("❌ ریپلای کن یا آیدی/لینک بده."); return
            w = data["warns"].get(ck, {})
            if t in w: del w[t]; save_data(data); await message.reply("✅ اخطار پاک شد.")
            else: await message.reply("ℹ️ اخطاری نداشت.")
            return

        if cmd in ("rules", "قوانین"):
            r = data["rules"].get(ck)
            await message.reply(f"📜 {r}" if r else "📜 تنظیم نشده."); return

        if cmd.startswith("setrules") or cmd.startswith("تنظیم قوانین"):
            r = cmd.replace("setrules", "").replace("تنظیم قوانین", "").strip()
            if not r: await message.reply("❌ متن بده."); return
            data["rules"][ck] = r; save_data(data); await message.reply("✅ تنظیم شد."); return

        if cmd.startswith("setwelcome") or cmd.startswith("تنظیم پیام خوش آمدی"):
            w = cmd.replace("setwelcome", "").replace("تنظیم پیام خوش آمدی", "").strip()
            if not w: await message.reply("❌ متن بده."); return
            data["welcome"][ck] = w; save_data(data); await message.reply("✅ تنظیم شد."); return

        if cmd in ("delwelcome", "حذف پیام خوش آمدی"):
            if ck in data["welcome"]: del data["welcome"][ck]; save_data(data); await message.reply("✅ حذف شد.")
            else: await message.reply("ℹ️ تنظیم نشده بود.")
            return

        if cmd in ("lock", "قفل کردن گروه"):
            if ck not in data["locked"]: data["locked"].append(ck); save_data(data)
            await message.reply("🔒 قفل شد."); return

        if cmd in ("unlock", "باز کردن گروه"):
            if ck in data["locked"]: data["locked"].remove(ck); save_data(data)
            await message.reply("🔓 باز شد."); return

        if cmd.startswith("silence") or cmd.startswith("سکوت"):
            t = await get_target(cmd, message)
            if not t: await message.reply("❌ ریپلای کن یا بنویس: سکوت u0..."); return
            s = data.setdefault("silenced", {}).setdefault(ck, [])
            if t not in s: s.append(t); save_data(data)
            await message.reply(f"🤐 {t} سکوت شد."); return

        if cmd.startswith("unsilence") or cmd.startswith("حذف سکوت"):
            t = await get_target(cmd, message)
            if not t: await message.reply("❌ ریپلای کن یا بنویس: حذف سکوت u0..."); return
            s = data.setdefault("silenced", {}).setdefault(ck, [])
            if t in s: s.remove(t); save_data(data); await message.reply(f"🔊 {t} آزاد شد.")
            else: await message.reply("ℹ️ سکوت نبود.")
            return

        if cmd in ("locklink", "لینک قفل"):
            data.setdefault("filters", {}).setdefault(ck, {})["link"] = True; save_data(data); await message.reply("🔗 فیلتر لینک فعال شد."); return
        if cmd in ("unlocklink", "لینک باز"):
            data.setdefault("filters", {}).setdefault(ck, {})["link"] = False; save_data(data); await message.reply("🔓 فیلتر لینک غیرفعال شد."); return
        if cmd in ("lockid", "آیدی قفل"):
            data.setdefault("filters", {}).setdefault(ck, {})["id"] = True; save_data(data); await message.reply("🆔 فیلتر آیدی فعال شد."); return
        if cmd in ("unlockid", "آیدی باز"):
            data.setdefault("filters", {}).setdefault(ck, {})["id"] = False; save_data(data); await message.reply("🔓 فیلتر آیدی غیرفعال شد."); return
        if cmd in ("lockbad", "فحش قفل"):
            data.setdefault("filters", {}).setdefault(ck, {})["bad"] = True; save_data(data); await message.reply("🤬 فیلتر فحش فعال شد."); return
        if cmd in ("unlockbad", "فحش باز"):
            data.setdefault("filters", {}).setdefault(ck, {})["bad"] = False; save_data(data); await message.reply("🔓 فیلتر فحش غیرفعال شد."); return

        if (cmd.startswith("admin") and not cmd.startswith("admins")) or (cmd.startswith("ادمین") and not cmd.startswith("ادمین‌ها")):
            t = await get_target(cmd, message)
            if not t: await message.reply("❌ ریپلای کن یا بنویس: ادمین u0..."); return
            a = data.setdefault("admins", {}).setdefault(ck, [])
            if t not in a: a.append(t); save_data(data)
            await message.reply(f"👑 {t} ادمین شد."); return

        if cmd.startswith("demote") or cmd.startswith("برکنار"):
            t = await get_target(cmd, message)
            if not t: await message.reply("❌ ریپلای کن یا بنویس: برکنار u0..."); return
            a = data.setdefault("admins", {}).setdefault(ck, [])
            if t in a: a.remove(t); save_data(data); await message.reply(f"🚫 {t} برکنار شد.")
            else: await message.reply("ℹ️ ادمین نبود.")
            return

        if cmd in ("admins", "ادمین‌ها"):
            a = data.get("admins", {}).get(ck, []); o = data.get("owners", {}).get(ck, "—")
            await message.reply(f"👑 مالک: `{o}`\n\n**ادمین‌ها:**\n" + ("\n".join(f"• `{x}`" for x in a) if a else "—")); return

        if cmd.startswith("clear") or cmd.startswith("پاک"):
            p = cmd.replace("clear", "").replace("پاک", "").strip().split()
            if not p or not p[0].isdigit(): await message.reply("❌ پاک <۱-۵۰۰>"); return
            n = int(p[0])
            if not 1 <= n <= 500: await message.reply("❌ ۱ تا ۵۰۰."); return
            d = 0
            for i in range(1, n+1):
                tid = message.message_id - i
                if tid <= 0: break
                try: await bot.delete_message(message.chat_id, tid); d += 1
                except: pass
            await message.reply(f"🧹 {d} پیام پاک شد."); return

        if cmd in ("stats", "آمار"):
            w = data["warns"].get(ck, {}); b = data["banned"].get(ck, []); mc = data.get("msg_count", {}).get(ck, {})
            top = sorted(mc.items(), key=lambda x: -x[1])[:10]
            top_s = "\n".join(f"{i}. [{u}](https://rubika.ir/{u}) — {c} پیام" for i, (u, c) in enumerate(top, 1)) or "—"
            f = data.get("filters", {}).get(ck, {})
            await message.reply(
                f"📊 **آمار**\n👤 مالک: `{data.get('owners',{}).get(ck,'—')}`\n"
                f"👑 ادمین‌ها: {len(data.get('admins',{}).get(ck,[]))}\n"
                f"🔒 گروه: {'بسته' if ck in data.get('locked',[]) else 'باز'}\n"
                f"فیلترها: 🔗{'✅' if f.get('link') else '❌'} 🆔{'✅' if f.get('id') else '❌'} 🤬{'✅' if f.get('bad') else '❌'}\n"
                f"🤐 سکوت: {len(data.get('silenced',{}).get(ck,[]))} | 👥 بن: {len(b)} | ⚠️ اخطار: {len(w)}\n"
                f"💬 کل: {sum(mc.values())}\n\n🏆 **۱۰ نفر اول:**\n{top_s}"
            ); return

    except Exception as e:
        print(f"❌ خطا: {e}")

# ---------- اجرا ----------
if __name__ == "__main__":
    threading.Thread(target=run_http, daemon=True).start()
    print("✅ ربات فعال شد!")
    bot.run()
