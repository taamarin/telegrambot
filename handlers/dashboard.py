import requests
import time
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from handlers._admin import delete_message_after_delay, is_admin

# Konstanta
MAX_MESSAGE_AGE = 3
# MIHOMO_API = 'http://192.168.44.1:9090'
MIHOMO_API = 'http://192.168.1.1:9090'
API_SECRET = '123456'
HEADERS = {'Authorization': f'Bearer {API_SECRET}'}


def main_menu_keyboard(proxies):
    selector_buttons = [
        InlineKeyboardButton(f"{name} ➠ {proxies[name].get('now', '')}", callback_data=f"select_{name}")
        for name in proxies if proxies[name]['type'] == 'Selector'
    ]
    keyboard = [selector_buttons[i:i + 2] for i in range(0, len(selector_buttons), 2)]
    keyboard += [
        [InlineKeyboardButton("Status Delay", callback_data="status"),
         InlineKeyboardButton("Reload Config", callback_data="reload"),
         InlineKeyboardButton("Restart", callback_data="restart")],
        [InlineKeyboardButton("Upgrade", callback_data="upgrade"),
         InlineKeyboardButton("Versi", callback_data="version")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def get_node_latency(group, node):
    try:
        delay = requests.get(
            f"{MIHOMO_API}/proxies/{group}/delay?url=http://www.gstatic.com/generate_204&timeout=3000&name={node}",
            headers=HEADERS
        ).json()
        return delay.get('delay', 'timeout')
    except:
        return "error"


async def check_admin_permission(update, context, is_callback=False):
    user_id = update.effective_user.id
    username = update.effective_user.mention_html()

    if is_admin(user_id):
        return True

    if is_callback:
        await update.callback_query.answer("🤡 Bukan admin...,", show_alert=True)
    else:
        sent = await update.message.reply_html(f"{username} bukan admin.")
        asyncio.create_task(delete_message_after_delay(update.message, 30))
        asyncio.create_task(delete_message_after_delay(sent, 30))
    return False


async def start_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_permission(update, context, is_callback=False):
        return

    proxies = requests.get(f'{MIHOMO_API}/proxies', headers=HEADERS).json()['proxies']
    reply_markup = main_menu_keyboard(proxies)
    await update.message.reply_text(
        "Pilih grup proxy atau perintah:",
        reply_markup=reply_markup,
        reply_to_message_id=update.message.message_id
    )


async def button_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_permission(update, context, is_callback=True):
        return

    query = update.callback_query
    await query.answer()
    data = query.data

    await query.edit_message_text("Loading...")

    if data.startswith("select_"):
        group = data.split("_", 1)[1]
        group_info = requests.get(f'{MIHOMO_API}/proxies/{group}', headers=HEADERS).json()
        now_node = group_info.get('now', 'Tidak diketahui')
        nodes = group_info['all']

        buttons = [
            InlineKeyboardButton(
                f"{'✿ ' if p == now_node else ''}{p}",
                callback_data=f"choose_{group}_{p}"
            ) for p in nodes
        ]
        keyboard = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
        # Tambah tombol "Cek Delay" dan "Kembali"
        keyboard.append([
            InlineKeyboardButton("Cek Delay", callback_data=f"check_delay_{group}"),
            InlineKeyboardButton("Kembali", callback_data="back")
        ])
        await query.edit_message_text(
            text=f"*{group}* ➠ *{now_node}*\nList node:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data.startswith("check_delay_"):
        group = data.split("_", 2)[2]
        group_info = requests.get(f'{MIHOMO_API}/proxies/{group}', headers=HEADERS).json()
        nodes = group_info['all']

        latencies = await asyncio.gather(*[get_node_latency(group, node) for node in nodes])
        msg = f"*Delay untuk grup {group}:*\n"
        for node, latency in zip(nodes, latencies):
            msg += f"❀ {node}: {latency}ms\n"

        await query.edit_message_text(msg, parse_mode="Markdown")

    elif data.startswith("choose_"):
        _, group, proxy = data.split("_", 2)
        requests.put(f'{MIHOMO_API}/proxies/{group}', headers=HEADERS, json={"name": proxy})
        await query.edit_message_text(text=f"Proxy *{group}* ➠ *{proxy}*", parse_mode="Markdown")

    elif data == "status":
        proxies = requests.get(f"{MIHOMO_API}/proxies", headers=HEADERS).json()["proxies"]
        msg = "*Delay semua grup:*\n"
        for name, item in proxies.items():
            if item["type"] == "Selector":
                try:
                    delay = requests.get(
                        f"{MIHOMO_API}/proxies/{name}/delay?url=http://www.gstatic.com/generate_204&timeout=3000",
                        headers=HEADERS
                    ).json()
                    delay_time = delay.get('delay', 'timeout')
                except:
                    delay_time = "error"
                msg += f"❀ {name} ({delay_time}ms)\n"
        await query.edit_message_text(msg, parse_mode="Markdown")

    elif data == "reload":
        requests.put(f"{MIHOMO_API}/configs?force=true", headers=HEADERS, json={"path": "", "payload": ""})
        await query.edit_message_text("Config berhasil di-reload.")

    elif data == "restart":
        r = requests.post(f"{MIHOMO_API}/restart", headers=HEADERS)
        if r.status_code == 200:
            await asyncio.sleep(2)
            await query.edit_message_text("Restart selesai.")
        else:
            await query.edit_message_text("Gagal me-restart.")

    elif data == "upgrade":
        r = requests.post(f"{MIHOMO_API}/upgrade", headers=HEADERS)
        if r.status_code == 200:
            await asyncio.sleep(3)
            await query.edit_message_text("Berhasil diperbarui.")
        elif r.status_code == 500:
            await query.edit_message_text("Tidak ada pembaruan.")
        else:
            await query.edit_message_text("Gagal memperbarui.")

    elif data == "version":
        version = requests.get(f"{MIHOMO_API}/version", headers=HEADERS).json()
        await query.edit_message_text(f"`{version['version']}`", parse_mode="Markdown")

    elif data == "back":
        proxies = requests.get(f'{MIHOMO_API}/proxies', headers=HEADERS).json()['proxies']
        reply_markup = main_menu_keyboard(proxies)
        await query.edit_message_text("Kembali ke menu utama:", reply_markup=reply_markup)