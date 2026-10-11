import os
import uuid
import requests
import asyncio
import subprocess
import html

from telegram import Update
from telegram.ext import ContextTypes
from handlers._admin import delete_message_after_delay, is_admin

async def handle_bash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fungsi untuk menjalankan perintah bash."""
    user_id = update.effective_user.id
    username = update.effective_user.mention_html()

    if not is_admin(user_id):
        sent_message = await update.message.reply_html(f"{username} not the admin, bro.")
        asyncio.create_task(delete_message_after_delay(update.message, 60))
        asyncio.create_task(delete_message_after_delay(sent_message, 60))
        return

    if len(context.args) == 0:
        sent_message = await update.message.reply_html(
            "/bash <code>ls -l</code>"
        )
        # asyncio.create_task(delete_message_after_delay(update.message, 60))
        # asyncio.create_task(delete_message_after_delay(sent_message, 60))
        return

    command = ' '.join(context.args)
    try:
        # Kirim pesan awal
        sent_message = await update.message.reply_text("loading...")

        # Jalankan perintah bash
        result = subprocess.getoutput(command)

        # Edit pesan dengan hasil output
        # await sent_message.edit_text(f"<code>{result}</code>", parse_mode="HTML")

        escaped_result = html.escape(result)
        await sent_message.edit_text(
            f'<blockquote class="expandable"><code>{escaped_result}</code></blockquote>',
            parse_mode="HTML"
        )

        asyncio.create_task(delete_message_after_delay(update.message, 60))
        asyncio.create_task(delete_message_after_delay(sent_message, 60))
    except Exception as e:
        await sent_message.edit_text(f"Error: {e}")
        asyncio.create_task(delete_message_after_delay(update.message, 60))
        asyncio.create_task(delete_message_after_delay(sent_message, 60))