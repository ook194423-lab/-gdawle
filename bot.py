import os
import requests
import telebot
from flask import Flask
from threading import Thread

# 1. السيرفر الوهمي
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run_web, daemon=True).start()

# 2. الإعدادات من Environment Variables في Render
TOKEN = os.environ.get('9059288274:AAHPa-Q2K11KClD9Jen_NN-RMCHHbth-tN8')
CHANNEL_ID = int(os.environ.get('-1003713705463'))
API_USER = os.environ.get('700106778')
API_SECRET = os.environ.get('THw6tAtGMmjVg2grjKAoQtKZPiYWcoPT')

# النماذج المطلوبة في طلب واحد
MODELS = 'nudity-2.0,wad,offensive,gore-2.0,genai,qr-content,text-content'

# حدود الحذف لكل تصنيف (0 إلى 1)
THRESHOLDS = {
    'nudity': 0.5,
    'gore': 0.5,
    'violence': 0.5,
    'weapons': 0.6,
    'alcohol': 0.7,
    'drugs': 0.6,
    'hate': 0.5,
    'ai_generated': 0.9,
    'text_harm': 0.6,
}

bot = telebot.TeleBot(TOKEN)

def num(value):
    """يحوّل القيمة إلى رقم، سواء كانت رقماً مباشراً أو كائناً فيه prob."""
    if isinstance(value, dict):
        value = value.get('prob', 0)
    return float(value) if isinstance(value, (int, float)) else 0.0

def analyze_image(file_path):
    """يرجع (True, []) إذا الصورة نظيفة، أو (False, [أسباب]) إذا مخالفة.
    أي فشل في الفحص يرجع False (مبدأ الحذف عند الشك)."""
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
        return False, ['فشل الفحص']

    nudity = result.get('nudity', {})
    scores = {
        'nudity': max(
            nudity.get('sexual_activity', 0),
            nudity.get('sexual_display', 0),
            nudity.get('erotica', 0),
        ),
        'gore': num(result.get('gore', {})),
        'violence': num(result.get('gore', {})),
        'weapons': num(result.get('weapon', result.get('wad', {}).get('weapon', 0))),
        'alcohol': num(result.get('alcohol', result.get('wad', {}).get('alcohol', 0))),
        'drugs': num(result.get('drugs', result.get('wad', {}).get('drugs', 0))),
        'hate': num(result.get('offensive', {})),
        'ai_generated': num(result.get('type', {}).get('ai_generated', 0)),
    }

    # النصوص: الشتائم والمحتوى المؤذي في الصورة
    text = result.get('text', {})
    scores['text_harm'] = max(
        num(text.get('profanity', {})),
        num(text.get('moderation', {})),
    )

    reasons = [name for name, value in scores.items()
               if value >= THRESHOLDS.get(name, 1.0)]

    # الباركود وQR: أي نتيجة تعتبر مخالفة حسب سياستك
    if result.get('qr', {}).get('matches') or result.get('barcode', {}).get('matches'):
        reasons.append('qr_barcode')

    print('Scores:', scores, 'Reasons:', reasons)
    return len(reasons) == 0, reasons

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    temp_path = f'temp_{message.message_id}.jpg'
    safe, reasons = False, ['خطأ غير متوقع']

    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        data = bot.download_file(file_info.file_path)
        with open(temp_path, 'wb') as f:
            f.write(data)
        safe, reasons = analyze_image(temp_path)
    except Exception as e:
        print('Check error (treated as unsafe):', e)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    if not safe:
        print('Blocked. Reasons:', reasons)
        try:
            bot.delete_message(message.chat.id, message.message_id)
            print('Deleted unsafe image.')
        except Exception as e:
            print('Delete failed (check bot admin rights):', e)
        return

    try:
        bot.send_photo(CHANNEL_ID, message.photo[-1].file_id,
                       caption=message.caption or '')
    except Exception as e:
        print('Send to channel failed:', e)

print("Bot is running with multi-category filter...")
bot.infinity_polling()
