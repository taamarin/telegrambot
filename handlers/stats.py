import datetime
import time
import asyncio
import platform
import shutil
import sys
import threading

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes
from handlers.user_store import get_all_users, get_interaction_count, get_all_chats, add_chat, get_group_chats

from handlers._admin import delete_message_after_delay, is_admin, get_admin_ids
from telegram.helpers import escape_markdown

START_TIME = datetime.datetime.now()

def get_memory_usage():
    try:
        with open("/proc/meminfo") as f:
            meminfo = {line.split(":")[0]: int(line.split()[1]) for line in f if ":" in line}
        total = meminfo.get("MemTotal", 0)
        available = meminfo.get("MemAvailable", 0)
        used = total - available
        return f"{used // 1024} MB / {total // 1024} MB ({used * 100 // total}%)"
    except:
        return "Unavailable"

def get_cpu_usage():
    try:
        with open("/proc/stat") as f:
            cpu_line = f.readline().split()
        total_time_1 = sum(map(int, cpu_line[1:]))
        idle_time_1 = int(cpu_line[4])
        time.sleep(0.1)
        with open("/proc/stat") as f:
            cpu_line = f.readline().split()
        total_time_2 = sum(map(int, cpu_line[1:]))
        idle_time_2 = int(cpu_line[4])
        total_delta = total_time_2 - total_time_1
        idle_delta = idle_time_2 - idle_time_1
        usage_percent = (100 * (total_delta - idle_delta) // total_delta) if total_delta else 0
        return f"{usage_percent}%"
    except:
        return "Unavailable"

def get_disk_usage():
    try:
        total, used, free = shutil.disk_usage("/")
        used_mb = used // (1024 ** 2)
        total_mb = total // (1024 ** 2)
        percent = used * 100 // total
        return f"{used_mb} MB / {total_mb} MB ({percent}%)"
    except:
        return "Unavailable"

def get_start_time():
    return START_TIME.strftime("%Y-%m-%d %H:%M:%S")

def get_python_info():
    return f"{platform.python_implementation()} {platform.python_version()}"

def get_platform_info():
    return f"{platform.system()} {platform.release()} ({platform.machine()})"

def get_thread_count():
    return threading.active_count()

def get_event_loop_status():
    loop = asyncio.get_event_loop()
    return "Running" if loop.is_running() else "Not running"

async def get_api_latency(bot):
    start = time.time()
    await bot.get_me()
    return int((time.time() - start) * 1000)

async def handle_botinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.mention_html()

    if not is_admin(user_id):
        sent_message = await update.message.reply_html(f"{username} not the admin, bro.")
        asyncio.create_task(delete_message_after_delay(update.message, 60))
        asyncio.create_task(delete_message_after_delay(sent_message, 60))
        return

    try:
        loading_message = await update.message.reply_text("Loading...")

        start = time.time()

        now = datetime.datetime.now()
        uptime = now - START_TIME
        uptime_str = str(uptime).split('.')[0]

        total_users = len(get_all_users())
        total_chats = len(get_all_chats())  # Anda harus menerapkan ini
        total_group_chats = len(get_group_chats())

        total_interactions = get_interaction_count()
        total_admins = len(get_admin_ids())  # You must implement this

        api_latency = await get_api_latency(context.bot)

        cpu_usage = get_cpu_usage()
        memory_usage = get_memory_usage()
        disk_usage = get_disk_usage()
        start_time = get_start_time()
        python_version = get_python_info()
        platform_info = get_platform_info()
        thread_count = get_thread_count()
        loop_status = get_event_loop_status()

        stats_message = (
            f"* System Diagnostics Report*\n"
            f"❀ *Users:* `{total_users}`\n"
            f"❀ *Active Chats:* `{total_chats}`\n"
            f"❀ *Group Chats:* `{total_group_chats}`\n"
            f"❀ *Admin Count:* `{total_admins}`\n"
            f"❀ *Interaction Count:* `{total_interactions}`\n"
            f"❀ *Uptime:* `{uptime_str}`\n"
            f"❀ *Started:* `{start_time}`\n"
            f"❀ *Telegram API Latency:* `{api_latency} ms`\n"
            f"❀ *CPU Load:* `{cpu_usage}`\n"
            f"❀ *RAM Usage:* `{memory_usage}`\n"
            f"❀ *Disk Usage:* `{disk_usage}`\n"
            f"❀ *Python Version:* `{python_version}`\n"
            f"❀ *Platform:* `{platform_info}`\n"
            f"❀ *Active Threads:* `{thread_count}`\n"
            f"❀ *Event Loop Status:* `{loop_status}`"
        )

        await loading_message.edit_text(stats_message, parse_mode="Markdown")
        asyncio.create_task(delete_message_after_delay(update.message, 60))
        asyncio.create_task(delete_message_after_delay(loading_message, 60))

    except Exception as e:
        await loading_message.edit_text(f"Error: {e}")
        asyncio.create_task(delete_message_after_delay(update.message, 60))
        asyncio.create_task(delete_message_after_delay(loading_message, 60))