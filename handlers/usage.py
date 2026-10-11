import subprocess
import re
from telegram import Update
from telegram.ext import ContextTypes
from handlers._admin import delete_message_after_delay, is_admin
import asyncio

# Function to run the bash script and return output
async def get_usage_report():
    try:
        # Execute the bash script to get the usage report
        result = await asyncio.to_thread(
            subprocess.run, ["bash", "/root/bot/usage"], capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"

def format_message(message):
    """Format message with markdown-like syntax."""
    message = re.sub(r"```(.*?)```", r"<pre><code>\1</code></pre>", message, flags=re.DOTALL)
    message = re.sub(r"`([^`]+)`", r"<code>\1</code>", message)
    message = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", message)
    message = re.sub(r"__(.*?)__", r"<i>\1</i>", message)
    message = re.sub(r"~~(.*?)~~", r"<s>\1</s>", message)
    return message

async def usage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    username = update.effective_user.mention_html()

    # Periksa apakah pengguna admin
    if not is_admin(user_id):
        sent_message = await update.message.reply_html(f"{username} not the admin, bro.")
        asyncio.create_task(delete_message_after_delay(update.message, 60))
        asyncio.create_task(delete_message_after_delay(sent_message, 60))
        return

    # Kirim pesan sementara "Memuat informasi..."
    sent_message = await update.message.reply_text("loading...")

    # Get usage report from the bash script
    usage_report = await get_usage_report()

    if usage_report is None:
        await sent_message.edit_text("gagal memuat informasi.")
        return

    # Format the message
    formatted_report = format_message(usage_report)
    # Edit the sent message with the usage report
    await sent_message.edit_text(formatted_report, parse_mode="HTML")

    # Hapus pesan perintah pengguna dan balasan bot
    asyncio.create_task(delete_message_after_delay(update.message, 60))
    asyncio.create_task(delete_message_after_delay(sent_message, 60))