import os
import uuid
import requests
import asyncio
import subprocess

from telegram import Update
from telegram.ext import ContextTypes
from handlers._admin import delete_message_after_delay, is_admin
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def handle_notif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.mention_html()

    if not is_admin(user_id):
        sent_message = await update.message.reply_html(f"{username} not the admin, bro.")
        asyncio.create_task(delete_message_after_delay(update.message, 60))
        asyncio.create_task(delete_message_after_delay(sent_message, 60))
        return

    keyboard = [
        [
            InlineKeyboardButton("START", callback_data="notif_start"),
            InlineKeyboardButton("STOP", callback_data="notif_stop"),
            InlineKeyboardButton("STATUS", callback_data="notif_status"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    sent_message = await update.message.reply_text(
        "Pilih aksi untuk monitoring:",
        reply_markup=reply_markup
    )
    asyncio.create_task(delete_message_after_delay(update.message, 60))
    asyncio.create_task(delete_message_after_delay(sent_message, 60))

async def notif_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    username = query.from_user.mention_html()

    if not is_admin(user_id):
        await query.edit_message_text(f"{username} bukan admin.", parse_mode="HTML")
        return

    action = query.data.split("_")[1]
    command_map = {
        "start": "/root/monitor/bot r",
        "stop": "/root/monitor/bot k",
        "status": "/root/monitor/bot s"
    }

    command = command_map.get(action)
    if not command:
        await query.edit_message_text("Aksi tidak dikenali.")
        return

    await query.edit_message_text("loading...")

    try:
        result = subprocess.getoutput(command)
        await query.edit_message_text(f"<pre>{result}</pre>", parse_mode="HTML")
    except Exception as e:
        await query.edit_message_text(f"Error: {e}")