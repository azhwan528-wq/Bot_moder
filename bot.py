import json
import os
import re
import threading
import time
import requests
import random
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

from rubibot import RubiBot

TOKEN = os.environ.get("BOT_TOKEN", "")
if not TOKEN:
    print("❌ BOT_TOKEN تنظیم نشده!")
    exit(1)

bot = RubiBot(TOKEN)
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

# ==================== لیست‌های سرگرمی ====================
CHALLENGES = [
    "بهترین خاطره‌ات از دوران مدرسه رو تعریف کن.",
    "آخرین باری که از ته دل خندیدی کی بود؟",
    "اگه می‌تونستی یه توانایی خاص داشته باشی، چی انتخاب می‌کردی؟",
    "بزرگترین ترست چیه؟",
    "آخرین آهنگی که گوش دادی چی بود؟",
    "اگه یه روز نامرئی می‌شدی، چیکار می‌کردی؟",
    "بدترین هدیه‌ای که تا حالا گرفتی چی بود؟",
    "اولین چیزی که وقتی از خواب بیدار می‌شی بهش فکر می‌کنی چیه؟",
    "اگه قرار بود یه کتاب بنویسی، اسمش رو چی می‌ذاشتی؟",
    "آخرین فیلمی که دیدی و چقدر بهش نمره می‌دی؟",
    "اگه یه سفر رایگان به هر جای دنیا داشتی، کجا می‌رفتی؟",
    "بهترین دوستت رو چطور توصیف می‌کنی؟",
    "چیزی که هیچ‌وقت نمی‌تونی ببخشی چیه؟",
    "اگه یه روز پول بی‌نهایت داشتی، اولین کارت چی بود؟",
    "بدترین درسی که تو مدرسه داشتی چی بود؟",
    "آخرین باری که گریه کردی برای چی بود؟",
    "اگه می‌تونستی با یه شخصیت تاریخی شام بخوری، کی رو انتخاب می‌کردی؟",
    "یه چیزی که هیچ‌کس درباره‌ات نمی‌دونه چیه؟",
    "بهترین نصیحتی که تا حالا گرفتی چیه؟",
    "اگه یه سوپرپاور داشتی، ازش چطور استفاده می‌کردی؟",
    "دوست داری کدوم حیوان باشی و چرا؟",
    "آخرین باری که یه کار احمقانه کردی کی بود؟",
    "اگه می‌تونستی یه قانون تو دنیا عوض کنی، چی رو عوض می‌کردی؟",
    "بزرگترین آرزوی دوران کودکیت چی بود؟",
    "چی باعث می‌شه بیشتر از همه عصبی بشی؟",
    "اگه یه روز رو با کسی می‌تونستی عوض کنی، کی رو انتخاب می‌کردی؟",
    "بهترین ویژگی خودت چیه؟",
    "بدترین ویژگی خودت چیه؟",
    "اگه مجبور بودی یه غذا رو تا آخر عمر بخوری، چی انتخاب می‌کردی؟",
    "یه چیز که همیشه می‌خواستی یاد بگیری ولی وقت نکردی چیه؟",
    "آخرین باری که از کسی ناامید شدی کی بود؟",
    "اگه می‌تونستی به گذشته برگردی، چه کاری رو متفاوت انجام می‌دادی؟",
    "دوست داری ۱۰ سال دیگه کجا باشی؟",
    "چی بیشتر از همه تو رو خوشحال می‌کنه؟",
    "یه عادت بد که داری و دوست داری ترکش کنی چیه؟",
    "بهترین سفر زندگیت کجا بود؟",
    "اگه یه روز کامل بدون اینترنت بودی، چیکار می‌کردی؟",
    "دوست داری چه مهارتی رو در خودت تقویت کنی؟",
    "آخرین کتابی که خوندی چی بود؟",
    "اگه یه رستوران باز می‌کردی، اسمش رو چی می‌ذاشتی؟",
    "بهترین هدیه‌ای که تا حالا گرفتی چی بود؟",
    "چی تو رو بیشتر از همه می‌ترسونه؟",
    "اگه می‌تونستی یه روز با یه شخصیت کارتونی زندگی کنی، کی رو انتخاب می‌کردی؟",
    "یه چیزی که باعث افتخارت می‌شه چیه؟",
    "چی تو رو بیشتر از همه ناراحت می‌کنه؟",
    "دوست داری چه لقبی داشته باشی؟",
    "آخرین باری که یه کار جدید رو امتحان کردی کی بود؟",
    "بهترین دوستت چه ویژگی‌ای داره که تو دوستش داری؟",
    "اگه می‌تونستی یه روز رو دوباره تجربه کنی، کدوم روز بود؟",
    "چی تو رو بیشتر از همه می‌خندونه؟",
    "بهترین تصمیمی که تا حالا گرفتی چیه؟",
    "بدترین تصمیمی که تا حالا گرفتی چیه؟",
    "دوست داری چه چیزی رو تو خودت تغییر بدی؟",
    "آخرین باری که به کسی کمک کردی کی بود؟",
    "چی بیشتر از همه تو رو آروم می‌کنه؟",
    "اگه یه جزیره متروکه فرستاده می‌شدی، سه چیز رو با خودت می‌بردی؟",
    "بهترین ویژگی دوستات چیه؟",
    "چی تو رو بیشتر از همه هیجان‌زده می‌کنه؟",
    "دوست داری چه چیز جدیدی رو تجربه کنی؟",
    "آخرین باری که یه اتفاق غیرمنتظره برات افتاد کی بود؟",
    "بهترین چیز درباره‌ی خانواده‌ات چیه؟",
    "چی تو رو بیشتر از همه ناامید می‌کنه؟",
    "دوست داری چه چیزی رو به بقیه یاد بدی؟",
    "آخرین باری که یه تصمیم سخت گرفتی کی بود؟",
    "بهترین چیز درباره‌ی این گروه چیه؟",
    "چی تو رو بیشتر از همه به فکر فرو می‌بره؟",
    "دوست داری چه چیزی رو تو دنیا تغییر بدی؟",
    "آخرین باری که یه کار خارق‌العاده کردی کی بود؟",
    "بهترین چیز درباره‌ی خودت چیه؟",
    "چی تو رو بیشتر از همه شرمنده می‌کنه؟",
    "دوست داری چه چیزی رو با دیگران به اشتراک بذاری؟",
    "آخرین باری که یه چیز جدید یاد گرفتی کی بود؟",
    "بهترین چیز درباره‌ی دوستات چیه؟",
    "چی تو رو بیشتر از همه به چالش می‌کشه؟",
    "دوست داری چه چیزی رو در آینده انجام بدی؟",
    "آخرین باری که یه رویا دیدی و به یادش می‌مونی کی بود؟",
    "بهترین چیز درباره‌ی زندگی چیه؟",
    "چی تو رو بیشتر از همه به گریه می‌ندازه؟",
    "دوست داری چه چیزی رو با کسی در میون بذاری؟",
    "آخرین باری که یه کار غیرمنتظره انجام دادی کی بود؟",
    "بهترین چیز درباره‌ی امروز چیه؟",
    "چی تو رو بیشتر از همه به خنده می‌ندازه؟",
    "دوست داری چه چیزی رو در خودت ببینی؟",
    "آخرین باری که یه اتفاق خوب برات افتاد کی بود؟",
    "بهترین چیز درباره‌ی فردا چیه؟",
    "چی تو رو بیشتر از همه به فکر کردن وادار می‌کنه؟",
    "دوست داری چه چیزی رو با دیگران تقسیم کنی؟",
    "آخرین باری که یه کار درست انجام دادی کی بود؟",
    "بهترین چیز درباره‌ی دیروز چیه؟",
    "چی تو رو بیشتر از همه به خودت شک می‌ندازه؟",
    "دوست داری چه چیزی رو در زندگی تجربه کنی؟",
    "آخرین باری که یه کار اشتباه انجام دادی کی بود؟",
    "بهترین چیز درباره‌ی این لحظه چیه؟",
    "چی تو رو بیشتر از همه به خودت باور داری؟",
    "دوست داری چه چیزی رو به دیگران هدیه بدی؟",
    "آخرین باری که یه کار خلاقانه انجام دادی کی بود؟",
    "بهترین چیز درباره‌ی تو چیه؟",
    "چی تو رو بیشتر از همه به دیگران نزدیک می‌کنه؟",
    "دوست داری چه چیزی رو در دنیا ببینی؟",
]

