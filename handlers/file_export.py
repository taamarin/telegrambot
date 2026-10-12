import os
import asyncio
from telegram import Update, InputFile
from telegram.ext import ContextTypes
from handlers._admin import delete_message_after_delay, is_admin

async def handle_export(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    username = update.effective_user.mention_html()

    # Memeriksa apakah pengguna adalah admin
    if not is_admin(user_id):
        sent_message = await update.message.reply_html(f"{username} not the admin, bro.")
        asyncio.create_task(delete_message_after_delay(update.message, 30))
        asyncio.create_task(delete_message_after_delay(sent_message, 30))
        return

    # Memeriksa apakah ada argumen path
    if len(context.args) != 1:
        sent_message = await update.message.reply_text("/export path")
        asyncio.create_task(delete_message_after_delay(update.message, 30))
        asyncio.create_task(delete_message_after_delay(sent_message, 30))
        return

    file_path = context.args[0]

    # Kirim pesan "Proses sedang berlangsung..."
    sent_message = await update.message.reply_text("loading...")

    # Periksa apakah file ada di path yang diberikan
    if os.path.exists(file_path) and os.path.isfile(file_path):
        try:
            # Kirim file ke pengguna
            with open(file_path, 'rb') as file:
                file_name = os.path.basename(file_path)  # Ambil nama file dari path
                await update.message.reply_document(
                    document=InputFile(file, filename=file_name),
                    caption=f"{file_name} berhasil diexport."
                )
        except Exception as e:
            error_message = await update.message.reply_text(f"Error: {e}")
            asyncio.create_task(delete_message_after_delay(update.message, 30))
            asyncio.create_task(delete_message_after_delay(error_message, 30))
    else:
        # Jika file tidak ditemukan
        error_message = await update.message.reply_text(f"Error: file tidak ditemukan: {file_path}")
        asyncio.create_task(delete_message_after_delay(update.message, 30))
        asyncio.create_task(delete_message_after_delay(error_message, 30))

    # Hapus pesan proses dan perintah setelah delay
    asyncio.create_task(delete_message_after_delay(sent_message, 30))