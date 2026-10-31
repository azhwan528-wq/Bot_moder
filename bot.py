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

# ---------- لیست فحش (گسترش‌یافته) ----------
BAD_WORDS = [
    "کس", "کیر", "کص", "کون", "جنده", "حرومزاده", "حروم", "لاشی",
    "گوه", "گوز", "پدرسگ", "مادرسگ", "سگ", "سگی", "خارکسه", "خارکصه",
    "بی ناموس", "بی شرف", "بی غیرت", "دیوث", "کشکی", "اشغال",
    "احمق", "خنگ", "کودن", "نادان", "ابله", "احمق", "کثافت",
    "fuck", "shit", "bitch", "ass", "dick", "pussy", "cunt",
    "fck", "fuk", "stfu", "bastard", "whore", "slut",
]

LINK_PATTERN = re.compile(
    r'(https?://|www\.|t\.me/|telegram\.me/|rubika\.ir/|@[A-Za-z0-9_]{5,})',
    re.IGNORECASE
)

ID_PATTERN = re.compile(r'(u0[0-9a-zA-Z]{10,}|@[A-Za-z0-9_]{5,})')

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "rules": {},
        "warns": {},
        "banned": {},
        "welcome": {},
        "locked": [],
        "silenced": {},
        "owners": {},
        "admins": {},      # {chat_key: [user_id, ...]}
        "msg_count": {},
        "filters": {}
    }

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

def get_chat_key(chat_id):
    return str(chat_id)

def get_filter_state(chat_key, key):
    return data.setdefault("filters", {}).setdefault(chat_key, {}).get(key, False)

def set_filter_state(chat_key, key, value):
    data.setdefault("filters", {}).setdefault(chat_key, {})[key] = value
    save_data(data)

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
    return None

def is_owner(chat_key, user_id):
    owner = data.get("owners", {}).get(chat_key)
    return owner and str(owner) == str(user_id)

def is_admin(chat_key, user_id):
    admins = data.get("admins", {}).get(chat_key, [])
    return str(user_id) in [str(a) for a in admins]

def is_owner_or_admin(chat_key, user_id):
    if is_owner(chat_key, user_id):
        return True
    if is_admin(chat_key, user_id):
        return True
    # اگر مالک ثبت نشده، اولین نفر را مالک کن
    owner = data.get("owners", {}).get(chat_key)
    if not owner:
        data.setdefault("owners", {})[chat_key] = str(user_id)
        save_data(data)
        return True
    return False

def is_silenced(chat_key, user_id):
    silenced = data.get("silenced", {}).get(chat_key, [])
    return str(user_id) in [str(u) for u in silenced]

def contains_bad_word(text):
    text_lower = text.lower()
    for word in BAD_WORDS:
        if word.lower() in text_lower:
            return True
    return False

def contains_link(text):
    return bool(LINK_PATTERN.search(text))

def contains_id(text):
    return bool(ID_PATTERN.search(text))

