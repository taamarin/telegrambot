from telegram import Update
from telegram.ext import ContextTypes
from handlers._admin import delete_message_after_delay
import requests
import asyncio
from datetime import datetime
import pytz
import re

from handlers.user_store import increment_interaction
increment_interaction()

# Fungsi untuk memilih ikon berdasarkan kondisi cuaca
def get_weather_icon(description):
    desc = description.lower()
    if "clear" in desc:
        return "☀️"
    if "cloud" in desc:
        return "☁️"
    if "rain" in desc or "drizzle" in desc:
        return "🌧️"
    if "thunder" in desc:
        return "⛈️"
    if "snow" in desc:
        return "❄️"
    if "mist" in desc or "fog" in desc:
        return "🌫️"
    return "🌤️"
 
async def handle_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        sent = await update.message.reply_text(
            "/cuaca `<nama_kota>`", parse_mode="Markdown"
        )
        asyncio.create_task(delete_message_after_delay(update.message, 30))
        asyncio.create_task(delete_message_after_delay(sent, 30))
        return

    city = " ".join(context.args)
    loading = await update.message.reply_text("loading...")

    try:
        # Dapatkan koordinat kota dari OpenStreetMap (Nominatim)
        geo_url = f"https://nominatim.openstreetmap.org/search?format=json&q={city}"
        geo_res = requests.get(geo_url, headers={"User-Agent": "TelegramBot"})
        geo_data = geo_res.json()
        if not geo_data:
            await loading.edit_text(f"⚠️ Lokasi tidak ditemukan: *{city}*", parse_mode="Markdown")
            return

        lat = geo_data[0]["lat"]
        lon = geo_data[0]["lon"]
        display_name = geo_data[0]["display_name"].split(",")[0]

        # Ambil data cuaca dari Open-Meteo
        # weather_url = (
            # f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            # f"&current_weather=true&hourly=relativehumidity_2m,windspeed_10m"
        # )
        
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            f"&current_weather=true&hourly=relativehumidity_2m,windspeed_10m&timezone=auto"
        )

        weather_res = requests.get(weather_url)
        weather_data = weather_res.json()

        current = weather_data.get("current_weather", {})
        if not current:
            await loading.edit_text("⚠️ Data cuaca tidak tersedia.")
            return

        temp = current["temperature"]
        wind = current["windspeed"]
        weathercode = current["weathercode"]

        # Ambil kelembapan dari data hourly
        humidity = weather_data["hourly"]["relativehumidity_2m"][0]

        # Konversi kode cuaca ke ikon
        weather_descriptions = {
            0: "Clear",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Light rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Light snow",
            73: "Moderate snow",
            75: "Heavy snow",
            80: "Rain showers",
            95: "Thunderstorm",
        }
        description = weather_descriptions.get(weathercode, "Unknown")
        icon = get_weather_icon(description)


        local_time = current.get("time", "")  # Contoh: "2025-05-09T17:00"
        now = local_time[11:16] if "T" in local_time else "Tidak diketahui"

        message = (
            f"*{icon} Cuaca di {display_name}*\n"
            f"🕓 Perkiraan waktu lokal: `{now}`\n"
            f"🌡️ Suhu: `{temp}°C`\n"
            f"💧 Kelembaban: `{humidity}%`\n"
            f"🌬️ Angin: `{wind} km/jam`\n"
            f"📖 Deskripsi: _{description}_"
        )

        await loading.edit_text(message, parse_mode="Markdown")
        asyncio.create_task(delete_message_after_delay(update.message, 60))
        asyncio.create_task(delete_message_after_delay(loading, 60))

    except Exception as e:
        await loading.edit_text(f"Terjadi kesalahan:\n`{e}`", parse_mode="Markdown")
        asyncio.create_task(delete_message_after_delay(update.message, 30))
        asyncio.create_task(delete_message_after_delay(loading, 30))