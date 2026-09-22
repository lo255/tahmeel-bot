import os
import re
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types
import yt_dlp

# --- إعداد السيرفر المصغر للبقاء نشطاً 24/7 على Render ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"Bot is Running 24/7 with Adsterra Monetization!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_http_server, daemon=True).start()

# --- إعداد البوت والبيانات ---
BOT_TOKEN = "7767260638:AAHKNqMRON2ghADKYHD-94lFInn1tvGUmXM"
AD_LINK = "https://www.profitableratecpmnetwork.com/a0m43e0w?key=9976f2ba3803fa34553592c3aeaf6f18"
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')

YOUTUBE_REGEX = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|shorts/|.+\?v=)?([^&=%\?]{11})'

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 <b>مرحباً بك في بوت تحميل الفيديوهات!</b>\n\n"
        "📥 أرسل لي أي رابط فيديو من يوتيوب لتحميله بصيغة فيديو MP4 أو مقطع صوتي MP3 بجودة عالية."
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()
    match = re.search(YOUTUBE_REGEX, url)
    
    if not match:
        bot.reply_to(message, "⚠️ يرجى إرسال رابط يوتيوب صحيح.")
        return

    status_msg = bot.reply_to(message, "🔎 جاري فحص الرابط وجلب بيانات الفيديو...")

    try:
        ydl_opts = {'quiet': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'فيديو يوتيوب')
            duration = info.get('duration', 0)
            uploader = info.get('uploader', 'غير معروف')
            thumbnail = info.get('thumbnail')
            video_id = info.get('id')

        minutes, seconds = divmod(duration, 60)
        time_format = f"{minutes:02d}:{seconds:02d}"

        caption = (
            f"🎬 <b>العنوان:</b> {title}\n"
            f"👤 <b>القناة:</b> {uploader}\n"
            f"⏱ <b>المدة:</b> {time_format}\n\n"
            f"👇 <i>اختر صيغة التحميل، أو اضغط زر الدعم لمساعدتنا على الاستمرار:</i>"
        )

        markup = types.InlineKeyboardMarkup(row_width=2)
        # زر الربح من Adsterra
        btn_ad = types.InlineKeyboardButton("🚀 سيرفر التحميل السريع (إعلان داعم)", url=AD_LINK)
        # أزرار التحميل
        btn_video = types.InlineKeyboardButton("🎥 فيديو MP4", callback_data=f"vid_{video_id}")
        btn_audio = types.InlineKeyboardButton("🎵 مقطع صوتي MP3", callback_data=f"aud_{video_id}")
        
        markup.add(btn_ad)
        markup.add(btn_video, btn_audio)

        bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)

        if thumbnail:
            bot.send_photo(message.chat.id, thumbnail, caption=caption, reply_markup=markup)
        else:
            bot.send_message(message.chat.id, caption, reply_markup=markup)

    except Exception as e:
        bot.edit_message_text(f"❌ حدث خطأ أثناء جلب الفيديو: {str(e)[:100]}", chat_id=message.chat.id, message_id=status_msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith(('vid_', 'aud_')))
def process_download(call):
    action, video_id = call.data.split('_', 1)
    url = f"https://www.youtube.com/watch?v={video_id}"
    chat_id = call.message.chat.id

    bot.answer_callback_query(call.id, "⏳ جاري بدء التنزيل والمعالجة...")
    progress_msg = bot.send_message(chat_id, "⏳ جاري التنزيل والرفع إلى تليجرام، انتظر لحظات...")

    out_tmpl = f"downloads/{video_id}_%(ext)s"
    os.makedirs("downloads", exist_ok=True)

    try:
        if action == "vid":
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'outtmpl': out_tmpl,
                'max_filesize': 50 * 1024 * 1024,
                'quiet': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)

            with open(filename, 'rb') as video_file:
                bot.send_video(chat_id, video_file, caption="✅ تم التحميل بنجاح بواسطة البوت.")
            if os.path.exists(filename):
                os.remove(filename)

        elif action == "aud":
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': f"downloads/{video_id}.%(ext)s",
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'max_filesize': 50 * 1024 * 1024,
                'quiet': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                filename = f"downloads/{video_id}.mp3"

            with open(filename, 'rb') as audio_file:
                bot.send_audio(chat_id, audio_file, caption="✅ تم استخراج الصوت بنجاح.")
            if os.path.exists(filename):
                os.remove(filename)

        bot.delete_message(chat_id, progress_msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ تعذر استكمال التحميل: {str(e)[:120]}", chat_id, progress_msg.message_id)

print("Bot is polling...")
bot.infinity_polling(skip_pending=True)
