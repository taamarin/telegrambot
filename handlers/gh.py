import os
from telegram import Update, Message
from telegram.ext import Application, CommandHandler, ContextTypes
from github import Github
from github.ContentFile import ContentFile
from github.GithubException import GithubException

# TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
GITHUB_TOKEN = "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"
GITHUB_REPO = "taamarin/any-icon"
GITHUB_BRANCH = "main"  # Branch target
TARGET_PATH = ""  # Kosong artinya upload ke root repo

# Inisialisasi GitHub
g = Github(GITHUB_TOKEN)
repo = g.get_repo(GITHUB_REPO)

async def upload_to_github(file_path: str, github_path: str, commit_message: str):
    with open(file_path, "rb") as f:
        content = f.read()

    raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{github_path}"

    try:
        existing_file: ContentFile = repo.get_contents(github_path, ref=GITHUB_BRANCH)
        repo.update_file(
            path=github_path,
            message=commit_message,
            content=content,
            sha=existing_file.sha,
            branch=GITHUB_BRANCH
        )
        return (
            f"✅ File `{github_path}` berhasil *diupdate* di GitHub cabang `{GITHUB_BRANCH}`.\n"
            f"🔗 [Raw Link]({raw_url})"
        )
    except GithubException as e:
        if e.status == 404:
            repo.create_file(
                path=github_path,
                message=commit_message,
                content=content,
                branch=GITHUB_BRANCH
            )
            return (
                f"✅ File `{github_path}` berhasil *diupload* ke GitHub cabang `{GITHUB_BRANCH}`.\n"
                f"🔗 [Raw Link]({raw_url})"
            )
        else:
            raise

async def gh_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Gunakan perintah /gh dengan mereply file.")
        return

    commit_msg = " ".join(context.args).strip() or "[cli] upload"

    reply: Message = update.message.reply_to_message
    document = reply.document or reply.audio or reply.video or reply.voice or reply.photo

    if not document:
        await update.message.reply_text("❌ Balasan harus berupa file atau media.")
        return

    msg = await update.message.reply_text("⬇️ Mengunduh file...")

    file = await reply.effective_attachment.get_file()
    file_name = (
        reply.document.file_name
        if reply.document else f"{reply.effective_attachment.file_unique_id}.bin"
    )

    local_path = f"/tmp/{file_name}"
    github_path = f"{file_name}" if not TARGET_PATH else f"{TARGET_PATH.rstrip('/')}/{file_name}"

    await file.download_to_drive(local_path)

    try:
        result_msg = await upload_to_github(local_path, github_path, commit_msg)
        await msg.edit_text(result_msg, parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ Gagal upload: {e}")
    finally:
        os.remove(local_path)