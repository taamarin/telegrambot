from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, CallbackQueryHandler
import subprocess
import asyncio
from handlers._admin import delete_message_after_delay, is_admin

from handlers.user_store import increment_interaction
increment_interaction()

# Handler utama /box
async def handle_box(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.mention_html()

    if not is_admin(user_id):
        sent_message = await update.message.reply_html(f"{username} not the admin, bro.")
        asyncio.create_task(delete_message_after_delay(update.message, 60))
        asyncio.create_task(delete_message_after_delay(sent_message, 60))
        return

    keyboard = [
        [InlineKeyboardButton("STATUS", callback_data="box_status"),
        InlineKeyboardButton("RESTART", callback_data="box_restart")],
        [InlineKeyboardButton("CHECK", callback_data="box_ceks"),
        InlineKeyboardButton("UPGRADE", callback_data="box_upk")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    box_message = await update.message.reply_text("Pilih aksi untuk box:", reply_markup=reply_markup)
    asyncio.create_task(delete_message_after_delay(update.message, 60))
    asyncio.create_task(delete_message_after_delay(box_message, 60))

async def handle_box_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    await query.answer()

    if not is_admin(user_id):
        await query.edit_message_text("Kamu bukan admin.")
        return

    action_map = {
        "box_status": "/root/clash/box status",
        "box_restart": "/root/clash/box restart",
        "box_ceks": "/root/clash/box check",
        "box_upk": "/root/clash/box upgrade"
    }

    command = action_map.get(query.data)
    if not command:
        await query.edit_message_text("Perintah tidak valid.")
        return

    try:
        await query.edit_message_text("loding...")
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Error: {result.stderr.strip()}")

        # await query.edit_message_text(f"<pre>{result.stdout.strip()}</pre>", parse_mode="HTML")
        await query.edit_message_text(
            f'<blockquote class="expandable">{result.stdout.strip()}</blockquote>',
            parse_mode="HTML"
        )
    except Exception as e:
        await query.edit_message_text(f"Error: {e}")