TRUTH_OR_DARE = [
    "بزرگترین ترس زندگی‌ات چیه؟",
    "آخرین باری که گریه کردی کی بود و چرا؟",
    "تا حالا حس کردی کسی واقعاً تو رو نمی‌فهمه؟",
    "چیزی که همیشه باعث شده به خودت شک کنی چیه؟",
    "عمیق‌ترین ترس زندگی‌ات چیه؟",
    "به نظرت جذاب‌ترین شخص این جمع کیه؟",
    "بزرگ‌ترین حسرت زندگی‌ات چیه؟",
    "تا حالا تقلب یا کلاهبرداری کردی؟ داستانش رو تعریف کن.",
    "بزرگ‌ترین دروغ زندگی‌ات چی بوده؟",
    "اگه فقط یک روز از عمرت باقی مونده بود چیکار می‌کردی؟",
    "چه نیروی خارق‌العاده‌ای دوست داشتی داشته باشی؟",
    "عجیب‌ترین خوابی که دیدی چی بوده؟",
    "بدترین هدیه‌ای که گرفتی چی بود؟",
    "چه سوالی رو دوست نداری توی این بازی جواب بدی؟",
    "یکی از فانتزی‌های عاشقانه‌ات رو بگو.",
    "آخرین پیامی که به کسی دادی رو با صدای بلند بخون!",
    "وسایل توی کیف یا جیبت رو نشون بده!",
    "به اولین نفر توی لیست مخاطبینت زنگ بزن و آهنگ تولدت مبارک رو براش بخون!",
    "ادای یه حیوان رو دربیار و بقیه حدس بزنن!",
    "بچرخ و بعد سعی کن بلند شی و صاف راه بری!",
    "تا حالا شده به جای مدرسه/دانشگاه بری یه جا دیگه؟",
    "تا حالا تو امتحانا تقلب کردی؟",
    "اگه یه چیزی می‌تونستی اختراع کنی اون چی بود؟",
    "بزرگ‌ترین آرزوی شغلیت چیه؟",
    "الگوت تو زندگی کیه و چرا؟",
    "بزرگ‌ترین ترس دوران کودکیت چی بود؟",
    "آخرین باری که از ته دل خندیدی کی بود؟",
    "بهترین خاطره‌ات از دوران مدرسه چیه؟",
    "بدترین خاطره‌ات از دوران مدرسه چیه؟",
    "اگه می‌تونستی یه روز جای یه نفر باشی، کی رو انتخاب می‌کردی؟",
    "چی تو رو بیشتر از همه عصبی می‌کنه؟",
    "چی تو رو بیشتر از همه خوشحال می‌کنه؟",
    "چی تو رو بیشتر از همه ناراحت می‌کنه؟",
    "بهترین ویژگی خودت چیه؟",
    "بدترین ویژگی خودت چیه؟",
    "یه چیزی که هیچ‌کس درباره‌ات نمی‌دونه چیه؟",
    "بهترین نصیحتی که تا حالا گرفتی چیه؟",
    "بدترین نصیحتی که تا حالا گرفتی چیه؟",
    "اگه می‌تونستی یه قانون تو دنیا عوض کنی، چی رو عوض می‌کردی؟",
    "بزرگ‌ترین آرزوی دوران کودکیت چی بود؟",
    "آخرین باری که یه کار احمقانه کردی کی بود؟",
    "دوست داری کدوم حیوان باشی و چرا؟",
    "اگه یه سوپرپاور داشتی، ازش چطور استفاده می‌کردی؟",
    "بهترین سفر زندگیت کجا بود؟",
    "بدترین سفر زندگیت کجا بود؟",
    "آخرین کتابی که خوندی چی بود؟",
    "آخرین فیلمی که دیدی چی بود؟",
    "بهترین فیلمی که دیدی چی بود؟",
    "بدترین فیلمی که دیدی چی بود؟",
    "آخرین آهنگی که گوش دادی چی بود؟",
    "بهترین آهنگی که گوش دادی چی بود؟",
    "دوست داری چه مهارتی رو یاد بگیری؟",
    "دوست داری چه زبانی رو یاد بگیری؟",
    "دوست داری به کدوم کشور سفر کنی؟",
    "دوست داری چه غذایی رو امتحان کنی؟",
    "بدترین غذایی که خوردی چی بود؟",
    "بهترین غذایی که خوردی چی بود؟",
    "دوست داری چه نوشیدنی‌ای رو امتحان کنی؟",
    "بدترین نوشیدنی‌ای که خوردی چی بود؟",
    "بهترین نوشیدنی‌ای که خوردی چی بود؟",
    "دوست داری چه ورزشی رو انجام بدی؟",
    "دوست داری چه ساز موسیقی رو یاد بگیری؟",
    "دوست داری چه هنری رو یاد بگیری؟",
    "دوست داری چه شغلی رو امتحان کنی؟",
    "دوست داری چه کسب‌وکاری راه بندازی؟",
    "دوست داری چه اختراعی بکنی؟",
    "دوست داری چه اکتشافی بکنی؟",
    "دوست داری چه تحقیقی بکنی؟",
    "دوست داری چه کتابی بنویسی؟",
    "دوست داری چه فیلمی بسازی؟",
    "دوست داری چه آهنگی بسازی؟",
    "دوست داری چه بازی‌ای بسازی؟",
    "دوست داری چه اپلیکیشنی بسازی؟",
    "دوست داری چه وب‌سایتی بسازی؟",
    "دوست داری چه رباتی بسازی؟",
    "دوست داری چه کاری رو برای اولین بار انجام بدی؟",
    "دوست داری چه کاری رو برای آخرین بار انجام بدی؟",
    "دوست داری چه چیزی رو به بقیه یاد بدی؟",
    "دوست داری چه چیزی رو از بقیه یاد بگیری؟",
    "دوست داری چه چیزی رو با بقیه به اشتراک بذاری؟",
    "دوست داری چه چیزی رو از بقیه پنهان کنی؟",
    "دوست داری چه چیزی رو در خودت تغییر بدی؟",
    "دوست داری چه چیزی رو در دیگران تغییر بدی؟",
    "دوست داری چه چیزی رو در دنیا تغییر بدی؟",
    "دوست داری چه چیزی رو در آینده ببینی؟",
    "دوست داری چه چیزی رو در گذشته می‌دیدی؟",
    "دوست داری چه چیزی رو در حال حاضر تجربه کنی؟",
    "دوست داری چه چیزی رو در آینده تجربه کنی؟",
    "دوست داری چه چیزی رو هرگز تجربه نکنی؟",
    "دوست داری چه چیزی رو همیشه تجربه کنی؟",
    "دوست داری چه چیزی رو یک بار تجربه کنی؟",
    "دوست داری چه چیزی رو چند بار تجربه کنی؟",
    "دوست داری چه چیزی رو هیچ‌وقت تجربه نکنی؟",
    "دوست داری چه چیزی رو حتماً تجربه کنی؟",
    "دوست داری چه چیزی رو شاید تجربه کنی؟",
    "دوست داری چه چیزی رو احتمالاً تجربه کنی؟",
    "دوست داری چه چیزی رو قطعاً تجربه کنی؟",
]

