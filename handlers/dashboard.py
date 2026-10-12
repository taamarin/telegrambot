import requests
import asyncio
from html import escape
from urllib.parse import quote
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from handlers._admin import delete_message_after_delay, is_admin

MIHOMO_API = 'http://192.168.1.1:9090'
API_SECRET = '123456'
HEADERS = {'Authorization': f'Bearer {API_SECRET}'}


API_TIMEOUT = 10


async def api_request(method, path, *, params=None, json=None, check_status=True):
    response = await asyncio.to_thread(
        requests.request,
        method,
        f"{MIHOMO_API}{path}",
        headers=HEADERS,
        params=params,
        json=json,
        timeout=API_TIMEOUT
    )
    if check_status:
        response.raise_for_status()
    return response


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
        response = await api_request(
            "GET",
            f"/proxies/{quote(group, safe='')}/delay",
            params={
                "url": "http://www.gstatic.com/generate_204",
                "timeout": 3000,
                "name": node
            }
        )
        delay = response.json()
        return delay.get('delay', 'timeout')
    except (requests.RequestException, ValueError):
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

    try:
        response = await api_request("GET", "/proxies")
        proxies = response.json()['proxies']
        reply_markup = main_menu_keyboard(proxies)
    except (requests.RequestException, ValueError, KeyError, TypeError):
        await update.message.reply_text("Gagal mengambil data dashboard dari Clash.")
        return
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

    try:
        await handle_dashboard_action(query, data)
    except (requests.RequestException, ValueError, KeyError, TypeError):
        await query.edit_message_text("Gagal memproses permintaan dashboard Clash.")


async def handle_dashboard_action(query, data):
    if data.startswith("select_"):
        group = data.split("_", 1)[1]
        response = await api_request("GET", f"/proxies/{quote(group, safe='')}")
        group_info = response.json()
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
            text=f"<b>{escape(group)}</b> ➠ <b>{escape(str(now_node))}</b>\nList node:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    elif data.startswith("check_delay_"):
        group = data.split("_", 2)[2]
        response = await api_request("GET", f"/proxies/{quote(group, safe='')}")
        group_info = response.json()
        nodes = group_info['all']

        latencies = await asyncio.gather(*[get_node_latency(group, node) for node in nodes])
        msg = f"<b>Delay untuk grup {escape(group)}:</b>\n"
        for node, latency in zip(nodes, latencies):
            msg += f"❀ {escape(str(node))}: {escape(str(latency))}ms\n"

        await query.edit_message_text(msg, parse_mode="HTML")

    elif data.startswith("choose_"):
        _, group, proxy = data.split("_", 2)
        await api_request(
            "PUT",
            f"/proxies/{quote(group, safe='')}",
            json={"name": proxy}
        )
        await query.edit_message_text(
            text=f"Proxy <b>{escape(group)}</b> ➠ <b>{escape(proxy)}</b>",
            parse_mode="HTML"
        )

    elif data == "status":
        response = await api_request("GET", "/proxies")
        proxies = response.json()["proxies"]
        groups = [
            name for name, item in proxies.items()
            if item["type"] == "Selector"
        ]

        async def group_latency(name):
            try:
                response = await api_request(
                    "GET",
                    f"/proxies/{quote(name, safe='')}/delay",
                    params={
                        "url": "http://www.gstatic.com/generate_204",
                        "timeout": 3000
                    }
                )
                return response.json().get('delay', 'timeout')
            except (requests.RequestException, ValueError):
                return "error"

        latencies = await asyncio.gather(*(group_latency(name) for name in groups))
        msg = "<b>Delay semua grup:</b>\n"
        for name, delay_time in zip(groups, latencies):
            msg += f"❀ {escape(str(name))} ({escape(str(delay_time))}ms)\n"
        await query.edit_message_text(msg, parse_mode="HTML")

    elif data == "reload":
        await api_request(
            "PUT",
            "/configs",
            params={"force": "true"},
            json={"path": "", "payload": ""}
        )
        await query.edit_message_text("Config berhasil di-reload.")

    elif data == "restart":
        r = await api_request("POST", "/restart")
        if r.status_code == 200:
            await asyncio.sleep(2)
            await query.edit_message_text("Restart selesai.")
        else:
            await query.edit_message_text("Gagal me-restart.")

    elif data == "upgrade":
        r = await api_request("POST", "/upgrade", check_status=False)
        if r.status_code == 200:
            await asyncio.sleep(3)
            await query.edit_message_text("Berhasil diperbarui.")
        elif r.status_code == 500:
            await query.edit_message_text("Tidak ada pembaruan.")
        else:
            await query.edit_message_text("Gagal memperbarui.")

    elif data == "version":
        response = await api_request("GET", "/version")
        version = response.json()
        await query.edit_message_text(
            f"<code>{escape(str(version['version']))}</code>",
            parse_mode="HTML"
        )

    elif data == "back":
        response = await api_request("GET", "/proxies")
        proxies = response.json()['proxies']
        reply_markup = main_menu_keyboard(proxies)
        await query.edit_message_text("Kembali ke menu utama:", reply_markup=reply_markup)