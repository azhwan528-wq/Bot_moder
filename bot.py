import json
import os
import re
import threading
import time
import requests
import random
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

from rubika_bot_api.api import Robot
from rubika_bot_api import filters

TOKEN = os.environ.get("BOT_TOKEN", "")
if not TOKEN:
    print("❌ BOT_TOKEN تنظیم نشده!")
    exit(1)

bot = Robot(token=TOKEN)
DATA_FILE = "bot_data.json"

BAD_WORDS = [
    "کس", "کیر", "کص", "کون", "جنده", "حرومزاده", "حروم", "لاشی",
    "گوه", "گوز", "پدرسگ", "مادرسگ", "سگ", "سگی", "خارکسه", "خارکصه",
    "بی ناموس", "بی شرف", "بی غیرت", "دیوث", "کشکی", "اشغال",
    "احمق", "خنگ", "کودن", "نادان", "ابله", "کثافت", "عن",
]

LINK_PATTERN = re.compile(r'(https?://|www\.|t\.me/|rubika\.ir/|@[A-Za-z0-9_]{5,})', re.IGNORECASE)
ID_PATTERN = re.compile(r'(u0[0-9a-zA-Z]{10,}|@[A-Za-z0-9_]{5,})')

CHALLENGES = ["بهترین خاطره‌ات از دوران مدرسه رو تعریف کن.", "بزرگترین ترست چیه؟", "اگه یه روز نامرئی می‌شدی چیکار می‌کردی؟"]
TRUTH_OR_DARE = ["بزرگترین ترس زندگی‌ات چیه؟", "آخرین باری که گریه کردی کی بود؟", "به نظرت جذاب‌ترین شخص این جمع کیه؟"]
BIOS = ["دنیا محل عبوره، ما هم رهگذریم.", "زندگی زیباست، فقط باید درست ببینیش.", "به خودت ایمان داشته باش."]
DEEP_TRUTH_OR_DARE = ["بزرگ‌ترین راز زندگیت چیه که هیچ‌کس نمی‌دونه؟", "بزرگ‌ترین درسی که زندگی بهت داده چیه؟"]
JOKES = ["به یارو میگن چرا دیر اومدی؟ میگه آخه ساعت ۳ بود، گفتم صبر کنم ۴ بشه!", "به یارو میگن تو مدرسه چی یاد گرفتی؟ میگه یاد گرفتم که تو مدرسه چیزی یاد نمی‌دن!"]

COMMAND_PREFIXES = [
    "start", "راهنما", "help", "ping", "پینگ", "time", "زمان",
    "شناسهمن", "شناسهاو", "شناسه", "id", "مالک", "owner",
    "delete", "حذف", "ban", "بن", "kick", "اخراج",
    "warn", "اخطار", "unwarn", "حذفاخطار", "rules", "قوانین",
    "lock", "قفل", "unlock", "بازکردن", "silence", "سکوت",
    "unsilence", "حذفسکوت", "locklink", "لینکقفل", "unlocklink", "لینکباز",
    "lockid", "آیدیقفل", "unlockid", "آیدیباز", "lockbad", "فحشقفل",
    "unlockbad", "فحشباز", "admins", "adminlist", "ادمینها", "لیستادمین",
    "admin", "ادمین", "demote", "برکنار", "clear", "پاک", "stats", "آمار",
    "چالش", "challenge", "جرئت", "dare", "بیو", "bio",
    "جرئتحقیقت", "deeptruth", "جوک", "joke", "بازی", "game",
]

def normalize(cmd):
    c = cmd.replace(" ", "").replace("\u200c", "").replace("\u200f", "").replace("\u200e", "").strip().lower()
    c = c.replace("ي", "ی").replace("ك", "ک").replace("ة", "ه").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    return c

def is_command_text(ncmd):
    for p in COMMAND_PREFIXES:
        if ncmd.startswith(p):
            return True
    return False

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"rules": {}, "warns": {}, "banned": {}, "welcome": {}, "locked": [], "silenced": {}, "owners": {}, "admins": {}, "msg_count": {}, "filters": {}}

