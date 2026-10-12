import asyncio
import os

import requests
from telegram import Update
from telegram.ext import ContextTypes


async def handle_ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Gunakan: /ask <pertanyaan>")
        return

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        await update.message.reply_text(
            "Fitur AI belum dikonfigurasi. Atur environment variable OPENAI_API_KEY."
        )
        return

    prompt = " ".join(context.args)
    try:
        response = await asyncio.to_thread(
            requests.post,
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"******"},
            json={
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Kamu adalah asisten AI yang membantu pengguna. "
                            "Jawab dalam bahasa yang digunakan pengguna."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=30,
        )
        response.raise_for_status()
        answer = response.json()["choices"][0]["message"]["content"].strip()
        if not answer:
            raise ValueError("Empty response")
    except (requests.RequestException, ValueError, KeyError, IndexError):
        await update.message.reply_text("Maaf, AI tidak dapat menjawab saat ini.")
        return

    for start in range(0, len(answer), 4000):
        await update.message.reply_text(answer[start : start + 4000])
