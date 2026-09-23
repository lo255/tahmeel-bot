import os
import re
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types
import yt_dlp

# سيرفر لإبقاء الخدمة تعمل 24 ساعة دون توقف على Render
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"Bot is alive and running 24/7!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), KeepAliveHandler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# بيانات البوت
BOT_TOKEN = "7767260638:AAHKNqMRON2ghADKYHD-94lFInn1tvGUmXM"
# رابط موجه لقناة تليجرام لتجنب خطأ 500 (يمكنك تغييره لاحقاً برابط Adsterra فعال)
AD_LINK = "https://t.me/telegram"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')

YOUTUBE_REGEX = r'(https?://)?(www\.|m\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|shorts/|.+\?v=)?([^&=%\?]{11})'

def get_base_ydl_opts():
    opts = {
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 20,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'tv']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
            'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8',
        }
    }
    for name in ["cookies.txt", "cookies.txt.txt"]:
        if os.path.exists(name) and os.path.getsize(name) > 0:
            opts['cookiefile'] = name
            break
    return opts

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🚀 سيرفر التحميل المباشر", url=AD_LINK))
    welcome_text = (
        "👋 <b>مرحباً بك في بوت تحميل الفيديوهات جوكر!</b>\n\n"
        "📥 أرسل لي رابط فيديو من يوتيوب لتحميله بصيغة MP4 أو MP3 بجودة عالية."
    )
    bot.reply_to(message, welcome_text, reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()
    match = re.search(YOUTUBE_REGEX, url)
    
    if not match:
        bot.reply_to(message, "⚠️ يرجى إرسال رابط يوتيوب صحيح.")
        return

    video_id = match.group(6)
    clean_url = f"https://www.youtube.com/watch?v={video_id}"
    status_msg = bot.reply_to(message, "🔎 جاري فحص الرابط واستخراج الفيديو...")

    try:
        ydl_opts = get_base_ydl_opts()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=False)
            title = info.get('title', 'فيديو يوتيوب')
            duration = info.get('duration', 0)
            uploader = info.get('uploader', 'غير معروف')
            thumbnail = info.get('thumbnail')

        minutes, seconds = divmod(duration, 60)
        time_format = f"{minutes:02d}:{seconds:02d}"

        caption = (
            f"🎬 <b>العنوان:</b> {title}\n"
            f"👤 <b>القناة:</b> {uploader}\n"
            f"⏱ <b>المدة:</b> {time_format}\n\n"
            f"👇 <i>اختر صيغة التحميل:</i>"
        )

        markup = types.InlineKeyboardMarkup(row_width=2)
        btn_video = types.InlineKeyboardButton("🎥 فيديو MP4", callback_data=f"vid_{video_id}")
        btn_audio = types.InlineKeyboardButton("🎵 مقطع صوتي MP3", callback_data=f"aud_{video_id}")
        btn_ad = types.InlineKeyboardButton("🚀 سيرفر الدعم السريع", url=AD_LINK)
        markup.add(btn_video, btn_audio)
        markup.add(btn_ad)

        bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)

        if thumbnail:
            bot.send_photo(message.chat.id, thumbnail, caption=caption, reply_markup=markup)
        else:
            bot.send_message(message.chat.id, caption, reply_markup=markup)

    except Exception as e:
        err_markup = types.InlineKeyboardMarkup()
        err_markup.add(types.InlineKeyboardButton("🚀 سيرفر بديل", url=AD_LINK))
        bot.edit_message_text(
            f"❌ تعذر استخراج الفيديو: {str(e)[:120]}", 
            chat_id=message.chat.id, 
            message_id=status_msg.message_id, 
            reply_markup=err_markup
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith(('vid_', 'aud_')))
def process_download(call):
    action, video_id = call.data.split('_', 1)
    url = f"https://www.youtube.com/watch?v={video_id}"
    chat_id = call.message.chat.id

    bot.answer_callback_query(call.id, "⏳ جاري بدء التنزيل والمعالجة...")
    progress_msg = bot.send_message(chat_id, "⏳ جاري التنزيل والرفع، انتظر لحظات...")

    out_tmpl = f"downloads/{video_id}_%(ext)s"
    os.makedirs("downloads", exist_ok=True)

    try:
        ydl_opts = get_base_ydl_opts()
        if action == "vid":
            ydl_opts.update({
                'format': 'best[ext=mp4]/best',
                'outtmpl': out_tmpl,
                'max_filesize': 49 * 1024 * 1024,
            })
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)

            with open(filename, 'rb') as video_file:
                bot.send_video(chat_id, video_file, caption="✅ تم التحميل بنجاح!")
            if os.path.exists(filename):
                os.remove(filename)

        elif action == "aud":
            ydl_opts.update({
                'format': 'bestaudio/best',
                'outtmpl': f"downloads/{video_id}.%(ext)s",
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'max_filesize': 49 * 1024 * 1024,
            })
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                filename = f"downloads/{video_id}.mp3"

            with open(filename, 'rb') as audio_file:
                bot.send_audio(chat_id, audio_file, caption="✅ تم استخراج الصوت بنجاح!")
            if os.path.exists(filename):
                os.remove(filename)

        bot.delete_message(chat_id, progress_msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ تعذر استكمال التحميل: {str(e)[:120]}", chat_id, progress_msg.message_id)

print("Bot service is starting...")
while True:
    try:
        bot.infinity_polling(timeout=20, long_polling_timeout=20)
    except Exception as e:
        time.sleep(3)
