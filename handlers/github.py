import requests
import os
import base64
from telegram.constants import ParseMode
from telegram import Update
from telegram.ext import ContextTypes

# Konfigurasi GitHub
GITHUB_REPO = "taamarin/any-icon"
GITHUB_TOKEN = "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"
GITHUB_BRANCH = "main"

async def get_unique_filename(folder_path, file_name):
    """Cek apakah file sudah ada di GitHub dan cari nama unik jika perlu."""
    base_name, ext = os.path.splitext(file_name)
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    for i in range(100):  # Cek hingga 100 versi
        candidate = f"{base_name}_{i}{ext}" if i > 0 else file_name
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{folder_path}/{candidate}?ref={GITHUB_BRANCH}"
        resp = requests.get(url, headers=headers)
        if resp.status_code == 404:
            return candidate  # Nama belum dipakai
        elif resp.status_code != 200:
            raise Exception(f"GitHub API error: {resp.status_code} - {resp.text}")
    raise Exception("Terlalu banyak duplikat nama, gagal membuat nama unik.")

async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    reply = msg.reply_to_message

    if not reply or not (reply.document or reply.photo):
        await msg.reply_text("reply to file or photo")
        return

    # Tampilkan pesan loading
    loading_msg = await msg.reply_text("Loading...")

    # Path folder tujuan di GitHub
    folder_path = "uploads"
    if context.args:
        folder_path = context.args[0].strip('/')

    # Ambil file dari balasan
    if reply.document:
        telegram_file = reply.document
        file_name = telegram_file.file_name or "file.bin"
    elif reply.photo:
        telegram_file = reply.photo[-1]
        file_name = f"photo_{telegram_file.file_unique_id}.png"
    else:
        await loading_msg.edit_text("Unsupported file type.")
        return

    # Batas ukuran file 3MB
    max_size = 2 * 1024 * 1024
    file_size = telegram_file.file_size if hasattr(telegram_file, "file_size") else 0
    if file_size > max_size:
        await loading_msg.edit_text("Ukuran file terlalu besar! Maksimal 2MB.")
        return

    # Unduh file
    file = await context.bot.get_file(telegram_file.file_id)
    temp_path = f"/root/downloads/{file_name}"
    await file.download_to_drive(temp_path)

    # Pastikan nama unik
    try:
        unique_name = await get_unique_filename(folder_path, file_name)
    except Exception as e:
        await loading_msg.edit_text(f"Gagal memverifikasi nama file: {str(e)}")
        return

    # Encode base64
    with open(temp_path, "rb") as f:
        encoded_content = base64.b64encode(f.read()).decode()

    # Upload ke GitHub
    github_api = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{folder_path}/{unique_name}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    data = {
        "message": f"[cli] upload {unique_name} from Telegram bot",
        "content": encoded_content,
        "branch": GITHUB_BRANCH
    }

    # try:
        # r = requests.put(github_api, json=data, headers=headers)
        # if r.status_code in [200, 201]:
            # raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{folder_path}/{unique_name}"
            # symlink = f'<a href="{raw_url}">{unique_name}</a>'
            # await loading_msg.edit_text(f"Berhasil diupload ke GitHub!\nLink: {symlink}", parse_mode=ParseMode.HTML)
        # else:
            # error = r.json().get("message", "Unknown error")
            # await loading_msg.edit_text(f"Gagal upload: {error}")
    # except Exception as e:
        # await loading_msg.edit_text(f"Terjadi kesalahan saat upload: {str(e)}")

    try:
        r = requests.put(github_api, json=data, headers=headers)
        if r.status_code in [200, 201]:
            raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{folder_path}/{unique_name}"
            symlink = f'<a href="{raw_url}">{unique_name}</a>'
            await loading_msg.edit_text(f"Berhasil diupload ke GitHub!\nLink: {symlink}", parse_mode=ParseMode.HTML)
        else:
            error = r.json().get("message", "Unknown error")
            await loading_msg.edit_text(f"Gagal upload: {error}")
    except Exception as e:
        await loading_msg.edit_text(f"Terjadi kesalahan saat upload: {str(e)}")
    finally:
        # Hapus file sementara
        try:
            os.remove(temp_path)
        except Exception as e:
            print(f"Gagal menghapus file sementara: {e}")