BIOS = [
    "دنیا محل عبوره، ما هم رهگذریم.",
    "هرچی که دارم از لطف توست.",
    "زندگی زیباست، فقط باید درست ببینیش.",
    "من همونیم که هستم، نه چیزی که می‌خوای باشم.",
    "با لبخندت دنیا رو زیباتر کن.",
    "آرامش یعنی همین که هست.",
    "به خودت ایمان داشته باش.",
    "هیچ‌وقت دیر نیست برای شروع دوباره.",
    "خودت باش، بقیه نقش‌ها رو دیگران بازی می‌کنن.",
    "زندگی مثل دوچرخه‌سواریه، برای تعادل باید حرکت کنی.",
    "هر روز یه شروع جدیده.",
    "بهترین انتقام موفقیت است.",
    "عشق یعنی همین که هستی.",
    "دل به دریا بزن، ساحل نزدیکه.",
    "هر سختی یه آسونیه.",
    "به امید فردا.",
    "زندگی بدون ریسک، هیچی نیست.",
    "خودت رو باور کن.",
    "همیشه یه راهی هست.",
    "هیچ‌وقت نگو هرگز.",
    "با عشق زندگی کن.",
    "لبخند بهترین آرایشه.",
    "آرزو کن، تلاش کن، برس.",
    "هر چیزی ممکنه.",
    "به رویاهات ایمان داشته باش.",
    "زندگی کوتاهه، قدرشو بدون.",
    "دنیا رو با چشمای خودت ببین.",
    "منحصر به فرد باش.",
    "خودت رو دوست داشته باش.",
    "بهترین نسخه خودت باش.",
    "هر روز بهتر از دیروز.",
    "زندگی یه هدیه‌ست.",
    "با انرژی مثبت پیش برو.",
    "هیچ‌وقت از تلاش دست نکش.",
    "به خودت افتخار کن.",
    "دنیا رو تغییر بده.",
    "بهترین دوست خودت باش.",
    "هر لحظه رو زندگی کن.",
    "به آینده امیدوار باش.",
    "خودت رو قبول داشته باش.",
    "زندگی زیباست.",
    "با لبخند به استقبال روز برو.",
    "هر روز یه ماجراجویی جدیده.",
    "بهترین چیزها رایگانن.",
    "دلخوشی‌های کوچیک، خوشبختی‌های بزرگ.",
    "زندگی یه سفر است، نه مقصد.",
    "به مسیر ایمان داشته باش.",
    "هر قدم یه پیشرفته.",
    "خودت رو دست کم نگیر.",
    "بهترین روزها در راهن.",
    "با امید زندگی کن.",
    "هر چالشی یه فرصته.",
    "به خودت باور داشته باش.",
    "زندگی پر از شگفتیه.",
    "با عشق پیش برو.",
    "هر روز یه فرصت جدیده.",
    "بهترین نسخه خودت رو بساز.",
    "خودت رو دوست بدار.",
    "به دنیا لبخند بزن.",
    "هر لحظه رو غنیمت بشمار.",
    "به رویاهات چنگ بزن.",
    "زندگی یه بازی است، درست بازی کن.",
    "با انرژی مثبت زندگی کن.",
    "هر روز یه هدیه‌ست.",
    "به خودت ایمان داشته باش.",
    "بهترین چیزها در انتظارن.",
    "خودت رو باور کن.",
    "هر روز یه شروع تازه‌ست.",
    "به آینده امیدوار باش.",
    "زندگی زیباست، ازش لذت ببر.",
    "با لبخند زندگی کن.",
    "هر روز یه ماجراست.",
    "به خودت افتخار کن.",
    "بهترین نسخه خودت باش.",
    "خودت رو دوست داشته باش.",
    "به دنیا عشق بورز.",
    "هر لحظه رو زندگی کن.",
    "به رویاهات ایمان بیار.",
    "زندگی یه سفر است.",
    "با امید پیش برو.",
    "هر روز بهتر از دیروز.",
    "به خودت باور داشته باش.",
    "بهترین روزها در راهن.",
    "خودت رو دست کم نگیر.",
    "به مسیر ایمان داشته باش.",
    "هر قدم یه پیشرفته.",
    "به آینده امیدوار باش.",
    "زندگی پر از شگفتیه.",
    "با عشق زندگی کن.",
    "هر روز یه فرصت جدیده.",
    "به خودت ایمان داشته باش.",
    "بهترین نسخه خودت رو بساز.",
    "خودت رو دوست بدار.",
    "به دنیا لبخند بزن.",
    "هر لحظه رو غنیمت بشمار.",
    "به رویاهات چنگ بزن.",
    "زندگی یه بازی است.",
    "با انرژی مثبت زندگی کن.",
    "هر روز یه هدیه‌ست.",
]

