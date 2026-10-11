import asyncio

# Daftar ID admin (ganti dengan ID Telegram admin Anda)
ADMINS = [5488520229]

# Fungsi untuk menghapus pesan setelah delay
async def delete_message_after_delay(message, delay: int):
    await asyncio.sleep(delay)
    await message.delete()

# Fungsi untuk memeriksa apakah pengguna adalah admin
def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

# Fungsi untuk mendapatkan daftar ID admin
def get_admin_ids():
    return ADMINS