def save_data(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

data = load_data()

def is_group(ck):
    return ck.startswith("c") or ck.startswith("g")

def is_owner(ck, uid):
    return str(data.get("owners", {}).get(ck, "")) == str(uid)

def is_admin(ck, uid):
    return str(uid) in [str(a) for a in data.get("admins", {}).get(ck, [])]

def is_owner_or_admin(ck, uid):
    return is_owner(ck, uid) or is_admin(ck, uid)

def is_silenced(ck, uid):
    return str(uid) in [str(u) for u in data.get("silenced", {}).get(ck, [])]

def has_bad(text):
    return any(w.lower() in text.lower() for w in BAD_WORDS)

def inc_count(ck, uid):
    mc = data.setdefault("msg_count", {}).setdefault(ck, {})
    mc[str(uid)] = mc.get(str(uid), 0) + 1
    save_data(data)

def get_target(cmd_text, message):
    if getattr(message, 'reply_to_message_id', None):
        try:
            url = f"https://botapi.rubika.ir/v3/{TOKEN}/getMessage"
            r = requests.post(url, json={"chat_id": message.chat_id, "message_id": message.reply_to_message_id}, timeout=8)
            if r.status_code == 200:
                res = r.json()
                if res.get("status") == "OK":
                    sid = res.get("data", {}).get("message", {}).get("sender_id")
                    if sid: return str(sid)
        except Exception:
            pass
    m = re.search(r'rubika\.ir/([uc]0[0-9a-zA-Z]{10,})', cmd_text or "")
    if m: return m.group(1)
    m = re.search(r'\b([uc]0[0-9a-zA-Z]{10,})\b', cmd_text or "")
    if m: return m.group(1)
    return None

HELP = """📚 **راهنمای ربات**

👑 **مدیریت:**
🔹 مالک / شناسه / لیست ادمین / ادمین / برکنار

⚙️ **تنظیمات:**
🔹 قوانین / تنظیم قوانین <متن>
🔹 تنظیم پیام خوش آمدی <متن> / حذف پیام خوش آمدی
🔹 قفل کردن گروه / باز کردن گروه
🔹 لینک قفل / لینک باز / آیدی قفل / آیدی باز / فحش قفل / فحش باز

🛡️ **مدیریت اعضا:**
🔹 حذف / بن / اخراج / اخطار / حذف اخطار / سکوت / حذف سکوت
🔹 پاک <تعداد> — ۱ تا ۵۰۰

🎮 **سرگرمی:**
🔹 چالش / جرئت / بیو / جرئت حقیقت / جوک / بازی

ℹ️ **عمومی:**
🔹 آمار / ping / time
"""

class HC(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
    def log_message(self, *a): pass

def run_http():
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 8080))), HC).serve_forever()

def keep_alive():
    url = os.environ.get("RENDER_EXTERNAL_URL", "")
    if not url:
        port = os.environ.get("PORT", 8080)
        url = f"http://localhost:{port}"
    print(f"💓 Keep-alive فعال شد. URL: {url}")
    time.sleep(30)
    while True:
        try:
            r = requests.get(url, timeout=15)
            print(f"💓 Ping {url} → {r.status_code}")
        except Exception as e:
            print(f"⚠️ Ping failed: {e}")
        time.sleep(300)

