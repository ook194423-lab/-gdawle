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
TOKEN = '9059288274:AAEvcvGCouaaJxPF0VoSprcYT5nmp89HE2A'
CHANNEL_ID = -1003713705463

# مفاتيح حسابك في Sightengine
API_USER = '700106778'
API_SECRET = 'THw6tAtGMmjVg2grjKAoQtKZPiYWcoPT'

bot = telebot.TeleBot(TOKEN)


def check_image_safety_by_upload(file_path):
  """دالة لفحص الصورة مع طباعة النتيجة في السجلات لمعرفة السبب"""
  try:
    with open(file_path, 'rb') as image_file:
      files = {'media': image_file}
      data = {
          'models': 'nudity-2.0,wad,offensive',
          'api_user': API_USER,
          'api_secret': API_SECRET,
      }
      response = requests.post(
          'https://api.sightengine.com/1.0/check.json',
          files=files,
          data=data,
      )
      output = response.json()
      print(
          'API Response:', output
      )  # ستطبع النتيجة حرفياً في سجلات Render لتراها

      if output.get('status') == 'success':
        nudity_safe = output.get('nudity', {}).get('safe', 1.0)
        print(f'Nudity Safe Score: {nudity_safe}')  # طباعة نسبة الأمان

        # إذا كانت نسبة الأمان أقل من 95% (نجعلها صارمة جداً للتجربة)
        if nudity_safe < 0.95:
          return False
    return True
  except Exception as e:
    print(f'Error in check exception: {e}')
    return True


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
  try:
    # تحميل الصورة المؤقتة من سيرفرات تليجرام إلى جهاز البوت محلياً لفحصها
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    temp_path = 'temp_image.jpg'
    with open(temp_path, 'wb') as new_file:
      new_file.write(downloaded_file)

    # فحص الصورة بالتنفيذ المباشر
    is_safe = check_image_safety_by_upload(temp_path)

    # حذف الملف المؤقت من الذاكرة
    if os.path.exists(temp_path):
      os.remove(temp_path)

    if not is_safe:
      # إذا كانت الصورة مخالفة: احذف رسالة المستخدم فوراً من الشات ولا تنشرها
      try:
        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
      except Exception:
        pass
      return

    # إذا كانت الصورة آمنة ونظيفة: انشرها في القناة فوراً
    photo_file_id = message.photo[-1].file_id
    caption_text = message.caption if message.caption else ''
    bot.send_photo(
        chat_id=CHANNEL_ID, photo=photo_file_id, caption=caption_text
    )

  except Exception as e:
    print(f'Error: {e}')


print('Bot is running with strict direct-upload filter...')
bot.infinity_polling()
