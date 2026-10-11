# handlers/restart.py
from telegram import Update
from telegram.ext import ContextTypes
from handlers._admin import delete_message_after_delay, is_admin

import asyncio
import subprocess

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    username = update.effective_user.mention_html()

    if not is_admin(user_id):
        sent_message = await update.message.reply_html(f"{username} not the admin, bro.")
        asyncio.create_task(delete_message_after_delay(update.message, 10))
        asyncio.create_task(delete_message_after_delay(sent_message, 10))
        return

    sent_message = await update.message.reply_text("Bot restart...")
    # asyncio.create_task(delete_message_after_delay(update.message, 30))
    # asyncio.create_task(delete_message_after_delay(sent_message, 30))

    # Jalankan perintah restart pada OpenWrt
    subprocess.Popen(["/root/telegram/main.sh", "l"])