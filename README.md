import telebot

# ضع هنا توكن البوت الذي حصلت عليه من BotFather
TOKEN = "9059288274:AAEk0m6pgxqR1rTIKrmySri6t4y70sDU4AY"

# ضع هنا معرف قناتك (مثلاً '@my_channel' أو المعرف الرقمي '-100xxxxxxxxxx')
CHANNEL_ID = "-1003713705463"

bot = telebot.TeleBot(TOKEN)


# استقبال أي صورة مع نص (Caption) يرسلها المالك للبوت
@bot.message_handler(content_types=['photo'])
def forward_photo_to_channel(message):
  try:
    # جلب أفضل جودة للصورة المرفقة
    photo_file_id = message.photo[-1].file_id
    # جلب النص المرافق للصورة إن وجد
    caption_text = message.caption if message.caption else ""

    # إرسال الصورة مباشرة للقناة مع النص
    bot.send_photo(
        chat_id=CHANNEL_ID, photo=photo_file_id, caption=caption_text
    )

    # رد تأكيد لك في المحادثة الخاصة مع البوت
    bot.reply_to(message, "تم نشر الصورة في القناة بنجاح! ✅")
  except Exception as e:
    bot.reply_to(message, f"حدث خطأ أثناء الإرسال: {e}")


# تشغيل البوت
print("Bot is running...")
bot.infinity_polling()
