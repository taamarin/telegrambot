import yaml
from telegram import Update
from telegram.ext import ContextTypes

MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB

from handlers.user_store import increment_interaction
increment_interaction()

async def handle_checkyaml(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message or not update.message.reply_to_message.document:
        await update.message.reply_text("Balas ke file YAML yang ingin diperiksa.")
        return

    document = update.message.reply_to_message.document

    # Periksa ekstensi
    if not document.file_name.endswith((".yaml", ".yml")):
        await update.message.reply_text("File bukan YAML. Harap unggah file dengan ekstensi .yaml atau .yml.")
        return

    # Periksa ukuran file
    if document.file_size > MAX_FILE_SIZE:
        await update.message.reply_text("Ukuran file terlalu besar. Maksimum 2MB.")
        return

    # Unduh dan decode isi file
    try:
        file = await document.get_file()
        file_content = await file.download_as_bytearray()
        text_content = file_content.decode("utf-8")
    except Exception as e:
        await update.message.reply_text(f"Gagal mengunduh file: {e}")
        return

    try:
        yaml.safe_load(text_content)
        await update.message.reply_text("YAML valid, tidak ditemukan kesalahan.")
    except yaml.YAMLError as e:
        if hasattr(e, 'problem_mark'):
            mark = e.problem_mark
            line_number = mark.line + 1
            column = mark.column + 1
            lines = text_content.splitlines()
            error_line = lines[mark.line] if mark.line < len(lines) else "Baris tidak ditemukan"
            snippet = f"{line_number}: {error_line}"
            location = f"Baris {line_number}, Kolom {column}"
        else:
            location = "Lokasi tidak diketahui"
            snippet = "(tidak ada baris yang bisa ditampilkan)"

        await update.message.reply_text(
            f"YAML tidak valid.\nLokasi kesalahan: {location}\n"
            f"Cuplikan:\n`{snippet}`\n\nDetail:\n```{e}```",
            parse_mode="Markdown"
        )