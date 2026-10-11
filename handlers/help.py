from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from handlers.user_store import increment_interaction
increment_interaction()

# Fungsi utama untuk /help
async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [
            InlineKeyboardButton("User Commands", callback_data='help_user'),
            InlineKeyboardButton("Admin Commands", callback_data='help_admin'),
        ],
        [
            InlineKeyboardButton("Donat", callback_data='donate'),
            InlineKeyboardButton("Hub Admin", callback_data='contact_admin')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    user = update.effective_user
    name = f"@{user.username}" if user.username else user.first_name

    await update.message.reply_text(
        f"{name}, Silakan pilih kategori bantuan yang ingin Anda lihat:",
        reply_markup=reply_markup
    )

# Fungsi callback saat tombol ditekan
async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

# ❀ /worker — Mendapatkan akun VPN (Cloudflare Worker).
# ❀ /prayer — Menampilkan jadwal salat berdasarkan lokasi.
# ❀ /cuaca — Menampilkan informasi cuaca terkini.

    if query.data == 'help_user':
        text = """
<b>User Commands</b>
❀ /start — Memulai bot dan menampilkan pesan sambutan.
❀ /dpost — Mengunduh postingan dari Instagram.
❀ /xray — Konversi konfigurasi outbound Xray.
❀ /clash — Konversi konfigurasi outbound Clash.
❀ /cbfr — Konversi ke konfigurasi BFR (Clash).
❀ /sbfr — Konversi ke konfigurasi BFR (Sing-box).
❀ /flclash — Konversi ke konfigurasi FlClash.
❀ /cmfa — Konversi ke konfigurasi CMFA.
❀ /sing — Konversi konfigurasi outbound Sing-box.
❀ /sfa — Konversi ke konfigurasi Sing-box (Android).
❀ /yaml — Pemeriksa dan validasi file YAML.
❀ /hostip — Menampilkan IP dari sebuah domain.
❀ /upload — Mengunggah file ikon untuk Zashboard.
❀ /revclash — Mengubah konfigurasi Clash (YAML) menjadi URL V2Ray (vmess, vless, trojan, dll).
"""
    elif query.data == 'help_admin':
        text = """
<b>Admin Commands</b>
❀ /info — Menampilkan informasi tentang bot.
❀ /sh — Menjalankan perintah bash di server.
❀ /xclash — Menampilkan status dan opsi restart untuk Clash.
❀ /tcp — Menampilkan opsi pengaturan algoritma TCP"
❀ /restart — Memulai ulang bot.
❀ /down — Mengunduh file dari URL.
❀ /yacd — Kontrol Dashboard Clash.
"""
    elif query.data == 'donate':
        text = 'support ke: <a href="https://saweria.co/taamarin">Saweria</a>\nTerimakasih.'
    elif query.data == 'contact_admin':
        text = "@taamarin"
    else:
        text = "Unknown command."
    
    await query.edit_message_text(text=text, parse_mode='HTML', disable_web_page_preview=False)