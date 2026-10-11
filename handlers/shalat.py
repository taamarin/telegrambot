import requests
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from requests.utils import quote

from handlers.user_store import increment_interaction
increment_interaction()

def get_prayer_times_by_city(city):
    city_encoded = quote(city)
    url = f"http://api.aladhan.com/v1/timingsByCity?city={city_encoded}&country=Indonesia&method=2"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data['code'] == 200:
                return data['data']['timings']
        return None
    except Exception as e:
        print(f"Error fetching prayer times: {e}")
        return None

# Handle untuk perintah manual /prayer
from handlers._admin import delete_message_after_delay
async def handle_prayer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        city = " ".join(context.args)
    else:
        sent_message = await update.message.reply_text(
            "❗ Format salah. Gunakan `/prayer <nama kota>`.\nContoh: `/prayer Banda Aceh`",
            parse_mode="Markdown"
        )
        asyncio.create_task(delete_message_after_delay(update.message, 60))
        asyncio.create_task(delete_message_after_delay(sent_message, 60))
        return

    times = get_prayer_times_by_city(city)
    if times:
        prayer_times = (
            f"🕌 **Prayer Times {city.title()}** 🕌\n"
            f"*Imsak*: {times['Imsak']}\n"
            f"*Fajr*: {times['Fajr']}\n"
            f"*Dhuhr*: {times['Dhuhr']}\n"
            f"*Asr*: {times['Asr']}\n"
            f"*Maghrib*: {times['Maghrib']}\n"
            f"*Isha*: {times['Isha']}\n\n"
        )
        sent_message = await update.message.reply_text(prayer_times, parse_mode="Markdown")
    else:
        sent_message = await update.message.reply_text(
            f"❌ Gagal mendapatkan waktu shalat untuk kota *{city.title()}*. Pastikan ejaan benar.",
            parse_mode="Markdown"
        )

    # Hapus pesan perintah dan balasan setelah 60 detik
    asyncio.create_task(delete_message_after_delay(update.message, 60))
    asyncio.create_task(delete_message_after_delay(sent_message, 60))

# Fungsi ambil waktu shalat dari API berdasarkan kota
def get_prayer_times(city="Banda Aceh"):
    url = f"http://api.aladhan.com/v1/timingsByCity?city={city}&country=Indonesia&method=2"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data['code'] == 200:
                return data['data']['timings']
        return None
    except Exception as e:
        print(f"Error fetching prayer times: {e}")
        return None

# Fungsi kirim ke grup
async def send_prayer_times_to_chat(context: ContextTypes.DEFAULT_TYPE, city="Banda Aceh"):
    times = get_prayer_times(city)
    if times:
        prayer_times = (
            f"🕌 **Prayer Times {city.title()}** 🕌\n"
            f"*Imsak*: {times['Imsak']}\n"
            f"*Fajr*: {times['Fajr']}\n"
            f"*Dhuhr*: {times['Dhuhr']}\n"
            f"*Asr*: {times['Asr']}\n"
            f"*Maghrib*: {times['Maghrib']}\n"
            f"*Isha*: {times['Isha']}\n"
        )
        chat_id = "-1001597117128"
        message_thread_id = "283465"
        await context.bot.send_message(
            chat_id=chat_id,
            text=prayer_times,
            message_thread_id=message_thread_id,
            parse_mode="Markdown"
        )

# Loop cek waktu shalat dan kirim otomatis
async def prayer_time_loop(context: ContextTypes.DEFAULT_TYPE, city="Banda Aceh"):
    already_sent = set()
    while True:
        times = get_prayer_times(city)
        if times:
            current_time = datetime.now().strftime("%H:%M")
            for name, prayer_time in times.items():
                if current_time == prayer_time and name not in already_sent:
                    await send_prayer_times_to_chat(context, city)
                    already_sent.add(name)
                    break
        await asyncio.sleep(60)

# Untuk memulai fitur otomatis
async def start_auto_prayer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Notifikasi otomatis waktu shalat dimulai.")
    asyncio.create_task(prayer_time_loop(context, city="Banda Aceh"))