HELP_TEXT = """📚 **راهنمای ربات مدیریت گروه**

🔹 **حذف** — با ریپلای روی پیام
🔹 **بن** — با ریپلای یا آیدی (u0...)
🔹 **اخراج** — با ریپلای یا آیدی
🔹 **اخطار** — با ریپلای یا آیدی
🔹 **حذف اخطار** — با ریپلای یا آیدی
🔹 **شناسه** — نمایش شناسه کاربر
🔹 **قوانین** — نمایش قوانین
🔹 **تنظیم قوانین <متن>** — تعیین قوانین
🔹 **تنظیم پیام خوش آمدی <متن>** — تنظیم خوش‌آمد
🔹 **حذف پیام خوش آمدی** — حذف خوش‌آمد
🔹 **قفل کردن گروه** / **باز کردن گروه**
🔹 **سکوت u0...** / **حذف سکوت u0...** — با آیدی
🔹 **پاک <تعداد>** — ۱ تا ۵۰۰
🔹 **لینک قفل** / **لینک باز**
🔹 **آیدی قفل** / **آیدی باز**
🔹 **فحش قفل** / **فحش باز**
🔹 **ادمین u0...** — افزودن ادمین
🔹 **برکنار u0...** — حذف ادمین
🔹 **ادمین‌ها** — لیست ادمین‌ها
🔹 **زمان** / **پینگ** / **آمار** / **راهنما**
"""

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

    inc_msg_count(chat_key, sender)

    # فیلترهای خودکار
    should_delete = False
    reason = ""

    if get_filter_state(chat_key, "link") and contains_link(text):
        should_delete = True
        reason = "لینک"

    if get_filter_state(chat_key, "id") and contains_id(text):
        should_delete = True
        reason = "آیدی"

    if get_filter_state(chat_key, "bad") and contains_bad_word(text):
        should_delete = True
        reason = "فحش"

    if chat_key in data.get("locked", []) and not is_owner_or_admin(chat_key, sender):
        should_delete = True
        reason = "گروه قفل است"

    if is_silenced(chat_key, sender) and not is_owner_or_admin(chat_key, sender):
        should_delete = True
        reason = "کاربر در سکوت است"

    if should_delete:
        try:
            await client.delete_message(chat_id, msg_id)
            if reason in ("لینک", "آیدی", "فحش"):
                try:
                    warn_msg = await update.reply(f"⚠️ پیام به دلیل «{reason}» حذف شد.")
                    import asyncio
                    await asyncio.sleep(5)
                    try:
                        await client.delete_message(chat_id, warn_msg.message_id)
                    except Exception:
                        pass
                except Exception:
                    pass
        except Exception:
            pass
        return

    # راهنما
    if text in ("راهنما", "help", "/help", "/start"):
        await update.reply(HELP_TEXT)
        return

    # پینگ
    if text in ("پینگ", "/ping"):
        await update.reply("🏓 پونگ! ربات فعال است.")
        return

    # زمان
    if text in ("زمان", "/time"):
        now = datetime.now().strftime("%Y/%m/%d - %H:%M:%S")
        await update.reply(f"🕐 {now}")
        return

    # ثبت مالک
    if text in ("ثبت مالک", "/setowner"):
        if chat_key not in data.get("owners", {}):
            data.setdefault("owners", {})[chat_key] = sender
            save_data(data)
            await update.reply(f"✅ شما به عنوان مالک گروه ثبت شدید: `{sender}`")
        else:
            current = data["owners"][chat_key]
            await update.reply(f"ℹ️ مالک فعلی: `{current}`")
        return

    # شناسه
    if text in ("شناسه", "/id"):
        target = get_target_from_command("", update)
        if target:
            await update.reply(f"🆔 شناسه: `{target}`")
        else:
            await update.reply(f"🆔 شناسه شما: `{sender}`")
        return

    # حذف
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

    # بن
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

    # اخراج
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

    # اخطار
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

    # حذف اخطار
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

    # قوانین
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

    # تنظیم پیام خوش آمدی
    if text.startswith("تنظیم پیام خوش آمدی") or text.startswith("/setwelcome"):
        welcome_text = text.replace("تنظیم پیام خوش آمدی", "").replace("/setwelcome", "").strip()
        if not welcome_text:
            await update.reply("❌ بنویس: تنظیم پیام خوش آمدی <متن>")
            return
        data["welcome"][chat_key] = welcome_text
        save_data(data)
        await update.reply("✅ پیام خوش‌آمد تنظیم شد.")
        return

    if text in ("حذف پیام خوش آمدی", "/delwelcome"):
        if chat_key in data["welcome"]:
            del data["welcome"][chat_key]
            save_data(data)
            await update.reply("✅ پیام خوش‌آمد حذف شد.")
        else:
            await update.reply("ℹ️ پیام خوش‌آمدی تنظیم نشده بود.")
        return

    # قفل کردن گروه
    if text in ("قفل کردن گروه", "/lock"):
        if chat_key not in data["locked"]:
            data["locked"].append(chat_key)
            save_data(data)
        await update.reply("🔒 گروه قفل شد.")
        return

    if text in ("باز کردن گروه", "/unlock"):
        if chat_key in data["locked"]:
            data["locked"].remove(chat_key)
            save_data(data)
        await update.reply("🔓 گروه باز شد.")
        return

    # سکوت (با آیدی دستی)
    if text.startswith("سکوت") or text.startswith("/silence"):
        target = get_target_from_command(text, update)
        if not target:
            await update.reply("❌ بنویس: سکوت u0...\n(یا روی پیام کاربر ریپلای کن و بنویس «سکوت» اگر ریپلای کار کرد)")
            return
        silenced = data.setdefault("silenced", {}).setdefault(chat_key, [])
        if str(target) not in [str(u) for u in silenced]:
            silenced.append(str(target))
            save_data(data)
        await update.reply(f"🤐 کاربر {target} سکوت شد.")
        return

    # حذف سکوت (با آیدی دستی)
    if text.startswith("حذف سکوت") or text.startswith("/unsilence"):
        target = get_target_from_command(text, update)
        if not target:
            await update.reply("❌ بنویس: حذف سکوت u0...")
            return
        silenced = data.setdefault("silenced", {}).setdefault(chat_key, [])
        if str(target) in [str(u) for u in silenced]:
            silenced[:] = [u for u in silenced if str(u) != str(target)]
            save_data(data)
            await update.reply(f"🔊 کاربر {target} از سکوت درآمد.")
        else:
            await update.reply("ℹ️ این کاربر در سکوت نبود.")
        return

    # فیلترها
    if text in ("لینک قفل", "/locklink"):
        set_filter_state(chat_key, "link", True)
        await update.reply("🔗 فیلتر لینک فعال شد.")
        return
    if text in ("لینک باز", "/unlocklink"):
        set_filter_state(chat_key, "link", False)
        await update.reply("🔓 فیلتر لینک غیرفعال شد.")
        return
    if text in ("آیدی قفل", "/lockid"):
        set_filter_state(chat_key, "id", True)
        await update.reply("🆔 فیلتر آیدی فعال شد.")
        return
    if text in ("آیدی باز", "/unlockid"):
        set_filter_state(chat_key, "id", False)
        await update.reply("🔓 فیلتر آیدی غیرفعال شد.")
        return
    if text in ("فحش قفل", "/lockbad"):
        set_filter_state(chat_key, "bad", True)
        await update.reply("🤬 فیلتر فحش فعال شد.")
        return
    if text in ("فحش باز", "/unlockbad"):
        set_filter_state(chat_key, "bad", False)
        await update.reply("🔓 فیلتر فحش غیرفعال شد.")
        return

    # ادمین کردن
    if text.startswith("ادمین") or text.startswith("/admin"):
        target = get_target_from_command(text, update)
        if not target:
            await update.reply("❌ بنویس: ادمین u0...\nیا روی پیام کاربر ریپلای کن و بنویس «ادمین»")
            return
        admins = data.setdefault("admins", {}).setdefault(chat_key, [])
        if str(target) not in [str(a) for a in admins]:
            admins.append(str(target))
            save_data(data)
        await update.reply(f"👑 کاربر {target} به عنوان ادمین اضافه شد.")
        return

    # برکناری
    if text.startswith("برکنار") or text.startswith("/demote"):
        target = get_target_from_command(text, update)
        if not target:
            await update.reply("❌ بنویس: برکنار u0...")
            return
        admins = data.setdefault("admins", {}).setdefault(chat_key, [])
        if str(target) in [str(a) for a in admins]:
            admins[:] = [a for a in admins if str(a) != str(target)]
            save_data(data)
            await update.reply(f"🚫 کاربر {target} از ادمینی برکنار شد.")
        else:
            await update.reply("ℹ️ این کاربر ادمین نبود.")
        return

    # لیست ادمین‌ها
    if text in ("ادمین‌ها", "/admins"):
        admins = data.get("admins", {}).get(chat_key, [])
        owner = data.get("owners", {}).get(chat_key, "ثبت نشده")
        if not admins and not owner:
            await update.reply("ℹ️ هنوز ادمینی ثبت نشده.")
            return
        msg = f"👑 **مالک:** `{owner}`\n\n**ادمین‌ها:**\n"
        if admins:
            for a in admins:
                msg += f"• `{a}`\n"
        else:
            msg += "—"
        await update.reply(msg)
        return

    # پاک <تعداد>
    if text.startswith("پاک") or text.startswith("/clear"):
        parts = text.replace("/clear", "").replace("پاک", "").strip().split()
        if not parts or not parts[0].isdigit():
            await update.reply("❌ بنویس: پاک <تعداد>\nمثال: پاک ۳۰\n(حداقل ۱، حداکثر ۵۰۰)")
            return
        count = int(parts[0])
        if count < 1 or count > 500:
            await update.reply("❌ تعداد باید بین ۱ تا ۵۰۰ باشد.")
            return
        deleted = 0
        for i in range(1, count + 1):
            target_id = msg_id - i
            if target_id <= 0:
                break
            try:
                await client.delete_message(chat_id, target_id)
                deleted += 1
            except Exception:
                continue
        await update.reply(f"🧹 {deleted} پیام اخیر پاک شد. (از {count} درخواست‌شده)")
        return

    # آمار
    if text in ("آمار", "/stats"):
        warns = data["warns"].get(chat_key, {})
        banned = data["banned"].get(chat_key, [])
        msg_count = data.get("msg_count", {}).get(chat_key, {})
        total_msgs = sum(msg_count.values())
        top10 = sorted(msg_count.items(), key=lambda x: -x[1])[:10]
        top_lines = []
        for i, (uid, cnt) in enumerate(top10, 1):
            link = f"https://rubika.ir/{uid}"
            top_lines.append(f"{i}. [{uid}]({link}) — {cnt} پیام")
        top_str = "\n".join(top_lines) or "—"
        locked = "🔒 بسته" if chat_key in data.get("locked", []) else "🔓 باز"
        owner = data.get("owners", {}).get(chat_key, "ثبت نشده")
        silenced_count = len(data.get("silenced", {}).get(chat_key, []))
        admins_count = len(data.get("admins", {}).get(chat_key, []))
        link_state = "🔗 فعال" if get_filter_state(chat_key, "link") else "🔗 غیرفعال"
        id_state = "🆔 فعال" if get_filter_state(chat_key, "id") else "🆔 غیرفعال"
        bad_state = "🤬 فعال" if get_filter_state(chat_key, "bad") else "🤬 غیرفعال"
        msg = (
            f"📊 **آمار گروه**\n\n"
            f"👤 مالک: `{owner}`\n"
            f"👑 ادمین‌ها: {admins_count}\n"
            f"وضعیت گروه: {locked}\n"
            f"فیلترها: {link_state} | {id_state} | {bad_state}\n"
            f"🤐 سکوت‌شده‌ها: {silenced_count}\n"
            f"👥 بن‌شده‌ها: {len(banned)}\n"
            f"⚠️ اخطاردارها: {len(warns)}\n"
            f"💬 کل پیام‌ها: {total_msgs}\n\n"
            f"🏆 **۱۰ نفر پرتکلم:**\n{top_str}"
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
    print("📋 دستورات: حذف، بن، اخراج، اخطار، شناسه، قوانین، خوش‌آمد، قفل/باز، سکوت، فیلترها، ادمین، برکنار، پاک، آمار")
    app.run()
