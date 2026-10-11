# handlers/handle_info.py
import asyncio
import subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from handlers._admin import delete_message_after_delay, is_admin

# Menu awal dengan tombol
async def info_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [
            InlineKeyboardButton("STB", callback_data="info_stb"),
            InlineKeyboardButton("DEVICE", callback_data="info_4x"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    sent_message = await update.message.reply_text("Pilih jenis informasi:", reply_markup=reply_markup)

    # Hapus perintah /info dan tombol setelah 60 detik
    asyncio.create_task(delete_message_after_delay(update.message, 30))  # pesan /info
    asyncio.create_task(delete_message_after_delay(sent_message, 30))    # tombol inline

# Callback handler tombol
async def info_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query: CallbackQuery = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    username = update.effective_user.mention_html()
    message = query.message

    if not is_admin(user_id):
        await query.edit_message_text(f"{username} not the admin, bro.", parse_mode="HTML")
        return

    await query.edit_message_text("Loading information...")

    try:
        if query.data == "info_stb":
            command = """
TW=$(source /root/bot/info)

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STB Information
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
$TW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            """
        elif query.data == "info_4x":
            command = """
KERNEL=$(adb shell uname -r)
MODEL=$(adb shell getprop ro.product.model)
AC=$(adb shell dumpsys battery | grep 'AC powered:' | awk '{print $3}')
USB=$(adb shell dumpsys battery | grep 'USB powered:' | awk '{print $3}')
BATTERY_LEVEL=$(adb shell dumpsys battery | grep 'level' | awk '{print $2}')
[ "$BATTERY_LEVEL" -le 50 ] && LEVEL='🪫' || LEVEL='🔋'
BATTERY_TEMP=$(adb shell dumpsys battery | grep 'temperature' | awk '{print $2}')
BATTERY_TEMP_C=$(awk 'BEGIN {printf "%.1f", '"$BATTERY_TEMP"'/10}')
[ "$(echo "$BATTERY_TEMP_C <= 35.0" | bc)" -eq 1 ] && TEMP='🥶' || TEMP='🥵'
BOOT=$(adb shell uptime | awk -F' up ' '{print $2}' | cut -d ',' -f1)

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Device Information
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✿ Model          : ${MODEL}
✿ Kernel         : ${KERNEL}
✿ AC powered     : ${AC}
✿ USB            : ${USB}
✿ Battery Level  : ${BATTERY_LEVEL}% / 100% 
✿ Temperature    : ${BATTERY_TEMP_C}°C
✿ Uptime         : ${BOOT}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            """
        else:
            await query.edit_message_text("Perintah tidak dikenal.")
            return

        result = subprocess.getoutput(command)
        await query.edit_message_text(f"<pre>{result}</pre>", parse_mode="HTML")

    except Exception as e:
        await query.edit_message_text(f"Error: {e}")