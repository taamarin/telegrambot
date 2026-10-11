import sqlite3
from functools import wraps
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

DB_PATH = "/root/telegram/access.db"
GROUP_ID = -1001597117128
CHANNEL_ID = -1001502437119

GROUP_URL = "https://t.me/taamarin"
CHANNEL_URL = "https://t.me/nothing_taamarin"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                is_authorized INTEGER DEFAULT 0
            )
        ''')

def save_user_to_db(user):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name, is_authorized) VALUES (?, ?, ?, 1)",
            (user.id, user.username, user.first_name)
        )

async def check_membership(context, user_id):
    async def is_member(chat_id):
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            return member.status in ['member', 'administrator', 'creator']
        except:
            return False

    from asyncio import gather
    group_joined, channel_joined = await gather(
        is_member(GROUP_ID),
        is_member(CHANNEL_ID)
    )
    return group_joined, channel_joined

def restricted(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return

        group_joined, channel_joined = await check_membership(context, user.id)

        if group_joined and channel_joined:
            save_user_to_db(user)
            return await func(update, context, *args, **kwargs)

        # Respons cepat jika tidak memenuhi syarat
        name = f"@{user.username}" if user.username else (user.first_name or "Pengguna")
        text = (
            f"{name}, *akses ditolak*\n"
            "     ↳  silakan *bergabung* ke *grup* dan *channel* untuk akses bot ini:"
        )

        buttons = [
            [
                InlineKeyboardButton(f"Channel{' ✅' if channel_joined else ''}", url=CHANNEL_URL),
                InlineKeyboardButton(f"Group{' ✅' if group_joined else ''}", url=GROUP_URL)
            ]
        ]

        reply_markup = InlineKeyboardMarkup(buttons)

        if update.message:
            await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.message.edit_text(text, parse_mode="Markdown", reply_markup=reply_markup)

    return wrapper