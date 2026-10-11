import asyncio
import subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from handlers._admin import delete_message_after_delay, is_admin

# Fungsi untuk menjalankan perintah shell ADB
def run_adb_command(cmd: str) -> str:
    try:
        result = subprocess.check_output(cmd, shell=True, text=True)
        return result.strip()
    except subprocess.CalledProcessError as e:
        return f"Error: {e.output.strip()}" if e.output else "Perintah gagal dijalankan."

# Handler untuk perintah .tcp
async def tcp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("algoritma", callback_data='cek_tersedia'),
         InlineKeyboardButton("algoritma aktif", callback_data='cek_aktif')],
        [InlineKeyboardButton("set BBR", callback_data='set_bbr'),
         InlineKeyboardButton("set Westwood", callback_data='set_westwood')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Pilih aksi TCP:", reply_markup=reply_markup)

# Handler untuk aksi tombol
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    username = query.from_user.mention_html()

    await query.answer()

    if not is_admin(user_id):
        sent_message = await query.message.reply_html(f"{username} bukan admin, bro.")
        asyncio.create_task(delete_message_after_delay(query.message, 30))
        asyncio.create_task(delete_message_after_delay(sent_message, 30))
        return

    command_map = {
        'cek_tersedia': "adb shell 'su -c cat /proc/sys/net/ipv4/tcp_available_congestion_control'",
        'cek_aktif': "adb shell 'su -c cat /proc/sys/net/ipv4/tcp_congestion_control'",
        'set_bbr': "adb shell \"su -c 'echo bbr | tee /proc/sys/net/ipv4/tcp_congestion_control'\"",
        'set_westwood': "adb shell \"su -c 'echo westwood | tee /proc/sys/net/ipv4/tcp_congestion_control'\""
    }

    cmd = command_map.get(query.data)
    result = run_adb_command(cmd) if cmd else "Perintah tidak dikenali."
    await query.edit_message_text(text=f"results: <code>{result}</code>", parse_mode="HTML")