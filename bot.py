import os
import re
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types
import yt_dlp

# --- سيرفر HTTP لإبقاء الخدمة حية 24/7 على Render ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"Bot is Running 24/7 with Cookies & Adsterra!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_http_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_http_server, daemon=True).start()

# --- إعدادات البوت والربح ---
BOT_TOKEN = "7767260638:AAHKNqMRON2ghADKYHD-94lFInn1tvGUmXM"
AD_LINK = "https://www.profitableratecpmnetwork.com/a0m43e0w?key=9976f2ba3803fa34553592c3aeaf6f18"
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')

YOUTUBE_REGEX = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|shorts/|.+\?v=)?([^&=%\?]{11})'

def get_base_ydl_opts():
    opts = {
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android_creator', 'ios', 'tv']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }
    possible_names = ["cookies.txt", "cookies.txt.txt", "youtube.com_cookies.txt"]
    for name in possible_names:
        if os.path.exists(name):
            opts['cookiefile'] = name
            break
        full_path = os.path.join(os.path.dirname(__file__), name)
        if os.path.exists(full_path):
            opts['cookiefile'] = full_path
            break
    return opts

# رسالة الترحيب مع زر إعلان Adsterra
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    btn_ad = types.InlineKeyboardButton("🚀 سيرفر التحميل السريع (إعلان داعم)", url=AD_LINK)
    markup.add(btn_ad)
    
    welcome_text = (
        "👋 <b>مرحباً بك في بوت تحميل الفيديوهات جوكر!</b>\n\n"
        "📥 أرسل لي أي رابط فيديو من يوتيوب لتحميله بصيغة MP4 أو MP3 بجودة عالية.\n\n"
        "⚡ اضغط الزر بالأسفل لدعم استمرار السيرفر:"
    )
    bot.reply_to(message, welcome_text, reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()
    match = re.search(YOUTUBE_REGEX, url)
    
    if not match:
        bot.reply_to(message, "⚠️ يرجى إرسال رابط يوتيوب صحيح.")
        return

    status_msg = bot.reply_to(message, "🔎 جاري فحص الرابط عبر الكوكيز وتجهيز التحميل...")

    try:
        ydl_opts = get_base_ydl_opts()
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
            f"👇 <i>اختر صيغة التحميل:</i>"
        )

        markup = types.InlineKeyboardMarkup(row_width=2)
        btn_ad = types.InlineKeyboardButton("🚀 سيرفر التحميل السريع (إعلان)", url=AD_LINK)
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
        err_markup = types.InlineKeyboardMarkup()
        err_markup.add(types.InlineKeyboardButton("🚀 سيرفر التحميل البديل (إعلان)", url=AD_LINK))
        bot.edit_message_text(f"❌ تعذر استخراج الفيديو: {str(e)[:120]}", 
                              chat_id=message.chat.id, 
                              message_id=status_msg.message_id, 
                              reply_markup=err_markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith(('vid_', 'aud_')))
def process_download(call):
    action, video_id = call.data.split('_', 1)
    url = f"https://www.youtube.com/watch?v={video_id}"
    chat_id = call.message.chat.id

    bot.answer_callback_query(call.id, "⏳ جاري بدء التنزيل والمعالجة...")
    
    ad_box = types.InlineKeyboardMarkup()
    ad_box.add(types.InlineKeyboardButton("🚀 تسريع التحميل عبر السيرفر الداعم (إعلان)", url=AD_LINK))
    progress_msg = bot.send_message(chat_id, "⏳ جاري التنزيل والرفع، انتظر ثوانٍ معدودة...", reply_markup=ad_box)

    out_tmpl = f"downloads/{video_id}_%(ext)s"
    os.makedirs("downloads", exist_ok=True)

    try:
        ydl_opts = get_base_ydl_opts()
        if action == "vid":
            ydl_opts.update({
                'format': 'best[ext=mp4]/best',
                'outtmpl': out_tmpl,
                'max_filesize': 50 * 1024 * 1024,
            })
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)

            with open(filename, 'rb') as video_file:
                bot.send_video(chat_id, video_file, caption="✅ تم التحميل بنجاح بواسطة البوت.")
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
                'max_filesize': 50 * 1024 * 1024,
            })
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

# معالجة ذكية لتجاوز تعارض النسخ (Conflict 409) دون إيقاف السيرفر
print("Bot service is starting...")
while True:
    try:
        bot.polling(none_stop=True, timeout=20)
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code == 409:
            print("Conflict 409 detected. Waiting 6 seconds for old instance to terminate...")
            time.sleep(6)
        else:
            print(f"Telegram API Exception: {e}")
            time.sleep(4)
    except Exception as e:
        print(f"General polling error: {e}")
        time.sleep(4)
