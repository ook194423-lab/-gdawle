import os
import time  # ← هنا
import requests
import telebot
from flask import Flask
from threading import Thread

# ... باقي الملف كما هو ...

def analyze_image(file_path):
    start = time.time()  # ← قبل الطلب

    with open(file_path, 'rb') as image_file:
        response = requests.post(
            'https://api.sightengine.com/1.0/check.json',
            files={'media': image_file},
            data={
                'models': MODELS,
                'api_user': API_USER,
                'api_secret': API_SECRET,
            },
            timeout=30,
        )

    print(f'Sightengine took {time.time() - start:.2f}s')  # ← بعد الطلب

    result = response.json()
    # ... باقي الدالة كما هو

# 1. السيرفر الوهمي لإبقاء الخدمة حيّة على Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, use_reloader=False)

Thread(target=run_web).start()

# 2. الإعدادات من Environment Variables
REQUIRED = ['BOT_TOKEN', 'CHANNEL_ID', 'SIGHTENGINE_USER', 'SIGHTENGINE_SECRET']
missing = [k for k in REQUIRED if not os.environ.get(k)]
if missing:
    raise SystemExit(f"Missing environment variables: {missing}")

TOKEN = os.environ['9059288274:AAHs2T9yGu32M62yijjU72UBcZbbLIfQRwE']
CHANNEL_ID = int(os.environ['-1003713705463'])
API_USER = os.environ['700106778']
API_SECRET = os.environ['THw6tAtGMmjVg2grjKAoQtKZPiYWcoPT']

MODELS = 'nudity-2.0,gore-2.0,wad,offensive,genai,qr-content,text-content'

THRESHOLDS = {
    'nudity': 0.5,
    'gore': 0.5,
    'weapons': 0.6,
    'alcohol': 0.7,
    'drugs': 0.6,
    'hate': 0.5,
    'ai_generated': 0.9,
    'text_harm': 0.5,
}

# 3. إعدادات التحذير والحظر
MAX_WARNINGS = 2        # التحذير الأول والثاني، والثالث يطبّق العقوبة
ENABLE_BAN = False      # اجعله True بعد نجاح الاختبار
WARNINGS = {}           # user_id -> عدد التحذيرات (يُمسح عند إعادة تشغيل الخدمة)

ERROR_MARK = 'ERROR'

bot = telebot.TeleBot(TOKEN)

def num(value):
    if isinstance(value, dict):
        value = value.get('prob', 0)
    return float(value) if isinstance(value, (int, float)) else 0.0

def has_matches(obj):
    return isinstance(obj, dict) and len(obj.get('matches', [])) > 0

def analyze_image(file_path):
    """يرجع (True, []) للصورة النظيفة، أو (False, [أسباب]) للمخالفة،
    أو (False, [ERROR_MARK]) عند فشل تقني."""
    with open(file_path, 'rb') as image_file:
        response = requests.post(
            'https://api.sightengine.com/1.0/check.json',
            files={'media': image_file},
            data={
                'models': MODELS,
                'api_user': API_USER,
                'api_secret': API_SECRET,
            },
            timeout=30,
        )

    result = response.json()
    print('Sightengine response:', result)

    if result.get('status') != 'success':
        return False, [ERROR_MARK]

    nudity = result.get('nudity', {})
    text = result.get('text', {})

    scores = {
        'nudity': max(
            num(nudity.get('sexual_activity', 0)),
            num(nudity.get('sexual_display', 0)),
            num(nudity.get('erotica', 0)),
        ),
        'gore': num(result.get('gore', {})),
        'weapons': num(result.get('weapon', 0)),
        'alcohol': num(result.get('alcohol', 0)),
        'drugs': num(result.get('drugs', 0)),
        'hate': num(result.get('offensive', {})),
        'ai_generated': num(result.get('type', {}).get('ai_generated', 0)),
        'text_harm': 1.0 if (has_matches(text.get('profanity'))
                             or has_matches(text.get('moderation'))) else 0.0,
    }

    reasons = [name for name, value in scores.items()
               if value >= THRESHOLDS.get(name, 1.0)]

    if has_matches(result.get('qr')) or has_matches(result.get('barcode')):
        reasons.append('qr_barcode')

    print('Scores:', scores, 'Reasons:', reasons)
    return len(reasons) == 0, reasons

def apply_penalty(chat_id, user_id):
    """يرجع نص العقوبة للمستخدم ويطبّق الحظر إذا كان مفعّلاً."""
    WARNINGS[user_id] = WARNINGS.get(user_id, 0) + 1
    count = WARNINGS[user_id]

    if count <= MAX_WARNINGS:
        return f"⚠️ تحذير {count}/{MAX_WARNINGS}"

    if ENABLE_BAN:
        try:
            bot.ban_chat_member(chat_id, user_id)
            return "🚫 تم حظر المستخدم بعد تجاوز عدد التحذيرات"
        except Exception as e:
            print('Ban failed (check bot admin rights):', e)
            return "⚠️ تجاوز عدد التحذيرات (تعذّر الحظر، تحقق من صلاحيات البوت)"

    return "⚠️ تجاوز عدد التحذيرات (الحظر غير مفعّل بعد)"

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    temp_path = f'temp_{message.message_id}.jpg'

    status_msg = bot.reply_to(message, "يتم تحليل الصورة المرفقة..")

    safe, reasons = False, [ERROR_MARK]
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        data = bot.download_file(file_info.file_path)
        with open(temp_path, 'wb') as f:
            f.write(data)
        safe, reasons = analyze_image(temp_path)
    except Exception as e:
        print('Check error:', e)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    # 1. الصورة نظيفة: إرسال للقناة
    if safe:
        try:
            bot.send_photo(CHANNEL_ID, message.photo[-1].file_id,
                           caption=message.caption or '')
            print('Sent to channel.')
            bot.edit_message_text("تم ارسال الصورة ✅", chat_id, status_msg.message_id)
        except Exception as e:
            print('Send to channel failed:', e)
            bot.edit_message_text(f"فشل الإرسال للقناة: {e}", chat_id, status_msg.message_id)
        return

    # 2. الصورة مخالفة أو فشل التحليل: حذف الصورة
    try:
        bot.delete_message(chat_id, message.message_id)
        print('Deleted image. Reasons:', reasons)
    except Exception as e:
        print('Delete failed (check bot admin rights):', e)

    # 3. فشل تقني: لا يُحسب تحذير على المستخدم
    if reasons == [ERROR_MARK]:
        text = "⚠️ تعذّر تحليل الصورة، لم يتم ارسال الصورة ❌"
    else:
        penalty = apply_penalty(chat_id, user_id)
        text = f"لم يتم ارسال الصورة ❌\n{penalty}"

    try:
        bot.edit_message_text(text, chat_id, status_msg.message_id)
    except Exception as e:
        print('Edit status failed:', e)

print("Bot is running with multi-category filter...")
bot.infinity_polling(timeout=20, long_polling_timeout=20)
