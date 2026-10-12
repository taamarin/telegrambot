from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from handlers.user_store import increment_interaction


def _help_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("User Commands", callback_data="help_user"),
            InlineKeyboardButton("Admin Commands", callback_data="help_admin"),
        ],
        [
            InlineKeyboardButton("Donasi", callback_data="donate"),
            InlineKeyboardButton("Hubungi Admin", callback_data="contact_admin"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def _back_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ Kembali", callback_data="help_menu")]]
    )


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    increment_interaction()

    user = update.effective_user
    if user and user.username:
        name = f"@{user.username}"
    elif user and user.first_name:
        name = user.first_name
    else:
        name = "Pengguna"

    await update.effective_message.reply_text(
        f"{name}, Silakan pilih kategori bantuan yang ingin Anda lihat:",
        reply_markup=_help_menu(),
    )


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "help_menu":
        await query.edit_message_text(
            "Silakan pilih kategori bantuan yang ingin Anda lihat:",
            reply_markup=_help_menu(),
        )
        return
    if query.data == "help_user":
        text = """
<b>User Commands</b>
❀ /start — Memulai bot dan menampilkan menu bantuan.
❀ /help — Menampilkan menu bantuan.
❀ /ask — Bertanya kepada AI.
❀ /dpost — Mengunduh postingan dari Instagram.
❀ /xray — Konversi konfigurasi outbound Xray.
❀ /clash — Konversi konfigurasi outbound Clash.
❀ /cbfr — Konversi ke konfigurasi BFR (Clash).
❀ /sbfr — Konversi ke konfigurasi BFR (Sing-box).
❀ /flclash — Konversi ke konfigurasi FlClash.
❀ /cmfa — Konversi ke konfigurasi CMFA.
❀ /sing — Konversi konfigurasi outbound Sing-box.
❀ /sfa — Konversi ke konfigurasi Sing-box (Android).
❀ /yaml — Memeriksa dan memvalidasi file YAML.
❀ /hostip — Menampilkan IP dari sebuah domain.
❀ /upload — Mengunggah file ikon untuk Zashboard.
❀ /revclash — Mengubah konfigurasi Clash (YAML) menjadi URL V2Ray.
"""
    elif query.data == "help_admin":
        text = """
<b>Admin Commands</b>
❀ /stats — Menampilkan statistik bot.
❀ /sh — Menjalankan perintah bash di server.
❀ /xclash — Menampilkan status dan opsi restart untuk Clash.
❀ /tcp — Mengatur algoritma TCP.
❀ /restart — Memulai ulang bot.
❀ /down — Mengunduh file dari URL.
❀ /yacd — Membuka kontrol Dashboard Clash.
❀ /info — Menampilkan informasi tentang bot.
❀ /broadcast — Mengirim pesan siaran.
"""
    elif query.data == "donate":
        text = 'Dukung bot melalui <a href="https://saweria.co/taamarin">Saweria</a>. Terima kasih!'
    elif query.data == "contact_admin":
        text = "Admin: @taamarin"
    else:
        text = "Perintah tidak dikenal."

    await query.edit_message_text(
        text=text,
        parse_mode="HTML",
        disable_web_page_preview=False,
        reply_markup=_back_button(),
    )