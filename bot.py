import os
from threading import Thread
from flask import Flask
import telebot

# قراءة التوكن ومعرف القناة من إعدادات السيرفر (Environment Variables)
TOKEN = "9059288274:AAEk0m6pgxqR1rTIKrmySri6t4y70sDU4AY"
CHANNEL_ID = -1003713705463


bot = telebot.TeleBot(TOKEN)

# --- خادم ويب وهمي لإبقاء البوت يعمل مجاناً على السيرفر ---
app = Flask('')


@app.route('/')
def home():
  return 'Bot is running and active!'


def run_web():
  app.run(host='0.0.0.0', port=8080)


# تشغيل خادم الويب في الخلفية مع البوت
Thread(target=run_web).start()
# --------------------------------------------------------


# استقبال الصورة مع الوصف وإرسالها للقناة تلقائياً
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
    bot.reply_to(message, f"حدث خطأ أثناء الإرسال: {e}")


print("Bot is running...")
bot.infinity_polling()
