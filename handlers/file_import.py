import os
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from handlers._admin import delete_message_after_delay, is_admin

async def handle_import(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    username = update.effective_user.mention_html()

    if not is_admin(user_id):
        sent_message = await update.message.reply_html(f"{username} not the admin, bro.")
        asyncio.create_task(delete_message_after_delay(update.message, 30))
        asyncio.create_task(delete_message_after_delay(sent_message, 30))
        return

    # Tentukan path default
    default_path = "/root/telegram"

    if update.message.reply_to_message and update.message.reply_to_message.document:
        # Jika pesan adalah reply terhadap file
        file = await update.message.reply_to_message.document.get_file()
        file_name = update.message.reply_to_message.document.file_name
        
        # Tentukan path untuk menyimpan file
        if len(context.args) == 1:
            user_path = context.args[0]
            if not user_path.startswith("/"):
                user_path = f"/root/telegram/{user_path}"  # Menambahkan /root/telegram jika path tidak dimulai dengan /
            # Gabungkan path dengan nama file
            file_path = os.path.join(user_path, file_name)
        else:
            # Jika path tidak diberikan, gunakan default path
            file_path = os.path.join(default_path, file_name)

        # Pastikan path yang diberikan aman
        if not file_path.startswith(default_path):
            error_message = await update.message.reply_text("Error: invalid path.")
            asyncio.create_task(delete_message_after_delay(update.message, 30))
            asyncio.create_task(delete_message_after_delay(error_message, 30))
            return

        # Kirim pesan "Proses sedang berlangsung..."
        sent_message = await update.message.reply_text("proses sedang berlangsung...")

        try:
            # Mengunduh file ke path yang ditentukan
            await file.download_to_drive(file_path)
            await sent_message.edit_text(f"{file_path} telah diimpor.")
        except Exception as e:
            error_message = await update.message.reply_text(f"Error: {e}")
            asyncio.create_task(delete_message_after_delay(update.message, 30))
            asyncio.create_task(delete_message_after_delay(error_message, 30))
    else:
        sent_message = await update.message.reply_text("reply file yang akan diimpor.")

    # Hapus pesan setelah beberapa detik
    asyncio.create_task(delete_message_after_delay(update.message, 30))
    asyncio.create_task(delete_message_after_delay(sent_message, 30))