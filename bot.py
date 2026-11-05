import os
from threading import Thread
from flask import Flask
import requests
import telebot

# 1. السيرفر الوهمي لإبقاء البوت مستيقظاً على Render
app = Flask('')


@app.route('/')
def home():
  return 'Bot is running!'


def run_web():
  app.run(host='0.0.0.0', port=8080)


Thread(target=run_web).start()

# 2. إعدادات البوت والاتصال
TOKEN = '9059288274:AAFMYLkHh9rk4EGSpW7v7LBa1rGEncEm3Lg'
CHANNEL_ID = -1003713705463

# بيانات الفحص المجاني (Sightengine API) أو يمكنك استخدام مفاتيح تجريبية مجانية
API_USER = '700106778&api_secret=THw6tAtGMmjVg2grjKAoQtKZPiYWcoPT'
API_SECRET = 'THw6tAtGMmjVg2grjKAoQtKZPiYWcoPT'

bot = telebot.TeleBot(TOKEN)


def check_image_safety(photo_url):
  """دالة برمجية تفحص الصورة وتحدد ما إذا كانت آمنة أم لا"""
  try:
    params = {
        'url': photo_url,
        'models': 'nudity-2.0,wad,offensive',
        'api_user': API_USER,
        'api_secret': API_SECRET,
    }
    response = requests.get(
        'https://api.sightengine.com/1.0/check.json', params=params
    )
    output = response.json()

    if output['status'] == 'success':
      nudity_safe = output.get('nudity', {}).get('safe', 1.0)
      # إذا كانت نسبة الأمان أقل من الطبيعي، تعتبر الصورة مخالفة
      if nudity_safe < 0.8:
        return False
    return True
  except Exception:
    return True  # للسماح بمرور الصورة مؤقتاً في حال حدث ضغط بالاتترنت


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
  try:
    # الحصول على مسار الصورة المرسلة
    file_info = bot.get_file(message.photo[-1].file_id)
    photo_url = f'https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}'

    # فحص الصورة برمجياً
    is_safe = check_image_safety(photo_url)

    if not is_safe:
      # إذا كانت غير لائقة: احذف رسالة المستخدم فوراً ولا تنشرها في القناة
      try:
        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
      except Exception:
        pass
      return

    # إذا كانت الصورة نظيفة وآمنة: يتم نشرها في القناة مباشرة
    photo_file_id = message.photo[-1].file_id
    caption_text = message.caption if message.caption else ''
    bot.send_photo(
        chat_id=CHANNEL_ID, photo=photo_file_id, caption=caption_text
    )

  except Exception as e:
    print(f'Error: {e}')


print('Bot is running with auto-delete filter...')
bot.infinity_polling()