DEEP_TRUTH_OR_DARE = [
    "بزرگ‌ترین راز زندگیت چیه که هیچ‌کس نمی‌دونه؟",
    "اگه می‌تونستی به گذشته برگردی و یه تصمیم رو عوض کنی، کدوم تصمیم بود؟",
    "چیزی که بیشتر از همه ازش پشیمونی چیه؟",
    "اگه قرار بود امروز آخرین روز زندگیت باشه، به کی چی می‌گفتی؟",
    "بزرگ‌ترین درسی که زندگی بهت داده چیه؟",
    "چیزی که همیشه می‌خواستی بگی ولی نگرانی از واکنش دیگران باعث شده نگیش چیه؟",
    "اگه می‌تونستی یه نفر رو ببخشی، کی رو انتخاب می‌کردی؟",
    "بزرگ‌ترین ترس درونی‌ات چیه که هیچ‌وقت به کسی نگفتی؟",
    "چیزی که باعث می‌شه احساس کنی واقعاً زنده‌ای چیه؟",
    "اگه فقط یه جمله می‌تونستی به دنیا بگی، چی می‌گفتی؟",
]

# ---------- 50 جوک ----------
JOKES = [
    "به یارو میگن چرا دیر اومدی؟ میگه آخه ساعت ۳ بود، گفتم صبر کنم ۴ بشه!",
    "به یارو میگن تو خونه‌تون چند تا اتاق داره؟ میگه والا من تو راهرو زندگی می‌کنم!",
    "یه بار به دوستم گفتم بریم ماهیگیری، گفت آخه من شنا بلد نیستم!",
    "به یارو میگن چرا ریشات رو نمی‌زنی؟ میگه آخه این ریش‌ها رو با پول درآوردم!",
    "به یارو میگن تو مدرسه چی یاد گرفتی؟ میگه یاد گرفتم که تو مدرسه چیزی یاد نمی‌دن!",
    "یه بار یه پنگوئن رفت رستوران، گارسون گفت چی می‌خوری؟ گفت ماهی. گارسون گفت چه نوعی؟ گفت سرد!",
    "به یارو میگن اگه یه روز پولدار بشی چیکار می‌کنی؟ میگه می‌رم یه پیتزا می‌خرم، اونم بزرگش!",
    "به استاد گفتن چرا نمره من صفره؟ گفت چون تو برگه‌ت هیچی ننوشتی. گفت آخه من با اشاره حرف می‌زدم!",
    "به یارو میگن چرا از خونه فرار کردی؟ میگه آخه دیوارها داشتن بهم نزدیک می‌شدن!",
    "یه بار یه گربه رفت پیش دکتر، دکتر گفت چی شده؟ گفت میو!",
    "به یارو میگن چرا داری با تلفن حرف می‌زنی؟ میگه آخه این تلفن با من حرف می‌زنه!",
    "یه بار یه خرس رفت فروشگاه، فروشنده گفت چی می‌خوای؟ گفت عسل. فروشنده گفت چه مارکی؟ گفت وحشی!",
    "به یارو میگن چرا اینقدر می‌خندی؟ میگه آخه یادم اومد دیروز چرا می‌خندیدم!",
    "یه بار یه ماهی رفت پیش ملوان، گفت چرا منو گرفتی؟ ملوان گفت تو خودت اومدی تو تور!",
    "به یارو میگن تو خواب چی می‌بینی؟ میگه خواب می‌بینم بیدارم، بعد بیدار می‌شم می‌بینم خوابم!",
    "به استاد گفتن چرا کلاس تعطیله؟ گفت چون من امروز حالم خوبه!",
    "یه بار یه پرنده رفت رستوران، گارسون گفت چی می‌خوری؟ گفت کرم، ولی سرخ شده باشه!",
    "به یارو میگن چرا پاهات کجه؟ میگه آخه از بچگی با کج‌ها بزرگ شدم!",
    "به یارو میگن تو ماهیگیری بلدی؟ میگه آره، فقط ماهی‌ها بلد نیستن!",
    "یه بار یه فیل رفت تو یه مغازه، فروشنده گفت داداش ما جاش نداریم!",
    "به یارو میگن چرا اینقدر لاغری؟ میگه آخه من با هوا زندگی می‌کنم!",
    "به یارو میگن چرا ازدواج نکردی؟ میگه آخه من عاشق خودمم!",
    "یه بار یه سگ رفت پیش گربه، گفت میای دوست بشیم؟ گربه گفت برو بابا تو سگی!",
    "به یارو میگن چرا مدرسه نرفتی؟ میگه آخه من تو مدرسه معلم بودم!",
    "به یارو میگن تو فوتبال بازی می‌کنی؟ میگه آره، ولی توپ رو نمی‌زنم، توپ منو می‌زنه!",
    "یه بار یه گاو رفت پیش دکتر، دکتر گفت چی شده؟ گفت شیرم خشک شده، دکتر گفت خب آب بخور!",
    "به یارو میگن چرا موهات سفیده؟ میگه آخه از بچگی پیر بودم!",
    "به یارو میگن تو چی می‌خونی؟ میگه من کتاب نمی‌خونم، کتاب منو می‌خونه!",
    "یه بار یه لاک‌پشت رفت مسابقه دو، گفت من اول می‌شم، ولی سال دیگه!",
    "به یارو میگن چرا از ارتفاع می‌ترسی؟ میگه آخه از بچگی از بالا نگاه می‌کردم!",
    "به یارو میگن تو شنا بلدی؟ میگه آره، فقط تو آب غرق می‌شم!",
    "یه بار یه خرگوش رفت پیش لاک‌پشت، گفت مسابقه بدیم؟ لاک‌پشت گفت باشه، ولی من امروز وقت ندارم!",
    "به یارو میگن چرا اینقدر می‌خوابی؟ میگه آخه خواب بهترین دوست منه!",
    "به یارو میگن چرا اینقدر می‌خوری؟ میگه آخه من با غذا حرف می‌زنم!",
    "یه بار یه گربه رفت پیش ماهی، گفت بیا دوست بشیم، ماهی گفت برو بابا تو گربه‌ای!",
    "به یارو میگن تو آشپزی بلدی؟ میگه آره، فقط غذاهام خوراکی نیستن!",
    "به یارو میگن چرا اینقدر تنها هستی؟ میگه آخه من با خودم حرف می‌زنم!",
    "یه بار یه سگ رفت پیش گربه، گفت بیا با هم بریم ماهیگیری، گربه گفت من که ماهی نمی‌خورم!",
    "به یارو میگن تو رانندگی بلدی؟ میگه آره، فقط ماشین رو نمی‌تونم کنترل کنم!",
    "به یارو میگن چرا اینقدر ترسویی؟ میگه آخه من از سایه خودم می‌ترسم!",
    "به یارو میگن تو انگلیسی بلدی؟ میگه آره، yes و no و maybe!",
    "یه بار یه ماهی رفت پیش پرنده، گفت بیا با هم پرواز کنیم، پرنده گفت تو که بال نداری!",
    "به یارو میگن چرا اینقدر خسیسی؟ میگه آخه پول رو باید نگه داشت!",
    "به یارو میگن تو نقاشی بلدی؟ میگه آره، فقط نقاشی‌هام شبیه خط خطی هستن!",
    "به یارو میگن چرا اینقدر ساکتی؟ میگه آخه دارم با خودم حرف می‌زنم!",
    "یه بار یه فیل رفت پیش مورچه، گفت بیا با هم بازی کنیم، مورچه گفت من که نمی‌تونم تو رو ببینم!",
    "به یارو میگن تو موسیقی بلدی؟ میگه آره، فقط آهنگ‌هام گوش‌خراشن!",
    "به یارو میگن چرا اینقدر عجله داری؟ میگه آخه دیر شده!",
    "به یارو میگن تو ریاضی بلدی؟ میگه آره، ۱+۱=۲، بقیه‌اش رو نمی‌دونم!",
    "به یارو میگن چرا اینقدر می‌ترسی؟ میگه آخه من از همه چیز می‌ترسم، حتی از ترسیدن!",
    "به یارو میگن تو برنامه‌نویسی بلدی؟ میگه آره، فقط کدهام کار نمی‌کنن!",
    "به یارو میگن چرا اینقدر می‌خندی؟ میگه آخه به خودم فکر می‌کنم!",
    "به یارو میگن تو شاعر هستی؟ میگه آره، فقط شعرهام قافیه ندارن!",
]