@bot.on_message()
async def handle_all(robot_client, message):
    try:
        if not message.text:
            return
        raw = message.text.strip()
        cmd = raw.lstrip("/")
        ncmd = normalize(cmd)
        ck = str(message.chat_id)
        uid = str(message.sender_id)

        inc_count(ck, uid)

        is_cmd = is_command_text(ncmd)

        if is_group(ck) and not is_cmd and not is_owner_or_admin(ck, uid):
            f = data.get("filters", {}).get(ck, {})
            if f.get("link") and LINK_PATTERN.search(cmd):
                await bot.delete_message(message.chat_id, message.message_id); return
            if f.get("id") and ID_PATTERN.search(cmd):
                await bot.delete_message(message.chat_id, message.message_id); return
            if f.get("bad") and has_bad(cmd):
                await bot.delete_message(message.chat_id, message.message_id); return
            if ck in data.get("locked", []):
                await bot.delete_message(message.chat_id, message.message_id); return
            if is_silenced(ck, uid):
                await bot.delete_message(message.chat_id, message.message_id); return

        if ncmd in ("مالک", "owner"):
            owner = data.get("owners", {}).get(ck)
            await message.reply(f"👑 مالک گروه:\n`{owner}`" if owner else "ℹ️ هنوز مالکی تنظیم نشده.")
            return

        if ncmd in ("start", "راهنما", "help"):
            if is_group(ck) and not data.get("owners", {}).get(ck):
                data.setdefault("owners", {})[ck] = uid
                save_data(data)
                await message.reply(f"✅ شما به عنوان مالک گروه تنظیم شدید: `{uid}`")
            await message.reply(HELP)
            return

        if ncmd in ("ping", "پینگ"):
            start = time.time()
            await message.reply("🏓 ...")
            elapsed = int((time.time() - start) * 1000)
            await message.reply(f"🏓 Pong! {elapsed}ms")
            return

        if ncmd in ("time", "زمان"):
            await message.reply(f"🕐 {datetime.now():%Y/%m/%d - %H:%M:%S}")
            return

        if ncmd in ("شناسهمن", "myid"):
            await message.reply(f"🆔 شناسه شما: `{uid}`")
            return

        if ncmd in ("شناسهاو", "theirid"):
            t = get_target(cmd, message)
            await message.reply(f"🆔 شناسه: `{t}`" if t and t != uid else "❌ روی پیام کاربر ریپلای کن.")
            return

        if ncmd in ("شناسه", "id"):
            if getattr(message, 'reply_to_message_id', None):
                t = get_target(cmd, message)
                if t and t != uid:
                    await message.reply(f"🆔 شناسه: `{t}`"); return
            await message.reply(f"🆔 شناسه شما: `{uid}`")
            return

        if ncmd in ("delete", "حذف"):
            if not message.reply_to_message_id:
                await message.reply("❌ روی یک پیام ریپلای کن."); return
            try:
                await bot.delete_message(message.chat_id, message.reply_to_message_id)
                await message.reply("✅ پیام حذف شد.")
            except Exception as e:
                await message.reply(f"❌ {e}")
            return

        if ncmd.startswith("ban") or ncmd.startswith("بن"):
            t = get_target(cmd, message)
            if not t:
                await message.reply("❌ ریپلای کن یا آیدی/لینک بده."); return
            if is_owner_or_admin(ck, t):
                await message.reply("⚠️ نمی‌توان مالک یا ادمین را بن کرد."); return
            try:
                await bot.ban_chat_member(message.chat_id, t)
                data["banned"].setdefault(ck, []).append(t); save_data(data)
                await message.reply(f"🔨 {t} بن شد.")
            except Exception as e:
                await message.reply(f"❌ {e}")
            return

        if ncmd.startswith("kick") or ncmd.startswith("اخراج"):
            t = get_target(cmd, message)
            if not t:
                await message.reply("❌ ریپلای کن یا آیدی/لینک بده."); return
            if is_owner_or_admin(ck, t):
                await message.reply("⚠️ نمی‌توان مالک یا ادمین را اخراج کرد."); return
            try:
                await bot.ban_chat_member(message.chat_id, t)
                await bot.unban_chat_member(message.chat_id, t)
                await message.reply("👢 کاربر اخراج شد.")
            except Exception as e:
                await message.reply(f"❌ {e}")
            return

        if ncmd.startswith("warn") or ncmd.startswith("اخطار"):
            t = get_target(cmd, message)
            if not t:
                await message.reply("❌ ریپلای کن یا آیدی/لینک بده."); return
            if is_owner_or_admin(ck, t):
                await message.reply("⚠️ نمی‌توان به مالک یا ادمین اخطار داد."); return
            w = data["warns"].setdefault(ck, {}); w[t] = w.get(t, 0) + 1; save_data(data)
            if w[t] >= 3:
                try:
                    await bot.ban_chat_member(message.chat_id, t)
                    await message.reply(f"🔨 {t} بن شد (۳ اخطار).")
                except Exception as e:
                    await message.reply(f"⚠️ {e}")
            else:
                await message.reply(f"⚠️ اخطار {w[t]}/۳ برای {t}.")
            return

        if ncmd.startswith("unwarn") or ncmd.startswith("حذفاخطار"):
            t = get_target(cmd, message)
            if not t:
                await message.reply("❌ ریپلای کن یا آیدی/لینک بده."); return
            w = data["warns"].get(ck, {})
            if t in w: del w[t]; save_data(data); await message.reply("✅ اخطار پاک شد.")
            else: await message.reply("ℹ️ اخطاری نداشت.")
            return

        if ncmd in ("rules", "قوانین"):
            r = data["rules"].get(ck)
            await message.reply(f"📜 {r}" if r else "📜 تنظیم نشده.")
            return
        if ncmd.startswith("setrules") or ncmd.startswith("تنظیمقوانین"):
            r = cmd.replace("setrules", "").replace("تنظیم قوانین", "").strip()
            if not r: await message.reply("❌ متن بده."); return
            data["rules"][ck] = r; save_data(data); await message.reply("✅ تنظیم شد.")
            return

        if ncmd.startswith("setwelcome") or ncmd.startswith("تنظیمپیامخوشآمدی"):
            w = cmd.replace("setwelcome", "").replace("تنظیم پیام خوش آمدی", "").strip()
            if not w: await message.reply("❌ متن بده."); return
            data["welcome"][ck] = w; save_data(data); await message.reply("✅ تنظیم شد.")
            return
        if ncmd in ("delwelcome", "حذفپیامخوشآمدی"):
            if ck in data["welcome"]: del data["welcome"][ck]; save_data(data); await message.reply("✅ حذف شد.")
            else: await message.reply("ℹ️ تنظیم نشده بود.")
            return

        if ncmd in ("lock", "قفلکردنگروه", "قفل"):
            if ck not in data["locked"]: data["locked"].append(ck); save_data(data)
            await message.reply("🔒 قفل شد. (ادمین‌ها و مالک معاف هستند)")
            return
        if ncmd in ("unlock", "بازکردنگروه", "بازکردن"):
            if ck in data["locked"]: data["locked"].remove(ck); save_data(data)
            await message.reply("🔓 باز شد.")
            return

        if ncmd.startswith("unsilence") or ncmd.startswith("حذفسکوت"):
            t = get_target(cmd, message)
            if not t: await message.reply("❌ ریپلای کن یا بنویس: حذف سکوت u0..."); return
            s = data.setdefault("silenced", {}).setdefault(ck, [])
            if t in s: s.remove(t); save_data(data); await message.reply(f"🔊 {t} آزاد شد.")
            else: await message.reply("ℹ️ سکوت نبود.")
            return
        if ncmd.startswith("silence") or ncmd.startswith("سکوت"):
            t = get_target(cmd, message)
            if not t: await message.reply("❌ ریپلای کن یا بنویس: سکوت u0..."); return
            if is_owner_or_admin(ck, t):
                await message.reply("⚠️ نمی‌توان مالک یا ادمین را سکوت کرد."); return
            s = data.setdefault("silenced", {}).setdefault(ck, [])
            if t not in s: s.append(t); save_data(data)
            await message.reply(f"🤐 {t} سکوت شد.")
            return

        if ncmd in ("locklink", "لینکقفل"):
            data.setdefault("filters", {}).setdefault(ck, {})["link"] = True; save_data(data); await message.reply("🔗 فیلتر لینک فعال شد."); return
        if ncmd in ("unlocklink", "لینکباز"):
            data.setdefault("filters", {}).setdefault(ck, {})["link"] = False; save_data(data); await message.reply("🔓 فیلتر لینک غیرفعال شد."); return
        if ncmd in ("lockid", "آیدیقفل"):
            data.setdefault("filters", {}).setdefault(ck, {})["id"] = True; save_data(data); await message.reply("🆔 فیلتر آیدی فعال شد."); return
        if ncmd in ("unlockid", "آیدیباز"):
            data.setdefault("filters", {}).setdefault(ck, {})["id"] = False; save_data(data); await message.reply("🔓 فیلتر آیدی غیرفعال شد."); return
        if ncmd in ("lockbad", "فحشقفل"):
            data.setdefault("filters", {}).setdefault(ck, {})["bad"] = True; save_data(data); await message.reply("🤬 فیلتر فحش فعال شد."); return
        if ncmd in ("unlockbad", "فحشباز"):
            data.setdefault("filters", {}).setdefault(ck, {})["bad"] = False; save_data(data); await message.reply("🔓 فیلتر فحش غیرفعال شد."); return

        if ncmd in ("admins", "adminlist") or "لیستادمین" in ncmd or (ncmd.startswith("ادمین") and ncmd.endswith("ها")) or ncmd == "ادمینها":
            a = data.get("admins", {}).get(ck, [])
            o = data.get("owners", {}).get(ck, "—")
            msg = f"👑 مالک: `{o}`\n\n**ادمین‌ها:**\n"
            msg += "\n".join(f"• `{x}`" for x in a) if a else "—"
            await message.reply(msg)
            return

        if ncmd.startswith("admin") or ncmd.startswith("ادمین"):
            if not is_group(ck):
                await message.reply("❌ این دستور فقط در گروه کار می‌کند."); return
            t = get_target(cmd, message)
            if not t:
                await message.reply("❌ ریپلای کن یا بنویس: ادمین u0..."); return
            a = data.setdefault("admins", {}).setdefault(ck, [])
            if t in a:
                await message.reply(f"ℹ️ {t} از قبل ادمین است.")
            else:
                a.append(t); save_data(data)
                await message.reply(f"👑 {t} ادمین شد. (معاف از تمام محدودیت‌ها)")
            return

        if ncmd.startswith("demote") or ncmd.startswith("برکنار"):
            t = get_target(cmd, message)
            if not t:
                await message.reply("❌ ریپلای کن یا بنویس: برکنار u0..."); return
            a = data.setdefault("admins", {}).setdefault(ck, [])
            if t in a: a.remove(t); save_data(data); await message.reply(f"🚫 {t} برکنار شد.")
            else: await message.reply("ℹ️ ادمین نبود.")
            return

        if ncmd.startswith("clear") or ncmd.startswith("پاک"):
            p = cmd.replace("clear", "").replace("پاک", "").strip().split()
            if not p or not p[0].isdigit():
                await message.reply("❌ پاک <۱-۵۰۰>"); return
            n = int(p[0])
            if not 1 <= n <= 500:
                await message.reply("❌ ۱ تا ۵۰۰."); return
            d = 0
            for i in range(1, n + 1):
                tid = message.message_id - i
                if tid <= 0: break
                try: await bot.delete_message(message.chat_id, tid); d += 1
                except: pass
            await message.reply(f"🧹 {d} پیام پاک شد.")
            return

        if ncmd in ("stats", "آمار"):
            w = data["warns"].get(ck, {}); b = data["banned"].get(ck, []); mc = data.get("msg_count", {}).get(ck, {})
            top = sorted(mc.items(), key=lambda x: -x[1])[:10]
            top_s = "\n".join(f"{i}. `{u}` — {c} پیام" for i, (u, c) in enumerate(top, 1)) or "—"
            f = data.get("filters", {}).get(ck, {})
            await message.reply(
                f"📊 **آمار گروه**\n\n"
                f"👤 مالک: `{data.get('owners',{}).get(ck,'—')}`\n"
                f"👑 ادمین‌ها: {len(data.get('admins',{}).get(ck,[]))}\n"
                f"🔒 گروه: {'بسته' if ck in data.get('locked',[]) else 'باز'}\n"
                f"فیلترها: 🔗{'✅' if f.get('link') else '❌'} 🆔{'✅' if f.get('id') else '❌'} 🤬{'✅' if f.get('bad') else '❌'}\n"
                f"🤐 سکوت: {len(data.get('silenced',{}).get(ck,[]))} | 👥 بن: {len(b)} | ⚠️ اخطار: {len(w)}\n"
                f"💬 کل: {sum(mc.values())}\n\n"
                f"🏆 **۱۰ نفر اول:**\n{top_s}"
            )
            return

        if ncmd in ("چالش", "challenge"):
            await message.reply(f"🎯 **چالش:**\n\n{random.choice(CHALLENGES)}"); return
        if ncmd in ("جرئت", "dare", "truthordare"):
            await message.reply(f"🎲 **جرئت یا حقیقت:**\n\n{random.choice(TRUTH_OR_DARE)}"); return
        if ncmd in ("بیو", "bio"):
            await message.reply(f"✨ **بیو:**\n\n{random.choice(BIOS)}"); return
        if ncmd in ("جرئتحقیقت", "deeptruth"):
            await message.reply(f"💭 **جرئت حقیقت (عمیق):**\n\n{random.choice(DEEP_TRUTH_OR_DARE)}"); return
        if ncmd in ("جوک", "joke"):
            await message.reply(f"😂 **جوک:**\n\n{random.choice(JOKES)}"); return
        if ncmd in ("بازی", "game", "games"):
            await message.reply(
                "🎮 **بازی‌های گروهی:**\n\n"
                "1. حدس کلمه\n2. بیست سوالی\n3. اسم فامیل\n"
                "4. جرئت یا حقیقت (دستور «جرئت»)\n5. چالش (دستور «چالش»)\n"
                "6. داستان‌سازی\n7. پانتومیم\n8. حدس آهنگ\n\n"
                "🎯 **بازی‌های آنلاین:**\n"
                "برو به https://me-chat-1w2h.onrender.com/games.html"
            ); return

    except Exception as e:
        print(f"❌ خطا: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_http, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()
    print("✅ ربات فعال شد!")
    print("📋 دستورات: حذف، بن، اخراج، اخطار، شناسه، قوانین، خوش‌آمد، قفل، سکوت، ادمین، پاک، آمار، چالش، جرئت، بیو، جرئت حقیقت، جوک، بازی")
    asyncio.run(bot.run())
