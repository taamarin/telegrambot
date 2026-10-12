import asyncio
import sqlite3
import re
from datetime import datetime, timedelta
from telegram import Message, ChatPermissions, Update
from telegram.ext import ContextTypes, MessageHandler, filters
from telegram.helpers import mention_html

# == Konfigurasi limit & mute ==
CHAT_ID = -1001597117128
VIDEO_TOPIC_ID = 487276
LIMIT_TOPIC_ID = 282228
FILE_TOPIC_ID = 12345
COMMAND_TOPIC_ID = 283465  # ID topik untuk mute 10 menit

MUTE_COMMANDS = [
    "/cuaca", "/dpost", "/xray", "/clash", "/cbfr", "/sbfr", "/flclash",
    "/cmfa", "/sing", "/sfa", "/yaml", "/hostip", "/worker", "/prayer",
    "/upload", "/revclash", "/notes", "/trial", "/check", "/start"
]

DB_PATH = "/root/telegram/limits.db"
DAILY_LIMIT = 2


# ==============================
# Database
# ==============================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS user_messages (
        user_id INTEGER,
        date TEXT,
        count INTEGER,
        PRIMARY KEY (user_id, date)
    )''')
    conn.commit()
    conn.close()


async def increment_message_count(user_id: int) -> int:
    today = datetime.utcnow().date()
    today_str = today.isoformat()
    delete_before = (today - timedelta(days=7)).isoformat()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM user_messages WHERE date < ?", (delete_before,))
    c.execute("SELECT count FROM user_messages WHERE user_id = ? AND date = ?", (user_id, today_str))
    row = c.fetchone()

    if row:
        new_count = row[0] + 1
        c.execute("UPDATE user_messages SET count = ? WHERE user_id = ? AND date = ?", (new_count, user_id, today_str))
    else:
        new_count = 1
        c.execute("INSERT INTO user_messages (user_id, date, count) VALUES (?, ?, ?)", (user_id, today_str, 1))

    conn.commit()
    conn.close()
    return new_count


# ==============================
# Mute & Auto delete
# ==============================
async def mute_user(context: ContextTypes.DEFAULT_TYPE, user_id: int, minutes: int = 0, days: int = 0):
    try:
        until_date = datetime.utcnow() + timedelta(minutes=minutes, days=days)
        await context.bot.restrict_chat_member(
            chat_id=CHAT_ID,
            user_id=user_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date
        )
    except Exception as e:
        print(f"Gagal mute user {user_id}: {e}")


async def auto_delete_notification(message: Message, delay: int = 30):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception as e:
        print(f"Gagal hapus notifikasi: {e}")


# ==============================
# Filter pesan
# ==============================
async def filter_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return

    message: Message = update.message
    user = update.effective_user
    thread_id = message.message_thread_id

    # Topik video → hanya video
    if thread_id == VIDEO_TOPIC_ID:
        if not message.video:
            try:
                await message.delete()
                name = mention_html(user.id, user.first_name or "Pengguna")
                notif = await context.bot.send_message(
                    chat_id=CHAT_ID,
                    text=f"❗{name}, hanya kirim video di topik ini.",
                    message_thread_id=VIDEO_TOPIC_ID,
                    parse_mode='HTML'
                )
                asyncio.create_task(auto_delete_notification(notif, delay=5))
            except Exception as e:
                print(f"Gagal notifikasi video: {e}")
        return

    # Topik file → hanya file
    if thread_id == FILE_TOPIC_ID:
        if not message.document:
            try:
                await message.delete()
                name = mention_html(user.id, user.first_name or "Pengguna")
                notif = await context.bot.send_message(
                    chat_id=CHAT_ID,
                    text=f"📁 {name}, hanya kirim file di topik ini.",
                    message_thread_id=FILE_TOPIC_ID,
                    parse_mode='HTML'
                )
                asyncio.create_task(auto_delete_notification(notif, delay=5))
            except Exception as e:
                print(f"Gagal notifikasi file: {e}")
        return

    # Topik limit → max 2 pesan/hari
    if thread_id == LIMIT_TOPIC_ID:
        try:
            count = await increment_message_count(user.id)
            name = mention_html(user.id, user.first_name or "Pengguna")

            if count > DAILY_LIMIT:
                await message.delete()
                await mute_user(context, user.id, days=1)
                notif = await context.bot.send_message(
                    chat_id=CHAT_ID,
                    text=f"🚫 {name}, melebihi batas 2 pesan/hari. Dibisukan 24 jam.",
                    message_thread_id=LIMIT_TOPIC_ID,
                    parse_mode='HTML'
                )
                asyncio.create_task(auto_delete_notification(notif))
            elif count == DAILY_LIMIT:
                notif = await context.bot.send_message(
                    chat_id=CHAT_ID,
                    text=f"⚠️ {name}, sudah 2/2 pesan hari ini. Pesan berikutnya → mute.",
                    message_thread_id=LIMIT_TOPIC_ID,
                    parse_mode='HTML'
                )
                asyncio.create_task(auto_delete_notification(notif))
            elif count == DAILY_LIMIT - 1:
                notif = await context.bot.send_message(
                    chat_id=CHAT_ID,
                    text=f"ℹ️ {name}, sudah 1/2 pesan hari ini di topik ini.",
                    message_thread_id=LIMIT_TOPIC_ID,
                    parse_mode='HTML'
                )
                asyncio.create_task(auto_delete_notification(notif))
        except Exception as e:
            print(f"Gagal proses limit harian: {e}")

    # Topik command → mute 10 menit
    if thread_id == COMMAND_TOPIC_ID:
        match = re.match(r"(/[\w]+)(@[\w]+)?", message.text or "")
        if match:
            command = match.group(1).lower()
            if command in MUTE_COMMANDS:
                try:
                    member = await context.bot.get_chat_member(CHAT_ID, user.id)
                    if member.status in ("administrator", "creator"):
                        return

                    await message.delete()
                    await mute_user(context, user.id, minutes=10)

                    name = mention_html(user.id, user.first_name or "Pengguna")
                    notif = await context.bot.send_message(
                        chat_id=CHAT_ID,
                        text=f"🚫 {name}, dibisukan 10 menit karena menjalankan {command} di topik ini.",
                        message_thread_id=COMMAND_TOPIC_ID,
                        parse_mode='HTML'
                    )
                    asyncio.create_task(auto_delete_notification(notif, delay=30))
                except Exception as e:
                    print(f"Gagal mute 10 menit: {e}")
                return


# ==============================
# Fungsi helper untuk daftar ke Application
# ==============================
def register_limit_handlers(application):
    application.add_handler(MessageHandler(filters.ALL, filter_messages), group=10)