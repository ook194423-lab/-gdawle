import os
import requests
import telebot
from flask import Flask
from threading import Thread

# 1. إعداد السيرفر الوهمي للإبقاء على البوت مستيقظاً 24/7 عبر ريندر
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

# تشغيل السيرفر في خلفية النظام
Thread(target=run_web, daemon=True).start()

# 2. سحب البيانات الحساسة من متغيرات البيئة (Environment Variables) لأمان تام
TOKEN = os.environ.get('9059288274:AAHPa-Q2K11KClD9Jen_NN-RMCHHbth-tN8')
CHANNEL_ID = int(os.environ.get('-1003713705463'))  # معرف القناة (مثال: -1001234567890)
API_USER = os.environ.get('700106778')
API_SECRET = os.environ.get('THw6tAtGMmjVg2grjKAoQtKZPiYWcoPT')

# حد الخطورة: أي نسبة عري تتجاوز هذا الرقم (0.5 يعني 50%) ستعتبر الصورة مخالفة وتُحذف فوراً
UNSAFE_THRESHOLD = 0.5

bot = telebot.TeleBot(TOKEN)

def is_image_safe(file_path):
    """
    دالة الفحص الصارمة: 
    ترجع True فقط إذا أكد الفحص بوضوح أن الصورة نظيفة وآمنة.
    أي خطأ في الاتصال، أو فشل في الرد، أو شك في المحتوى يرجع False (حظر الحذف فوراً).
    """
    try:
        with open(file_path, 'rb') as image_file:
            response = requests.post(
                'https://api.sightengine.com/1.0/check.json',
                files={'media': image_file},
                data={
                    'models': 'nudity-2.0',
                    'api_user': API_USER,
                    'api_secret': API_SECRET,
                },
                timeout=30,
            )

        result = response.json()
        print('Sightengine response:', result) # ستظهر لك نتيجة الفحص كاملة في سجلات Render

        # التحقق من نجاح عملية الاتصال بالـ API
        if result.get('status') != 'success':
            print('Sightengine failed or rejected the request, treating image as unsafe by default.')
            return False

        # استخراج نسب العري والمحتوى الحساس من الرد
        nudity = result.get('nudity', {})
        safe_score = nudity.get('safe', 1.0)
        sexual_score = max(
            nudity.get('sexual_activity', 0),
            nudity.get('sexual_display', 0),
            nudity.get('erotica', 0),
        )

        print(f'Calculated Scores -> safe={safe_score}, sexual_max={sexual_score}')

        # إذا تجاوزت نسبة المحتوى غير اللائق الحد المسموح، أو انخفضت نسبة الأمان بشكل كبير
        if sexual_score >= UNSAFE_THRESHOLD or safe_score < (1 - UNSAFE_THRESHOLD):
            return False
            
        return True
        
    except Exception as e:
        print('Critical error during image analysis (treated as unsafe):', e)
        return False # في حال حدث خطأ تقني، نعتبر الصورة غير آمنة ونحذفها كإجراء احترازي

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    temp_path = f'temp_{message.message_id}.jpg'
    safe = False

    try:
        # خطوة أ: جلب مسار الصورة من سيرفرات تليجرام وتنزيلها مؤقتاً
        file_info = bot.get_file(message.photo[-1].file_id)
        data = bot.download_file(file_info.file_path)
        with open(temp_path, 'wb') as f:
            f.write(data)
            
        # خطوة ب: تمرير الصورة لدالة الفحص الصارمة
        safe = is_image_safe(temp_path)
        
    except Exception as e:
        print('Error downloading or processing photo:', e)
        safe = False
        
    finally:
        # خطوة ج: تنظيف الذاكرة ومسح الملف المؤقت مهما كانت النتيجة
        if os.path.exists(temp_path):
            os.remove(temp_path)

    # خطوة د: القرار النهائي (الحذف أو الإرسال للقناة)
    if not safe:
        try:
            # حذف رسالة المستخدم من المحادثة فوراً لمنع ظهورها أو وصولها لأحد
            bot.delete_message(message.chat.id, message.message_id)
            print('Successfully deleted unsafe image message.')
        except Exception as e:
            print('Failed to delete message. Make sure the bot is an admin with delete permissions:', e)
        return

    # إذا اجتازت الصورة الفحص بنجاح تام، يتم توجيهها ونشرها في القناة المخصصة
    try:
        bot.send_photo(CHANNEL_ID, message.photo[-1].file_id,
                       caption=message.caption or '')
        print('Image verified and successfully posted to the channel.')
    except Exception as e:
        print('Failed to send photo to the channel:', e)

print("Bot is running with strict security filter...")
bot.infinity_polling()
