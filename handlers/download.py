import aiohttp
import asyncio
import os
import time
from telegram import Update
from telegram.ext import ContextTypes
from handlers._admin import delete_message_after_delay, is_admin

def human_readable_size(size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"

def get_progress_bar(done, total, length=20):
    percent = done / total if total else 0
    full = int(length * percent)
    empty = length - full
    return f"[{'█' * full}{'░' * empty}] {int(percent * 100)}%"

async def download_file(url, filename, context: ContextTypes.DEFAULT_TYPE, chat_id, message_id):
    timeout = aiohttp.ClientTimeout(total=3600)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                total = int(response.headers.get('Content-Length', 0))

                max_size = 500 * 1024 * 1024
                if total > max_size:
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=f"❌ File terlalu besar (>500MB): {human_readable_size(total)}",
                        parse_mode='Markdown'
                    )
                    return None

                chunk_size = 1024 * 256
                downloaded = 0
                start_time = time.time()
                last_update = 0

                with open(filename, 'wb') as f:
                    async for chunk in response.content.iter_chunked(chunk_size):
                        f.write(chunk)
                        downloaded += len(chunk)
                        elapsed = time.time() - start_time
                        speed = downloaded / elapsed if elapsed > 0 else 0
                        eta = (total - downloaded) / speed if speed > 0 else 0

                        if time.time() - last_update >= 1:
                            progress = get_progress_bar(downloaded, total)
                            text = (
                                f"**Mengunduh dari URL...**\n"
                                f"`{progress}`\n"
                                f"📥 {human_readable_size(downloaded)} / {human_readable_size(total)}\n"
                                f"⚡️ {human_readable_size(speed)}/s\n"
                                f"⏳ ETA: {int(eta)}s"
                            )
                            try:
                                await context.bot.edit_message_text(
                                    chat_id=chat_id,
                                    message_id=message_id,
                                    text=text,
                                    parse_mode='Markdown'
                                )
                            except:
                                pass
                            last_update = time.time()
        return filename
    except Exception as e:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"❌ Gagal mengunduh:\n`{str(e)}`",
            parse_mode='Markdown'
        )
        return None

async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.mention_html()

    if not is_admin(user_id):
        sent = await update.message.reply_html(f"{username} bukan admin.")
        asyncio.create_task(delete_message_after_delay(update.message, 30))
        asyncio.create_task(delete_message_after_delay(sent, 30))
        return

    if not context.args:
        await update.message.reply_text("Gunakan: `/download <url>`", parse_mode='Markdown')
        return

    url = context.args[0]

    # Validasi URL sederhana
    if not url.startswith("http"):
        await update.message.reply_text("URL tidak valid. Harus dimulai dengan http atau https.", parse_mode='Markdown')
        return

    filename = url.split('/')[-1] or 'downloaded_file'
    chat_id = update.effective_chat.id
    thread_id = update.message.message_thread_id

    try:
        sent = await update.message.reply_text(
            f"Memulai unduhan dari:\n`{url}`",
            parse_mode='Markdown',
            message_thread_id=thread_id
        )

        filepath = await download_file(url, filename, context, chat_id, sent.message_id)
        if not filepath:
            return

        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=sent.message_id,
            text=f"✅ Selesai diunduh ke server sebagai `{filename}`",
            parse_mode='Markdown'
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")