# ==================== لیست پیشوندهای دستورات ====================
COMMAND_PREFIXES = [
    "start", "راهنما", "help", "ping", "پینگ", "time", "زمان",
    "شناسهمن", "شناسهاو", "شناسه", "id", "myid", "theirid",
    "مالک", "owner", "delete", "حذف", "ban", "بن", "kick", "اخراج",
    "warn", "اخطار", "unwarn", "حذفاخطار", "rules", "قوانین",
    "setrules", "تنظیمقوانین", "setwelcome", "تنظیمپیامخوشآمدی",
    "delwelcome", "حذفپیامخوشآمدی", "lock", "قفلکردنگروه", "قفل",
    "unlock", "بازکردنگروه", "بازکردن", "silence", "سکوت",
    "unsilence", "حذفسکوت", "locklink", "لینکقفل", "unlocklink", "لینکباز",
    "lockid", "آیدیقفل", "unlockid", "آیدیباز", "lockbad", "فحشقفل",
    "unlockbad", "فحشباز", "admins", "adminlist", "ادمینها", "لیستادمین",
    "admin", "ادمین", "demote", "برکنار", "clear", "پاک", "stats", "آمار",
    "چالش", "challenge", "جرئت", "dare", "truthordare", "بیو", "bio",
    "جرئتحقیقت", "deeptruth", "بازی", "game", "games", "جوک", "joke",
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
        if hasattr(message, 'reply_to_message') and message.reply_to_message:
            replied = message.reply_to_message
            if hasattr(replied, 'sender_id'):
                return str(replied.sender_id)
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
🔹 مالک — نمایش آیدی مالک
🔹 شناسه / شناسه من / شناسه او
🔹 لیست ادمین — نمایش ادمین‌ها
🔹 ادمین / برکنار — با ریپلای یا آیدی

⚙️ **تنظیمات:**
🔹 قوانین / تنظیم قوانین <متن>
🔹 تنظیم پیام خوش آمدی <متن> / حذف پیام خوش آمدی
🔹 قفل کردن گروه / باز کردن گروه
🔹 لینک قفل / لینک باز
🔹 آیدی قفل / آیدی باز
🔹 فحش قفل / فحش باز

🛡️ **مدیریت اعضا:**
🔹 حذف / بن / اخراج — با ریپلای یا آیدی
🔹 اخطار / حذف اخطار
🔹 سکوت / حذف سکوت
🔹 پاک <تعداد> — ۱ تا ۵۰۰

🎮 **سرگرمی:**
🔹 چالش — یک چالش تصادفی
🔹 جرئت — یک جرئت یا حقیقت
🔹 بیو — یک بیو تصادفی
🔹 جرئت حقیقت — یک سوال عمیق
🔹 جوک — یک جوک خنده‌دار
🔹 بازی — لیست بازی‌ها

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
    """هر ۵ دقیقه به URL خود ربات یه درخواست HTTP می‌زنه تا Render بیدار بمونه"""
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

@bot.message_handler()
def handle_all(message):
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
                bot.delete_message(message.chat_id, message.message_id); return
            if f.get("id") and ID_PATTERN.search(cmd):
                bot.delete_message(message.chat_id, message.message_id); return
            if f.get("bad") and has_bad(cmd):
                bot.delete_message(message.chat_id, message.message_id); return
            if ck in data.get("locked", []):
                bot.delete_message(message.chat_id, message.message_id); return
            if is_silenced(ck, uid):
                bot.delete_message(message.chat_id, message.message_id); return

        if ncmd in ("مالک", "owner"):
            owner = data.get("owners", {}).get(ck)
            if owner:
                bot.reply_to(message, f"👑 مالک گروه:\n`{owner}`")
            else:
                bot.reply_to(message, "ℹ️ هنوز مالکی تنظیم نشده.")
            return

        if ncmd in ("start", "راهنما", "help"):
            if is_group(ck) and not data.get("owners", {}).get(ck):
                data.setdefault("owners", {})[ck] = uid
                save_data(data)
                bot.reply_to(message, f"✅ شما به عنوان مالک گروه تنظیم شدید: `{uid}`")
            bot.reply_to(message, HELP)
            return

        if ncmd in ("ping", "پینگ"):
            start = time.time()
            bot.reply_to(message, "🏓 ...")
            elapsed = int((time.time() - start) * 1000)
            bot.reply_to(message, f"🏓 Pong! {elapsed}ms")
            return

        if ncmd in ("time", "زمان"):
            bot.reply_to(message, f"🕐 {datetime.now():%Y/%m/%d - %H:%M:%S}")
            return

        if ncmd in ("شناسهمن", "myid"):
            bot.reply_to(message, f"🆔 شناسه شما: `{uid}`")
            return
        if ncmd in ("شناسهاو", "theirid"):
            t = get_target(cmd, message)
            if t and t != uid:
                bot.reply_to(message, f"🆔 شناسه: `{t}`")
            else:
                bot.reply_to(message, "❌ روی پیام کاربر ریپلای کن.")
            return
        if ncmd in ("شناسه", "id"):
            if getattr(message, 'reply_to_message_id', None):
                t = get_target(cmd, message)
                if t and t != uid:
                    bot.reply_to(message, f"🆔 شناسه: `{t}`"); return
            bot.reply_to(message, f"🆔 شناسه شما: `{uid}`")
            return

        if ncmd in ("delete", "حذف"):
            if not message.reply_to_message_id:
                bot.reply_to(message, "❌ روی یک پیام ریپلای کن."); return
            try:
                bot.delete_message(message.chat_id, message.reply_to_message_id)
                bot.reply_to(message, "✅ پیام حذف شد.")
            except Exception as e:
                bot.reply_to(message, f"❌ {e}")
            return

        if ncmd.startswith("ban") or ncmd.startswith("بن"):
            t = get_target(cmd, message)
            if not t:
                bot.reply_to(message, "❌ ریپلای کن یا آیدی/لینک بده."); return
            if is_owner_or_admin(ck, t):
                bot.reply_to(message, "⚠️ نمی‌توان مالک یا ادمین را بن کرد."); return
            try:
                bot.ban_member(chat_id=message.chat_id, sender_id=t)
                data["banned"].setdefault(ck, []).append(t); save_data(data)
                bot.reply_to(message, f"🔨 {t} بن شد.")
            except Exception as e:
                bot.reply_to(message, f"❌ {e}")
            return

        if ncmd.startswith("kick") or ncmd.startswith("اخراج"):
            t = get_target(cmd, message)
            if not t:
                bot.reply_to(message, "❌ ریپلای کن یا آیدی/لینک بده."); return
            if is_owner_or_admin(ck, t):
                bot.reply_to(message, "⚠️ نمی‌توان مالک یا ادمین را اخراج کرد."); return
            try:
                bot.ban_member(chat_id=message.chat_id, sender_id=t)
                bot.unban_member(chat_id=message.chat_id, sender_id=t)
                bot.reply_to(message, "👢 کاربر اخراج شد.")
            except Exception as e:
                bot.reply_to(message, f"❌ {e}")
            return

        if ncmd.startswith("warn") or ncmd.startswith("اخطار"):
            t = get_target(cmd, message)
            if not t:
                bot.reply_to(message, "❌ ریپلای کن یا آیدی/لینک بده."); return
            if is_owner_or_admin(ck, t):
                bot.reply_to(message, "⚠️ نمی‌توان به مالک یا ادمین اخطار داد."); return
            w = data["warns"].setdefault(ck, {}); w[t] = w.get(t, 0) + 1; save_data(data)
            if w[t] >= 3:
                try:
                    bot.ban_member(chat_id=message.chat_id, sender_id=t)
                    bot.reply_to(message, f"🔨 {t} بن شد (۳ اخطار).")
                except Exception as e:
                    bot.reply_to(message, f"⚠️ {e}")
            else:
                bot.reply_to(message, f"⚠️ اخطار {w[t]}/۳ برای {t}.")
            return

        if ncmd.startswith("unwarn") or ncmd.startswith("حذفاخطار"):
            t = get_target(cmd, message)
            if not t:
                bot.reply_to(message, "❌ ریپلای کن یا آیدی/لینک بده."); return
            w = data["warns"].get(ck, {})
            if t in w: del w[t]; save_data(data); bot.reply_to(message, "✅ اخطار پاک شد.")
            else: bot.reply_to(message, "ℹ️ اخطاری نداشت.")
            return

        if ncmd in ("rules", "قوانین"):
            r = data["rules"].get(ck)
            bot.reply_to(message, f"📜 {r}" if r else "📜 تنظیم نشده.")
            return
        if ncmd.startswith("setrules") or ncmd.startswith("تنظیمقوانین"):
            r = cmd.replace("setrules", "").replace("تنظیم قوانین", "").strip()
            if not r: bot.reply_to(message, "❌ متن بده."); return
            data["rules"][ck] = r; save_data(data); bot.reply_to(message, "✅ تنظیم شد.")
            return

        if ncmd.startswith("setwelcome") or ncmd.startswith("تنظیمپیامخوشآمدی"):
            w = cmd.replace("setwelcome", "").replace("تنظیم پیام خوش آمدی", "").strip()
            if not w: bot.reply_to(message, "❌ متن بده."); return
            data["welcome"][ck] = w; save_data(data); bot.reply_to(message, "✅ تنظیم شد.")
            return
        if ncmd in ("delwelcome", "حذفپیامخوشآمدی"):
            if ck in data["welcome"]: del data["welcome"][ck]; save_data(data); bot.reply_to(message, "✅ حذف شد.")
            else: bot.reply_to(message, "ℹ️ تنظیم نشده بود.")
            return

        if ncmd in ("lock", "قفلکردنگروه", "قفل"):
            if ck not in data["locked"]: data["locked"].append(ck); save_data(data)
            bot.reply_to(message, "🔒 قفل شد. (ادمین‌ها و مالک معاف هستند)")
            return
        if ncmd in ("unlock", "بازکردنگروه", "بازکردن"):
            if ck in data["locked"]: data["locked"].remove(ck); save_data(data)
            bot.reply_to(message, "🔓 باز شد.")
            return

        if ncmd.startswith("unsilence") or ncmd.startswith("حذفسکوت"):
            t = get_target(cmd, message)
            if not t: bot.reply_to(message, "❌ ریپلای کن یا بنویس: حذف سکوت u0..."); return
            s = data.setdefault("silenced", {}).setdefault(ck, [])
            if t in s: s.remove(t); save_data(data); bot.reply_to(message, f"🔊 {t} آزاد شد.")
            else: bot.reply_to(message, "ℹ️ سکوت نبود.")
            return
        if ncmd.startswith("silence") or ncmd.startswith("سکوت"):
            t = get_target(cmd, message)
            if not t: bot.reply_to(message, "❌ ریپلای کن یا بنویس: سکوت u0..."); return
            if is_owner_or_admin(ck, t):
                bot.reply_to(message, "⚠️ نمی‌توان مالک یا ادمین را سکوت کرد."); return
            s = data.setdefault("silenced", {}).setdefault(ck, [])
            if t not in s: s.append(t); save_data(data)
            bot.reply_to(message, f"🤐 {t} سکوت شد.")
            return

        if ncmd in ("locklink", "لینکقفل"):
            data.setdefault("filters", {}).setdefault(ck, {})["link"] = True; save_data(data); bot.reply_to(message, "🔗 فیلتر لینک فعال شد."); return
        if ncmd in ("unlocklink", "لینکباز"):
            data.setdefault("filters", {}).setdefault(ck, {})["link"] = False; save_data(data); bot.reply_to(message, "🔓 فیلتر لینک غیرفعال شد."); return
        if ncmd in ("lockid", "آیدیقفل"):
            data.setdefault("filters", {}).setdefault(ck, {})["id"] = True; save_data(data); bot.reply_to(message, "🆔 فیلتر آیدی فعال شد."); return
        if ncmd in ("unlockid", "آیدیباز"):
            data.setdefault("filters", {}).setdefault(ck, {})["id"] = False; save_data(data); bot.reply_to(message, "🔓 فیلتر آیدی غیرفعال شد."); return
        if ncmd in ("lockbad", "فحشقفل"):
            data.setdefault("filters", {}).setdefault(ck, {})["bad"] = True; save_data(data); bot.reply_to(message, "🤬 فیلتر فحش فعال شد."); return
        if ncmd in ("unlockbad", "فحشباز"):
            data.setdefault("filters", {}).setdefault(ck, {})["bad"] = False; save_data(data); bot.reply_to(message, "🔓 فیلتر فحش غیرفعال شد."); return

        if ncmd in ("admins", "adminlist") or "لیستادمین" in ncmd or (ncmd.startswith("ادمین") and ncmd.endswith("ها")) or ncmd == "ادمینها":
            a = data.get("admins", {}).get(ck, [])
            o = data.get("owners", {}).get(ck, "—")
            msg = f"👑 مالک: `{o}`\n\n**ادمین‌ها:**\n"
            msg += "\n".join(f"• `{x}`" for x in a) if a else "—"
            bot.reply_to(message, msg)
            return

        if ncmd.startswith("admin") or ncmd.startswith("ادمین"):
            if not is_group(ck):
                bot.reply_to(message, "❌ این دستور فقط در گروه کار می‌کند."); return
            t = get_target(cmd, message)
            if not t:
                bot.reply_to(message, "❌ ریپلای کن یا بنویس: ادمین u0..."); return
            a = data.setdefault("admins", {}).setdefault(ck, [])
            if t in a:
                bot.reply_to(message, f"ℹ️ {t} از قبل ادمین است.")
            else:
                a.append(t); save_data(data)
                bot.reply_to(message, f"👑 {t} ادمین شد. (معاف از تمام محدودیت‌ها)")
            return

        if ncmd.startswith("demote") or ncmd.startswith("برکنار"):
            t = get_target(cmd, message)
            if not t:
                bot.reply_to(message, "❌ ریپلای کن یا بنویس: برکنار u0..."); return
            a = data.setdefault("admins", {}).setdefault(ck, [])
            if t in a: a.remove(t); save_data(data); bot.reply_to(message, f"🚫 {t} برکنار شد.")
            else: bot.reply_to(message, "ℹ️ ادمین نبود.")
            return

        if ncmd.startswith("clear") or ncmd.startswith("پاک"):
            p = cmd.replace("clear", "").replace("پاک", "").strip().split()
            if not p or not p[0].isdigit():
                bot.reply_to(message, "❌ پاک <۱-۵۰۰>"); return
            n = int(p[0])
            if not 1 <= n <= 500:
                bot.reply_to(message, "❌ ۱ تا ۵۰۰."); return
            d = 0
            for i in range(1, n + 1):
                tid = message.message_id - i
                if tid <= 0: break
                try: bot.delete_message(message.chat_id, tid); d += 1
                except: pass
            bot.reply_to(message, f"🧹 {d} پیام پاک شد.")
            return

        if ncmd in ("stats", "آمار"):
            w = data["warns"].get(ck, {}); b = data["banned"].get(ck, []); mc = data.get("msg_count", {}).get(ck, {})
            top = sorted(mc.items(), key=lambda x: -x[1])[:10]
            top_s = "\n".join(f"{i}. `{u}` — {c} پیام" for i, (u, c) in enumerate(top, 1)) or "—"
            f = data.get("filters", {}).get(ck, {})
            bot.reply_to(message,
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

        # ==================== سرگرمی ====================
        if ncmd in ("چالش", "challenge"):
            bot.reply_to(message, f"🎯 **چالش:**\n\n{random.choice(CHALLENGES)}"); return
        if ncmd in ("جرئت", "dare", "truthordare"):
            bot.reply_to(message, f"🎲 **جرئت یا حقیقت:**\n\n{random.choice(TRUTH_OR_DARE)}"); return
        if ncmd in ("بیو", "bio"):
            bot.reply_to(message, f"✨ **بیو:**\n\n{random.choice(BIOS)}"); return
        if ncmd in ("جرئت حقیقت", "deeptruth"):
            bot.reply_to(message, f"💭 **جرئت حقیقت (عمیق):**\n\n{random.choice(DEEP_TRUTH_OR_DARE)}"); return
        if ncmd in ("جوک", "joke"):
            bot.reply_to(message, f"😂 **جوک:**\n\n{random.choice(JOKES)}"); return
        if ncmd in ("بازی", "game", "games"):
            bot.reply_to(message,
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
    bot.polling()
