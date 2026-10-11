import re
import time
import asyncio
import socket
from urllib.parse import urlparse
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes
)
from html import escape

from handlers.user_store import increment_interaction
increment_interaction()

async def hostip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        domain_text = None

        if context.args:
            domain_text = " ".join(context.args)
        elif update.message.reply_to_message and update.message.reply_to_message.text:
            domain_text = update.message.reply_to_message.text.strip()
        else:
            await update.message.reply_text("/hostip `example.com`\nAtau balas pesan yang berisi domain.", parse_mode="MarkdownV2")
            return

        # Tampilkan pesan loading
        loading_msg = await update.message.reply_text("Loading...")

        # Ekstrak potensi domain atau URL dari teks
        candidates = re.findall(r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?', domain_text)
        domains = set()

        for item in candidates:
            if item.startswith("http://") or item.startswith("https://"):
                try:
                    parsed = urlparse(item)
                    if parsed.hostname:
                        domains.add(parsed.hostname)
                except Exception:
                    continue
            else:
                try:
                    parsed = urlparse("http://" + item)
                    if parsed.hostname:
                        domains.add(parsed.hostname)
                except Exception:
                    continue

        if not domains:
            await loading_msg.edit_text("Tidak ada domain valid ditemukan.")
            return

        responses = []
        for domain in domains:
            try:
                addr_info = socket.getaddrinfo(domain, None, proto=socket.IPPROTO_TCP)
                ipv4_addresses = set()
                ipv6_addresses = set()

                for entry in addr_info:
                    ip = entry[4][0]
                    if ":" in ip:
                        ipv6_addresses.add(ip)
                    else:
                        ipv4_addresses.add(ip)

                result = f"{domain}"
                if ipv4_addresses:
                    result += "\nIPv4: " + ", ".join(ipv4_addresses)
                if ipv6_addresses:
                    result += "\nIPv6: " + ", ".join(ipv6_addresses)
                if not ipv4_addresses and not ipv6_addresses:
                    result += "\nTidak ditemukan alamat IP."
                responses.append(result)
            except socket.gaierror:
                responses.append(f"*{domain}*\nTidak valid atau tidak dapat diakses.")

        await loading_msg.edit_text("\n\n".join(responses), parse_mode="Markdown")

        # Gabungkan jadi satu string, lalu escape karakter HTML-nya
        # escaped_result = escape("\n\n".join(responses))
        # await loading_msg.edit_text(
            # f'<blockquote class="expandable"><code>{escaped_result}</code></blockquote>',
            # parse_mode="HTML"
        # )

    except Exception as e:
        await update.message.reply_text("Format salah!! /hostip <url> | reply url")