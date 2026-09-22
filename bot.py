import os
import re
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types
import yt_dlp

# إعدادات البوت
BOT_TOKEN = "7767260638:AAHKNqMRON2ghADKYHD-94lFInn1tvGUmXM"
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

YDL_COMMON_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
}

def extract_yt_id(url):
    pattern = r'(?:youtu\.be\/|youtube\.com\/(?:watch\?(?:.*&)?v=|(?:embed|v|shorts)\/))([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def format_duration(seconds):
    sec = int(seconds or 0)
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def format_views(count):
    n = int(count or 0)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    if n >= 1_000:
        return f"{round(n / 1_000)}K"
    return str(n)

@bot.message_handler(commands=['start', 'help'])
def start_cmd(message):
    bot.send_message(
        message.chat.id,
        "👋 <b>مرحباً بك في بوت تحميل الميديا!</b> 📥\n\n"
        "أرسل رابط أي مقطع من يوتيوب لتحميله كفيديو أو صوت فوراً وبأعلى جودة."
    )

@bot.message_handler(func=lambda msg: msg.text and ("youtube.com" in msg.text or "youtu.be" in msg.text))
def handle_youtube_link(message):
    chat_id = message.chat.id
    raw_url = message.text.strip()
    video_id = extract_yt_id(raw_url)

    if not video_id:
        bot.reply_to(message, "⚠️ الرابط غير صالح، تأكد من صحة الرابط المرسل.")
        return

    search_msg = bot.send_message(chat_id, f'🔎 جاري البحث عن "{raw_url}"...', reply_to_message_id=message.message_id)

    try:
        with yt_dlp.YoutubeDL(YDL_COMMON_OPTS) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            
            title = info.get('title', 'مقطع فيديو يوتيوب')
            channel = info.get('uploader', 'قناة يوتيوب')
            duration = format_duration(info.get('duration', 0))
            views = format_views(info.get('view_count', 0))
            thumbnail_url = info.get('thumbnail') or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

        caption = (
            f"🎬 {title}\n"
            f"👤 {channel}\n"
            f"⏱️ {duration} - 👁️ {views}"
        )

        markup = types.InlineKeyboardMarkup(row_width=2)
        b_video = types.InlineKeyboardButton("🎥 مقطع فيديو", callback_data=f"vid_{video_id}")
        b_audio = types.InlineKeyboardButton("🎵 مقطع صوتي", callback_data=f"aud_{video_id}")
        markup.add(b_video, b_audio)

        bot.send_photo(chat_id, thumbnail_url, caption=caption, reply_markup=markup)
        bot.delete_message(chat_id, search_msg.message_id)

    except Exception:
        bot.send_message(chat_id, "❌ تعذر جلب معلومات هذا المقطع، يرجى المحاولة لاحقاً.")
        try:
            bot.delete_message(chat_id, search_msg.message_id)
        except Exception:
            pass

@bot.callback_query_handler(func=lambda call: call.data.startswith(("vid_", "aud_")))
def handle_download_action(call):
    chat_id = call.message.chat.id
    action, video_id = call.data.split("_")
    yt_url = f"https://www.youtube.com/watch?v={video_id}"

    if action == "vid":
        bot.answer_callback_query(call.id, "⏳ جاري تنزيل الفيديو...")
        status_msg = bot.send_message(chat_id, "⚡ <b>جاري سحب الفيديو، انتظر ثوانٍ...</b>")
        file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}_{int(time.time())}.mp4")

        ydl_opts = {
            **YDL_COMMON_OPTS,
            'format': 'best[ext=mp4][height<=720]/best[ext=mp4]/best',
            'outtmpl': file_path,
            'max_filesize': 48 * 1024 * 1024
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([yt_url])

            if os.path.exists(file_path):
                with open(file_path, 'rb') as vf:
                    bot.send_video(chat_id, vf, caption="✅ <b>تم تنزيل الفيديو بنجاح!</b>")
                os.remove(file_path)
                bot.delete_message(chat_id, status_msg.message_id)
        except Exception:
            bot.send_message(chat_id, "❌ تعذر تنزيل الفيديو (حجمه قد يتجاوز 50 ميجابايت).")
            if os.path.exists(file_path):
                os.remove(file_path)

    elif action == "aud":
        bot.answer_callback_query(call.id, "⏳ جاري استخراج المقطع الصوتي...")
        status_msg = bot.send_message(chat_id, "🎵 <b>جاري استخراج الصوت، انتظر قليلاً...</b>")
        file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}_{int(time.time())}.m4a")

        ydl_opts = {
            **YDL_COMMON_OPTS,
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'outtmpl': file_path,
            'max_filesize': 48 * 1024 * 1024
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([yt_url])

            if os.path.exists(file_path):
                with open(file_path, 'rb') as af:
                    bot.send_audio(chat_id, af, caption="✅ <b>تم تنزيل المقطع الصوتي بنجاح!</b>")
                os.remove(file_path)
                bot.delete_message(chat_id, status_msg.message_id)
        except Exception:
            bot.send_message(chat_id, "❌ تعذر استخراج الصوت لهذا المقطع.")
            if os.path.exists(file_path):
                os.remove(file_path)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running 24/7")

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

if __name__ == "__main__":
    t = threading.Thread(target=run_health_server, daemon=True)
    t.start()
    print("🚀 Joker Tahmeel Bot Engine is active 24/7...")
    bot.infinity_polling()
