import instaloader
import os
import re
from urllib.parse import urlparse
from telegram import Update
from telegram.ext import ContextTypes

from handlers.user_store import increment_interaction
increment_interaction()

def get_new_folder(base_path="/root/downloads/Instagram"):
    """Membuat folder baru berurutan Instagram1, Instagram2, dst."""
    counter = 1
    while True:
        folder_name = f"{base_path}{counter}"
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
            return folder_name
        counter += 1

def extract_username_from_url(url: str) -> str:
    """Ekstrak username dari URL profil Instagram."""
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split("/") if p]
    if len(path_parts) == 1:
        return path_parts[0]
    return None

def parse_story_url(url: str):
    """
    Mengembalikan (username, story_id) dari URL story Instagram.
    Contoh: https://www.instagram.com/stories/twinness_/3690816891993791404
    """
    m = re.search(r"instagram\.com/stories/([^/]+)/(\d+)", url)
    if m:
        return m.group(1), int(m.group(2))
    return None, None

async def handle_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Format salah!! /dpost <url atau username>")
        return

    arg = context.args[0].strip()
    loader = instaloader.Instaloader(download_comments=False, save_metadata=False)
    target_folder = get_new_folder()
    loader.dirname_pattern = target_folder

    try:
        files_sent = False
        is_url = arg.startswith("http://") or arg.startswith("https://")

        # === 1️⃣ Jika URL Post/Reel ===
        if "instagram.com/p/" in arg or "instagram.com/reel/" in arg:
            shortcode = arg.split("/")[-2]
            post = instaloader.Post.from_shortcode(loader.context, shortcode)
            loader.download_post(post, target=target_folder)

        # === 2️⃣ Jika URL Story Langsung ===
        elif "instagram.com/stories/" in arg:
            username, story_id = parse_story_url(arg)
            if not username:
                await update.message.reply_text("URL story tidak valid.")
                return

            profile = instaloader.Profile.from_username(loader.context, username)
            found = False
            # Cari story aktif user
            for story in loader.get_stories(userids=[profile.userid]):
                for item in story.get_items():
                    if story_id and item.mediaid == story_id:
                        loader.download_storyitem(item, target=target_folder)
                        found = True
            if not found:
                await update.message.reply_text("Story tidak ditemukan atau sudah kadaluarsa.")
                return

        # === 3️⃣ Jika URL Profil atau Username ===
        else:
            username = None
            if is_url:
                username = extract_username_from_url(arg)
            else:
                username = arg

            if not username:
                await update.message.reply_text("Tidak bisa menemukan username dari URL ini.")
                return

            profile = instaloader.Profile.from_username(loader.context, username)

            # Unduh semua story aktif
            for story in loader.get_stories(userids=[profile.userid]):
                for item in story.get_items():
                    loader.download_storyitem(item, target=target_folder)

            # Unduh semua highlight
            for highlight in loader.get_highlights(profile.userid):
                for item in highlight.get_items():
                    loader.download_storyitem(item, target=target_folder)

        # === 4️⃣ Kirim file hasil download ===
        for root, dirs, files in os.walk(target_folder):
            for file in files:
                if file.lower().endswith((".jpg", ".mp4")):
                    file_path = os.path.join(root, file)
                    with open(file_path, "rb") as f:
                        await update.message.reply_document(document=f)
                        files_sent = True

        # Bersihkan folder
        for root, dirs, files in os.walk(target_folder, topdown=False):
            for file in files:
                os.remove(os.path.join(root, file))
            for dir in dirs:
                os.rmdir(os.path.join(root, dir))
        os.rmdir(target_folder)

        if not files_sent:
            await update.message.reply_text("Tidak ada file ditemukan. Cek URL/username publik.")

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")