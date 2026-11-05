import os
from threading import Thread
from flask import Flask
import telebot

# --- 1. كود السيرفر الوهمي لإبقاء البوت مستيقظاً ---
app = Flask('')


@app.route('/')
def home():
  return 'Bot is running!'


def run_web():
  app.run(host='0.0.0.0', port=8080)


# تشغيل السيرفر في الخلفية
Thread(target=run_web).start()
# -----------------------------------------------

# --- 2. إعدادات بوت التليجرام ---
TOKEN = "9059288274:AAEk0m6pgxqR1rTIKrmySri6t4y70sDU4AY"
CHANNEL_ID = -1004336205957

bot = telebot.TeleBot(TOKEN)


@bot.message_handler(content_types=['photo'])
def forward_photo_to_channel(message):
  try:
    photo_file_id = message.photo[-1].file_id
    caption_text = message.caption if message.caption else ""
    bot.send_photo(
        chat_id=CHANNEL_ID, photo=photo_file_id, caption=caption_text
    )
    bot.reply_to(message, "تم نشر الصورة في القناة بنجاح! ✅")
  except Exception as e:
    bot.reply_to(message, f"حدث خطأ: {e}")


print('Bot is running...')
bot.infinity_polling()
