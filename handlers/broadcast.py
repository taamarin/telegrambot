from telegram import Update, Message
from telegram.ext import ContextTypes
from handlers.user_store import get_all_users

ADMIN_ID = 5488520229

async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("not the admin, bro")
        return

    users = get_all_users()
    if not users:
        await update.message.reply_text("tidak ada pengguna yang terdaftar.")
        return

    msg: Message = update.message
    success, fail = 0, 0

    # Balas media/file
    if msg.reply_to_message:
        for user_id in users:
            try:
                await msg.reply_to_message.copy(chat_id=user_id)
                success += 1
            except Exception as e:
                print(f"gagal kirim ke {user_id}: {e}")
                fail += 1

    # Kirim teks langsung
    elif context.args:
        text = ' '.join(context.args)
        for user_id in users:
            try:
                await context.bot.send_message(chat_id=user_id, text=text)
                success += 1
            except Exception as e:
                print(f"gagal kirim ke {user_id}: {e}")
                fail += 1
    else:
        await msg.reply_text("/broadcast `<pesan>` atau reply", parse_mode="Markdown")
        return

    await msg.reply_text(f"BROADCAST selesai.\nBerhasil: {success}\nGagal: {fail}")