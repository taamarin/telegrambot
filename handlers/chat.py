import json
import requests
import time
import re
import asyncio
import html
from telegram import Update
from telegram.ext import CallbackContext
from handlers._admin import delete_message_after_delay, is_admin

from handlers.user_store import increment_interaction
increment_interaction()

async def handle_chat(update: Update, context: CallbackContext):
    # Periksa apakah ada pesan yang di-reply
    if update.message.reply_to_message:
        original_message = update.message.reply_to_message.text
        user_input = " ".join(context.args)
        combined_input = f"{original_message}\n\n{user_input}".strip()
    else:
        user_input = " ".join(context.args)
        combined_input = user_input.strip()

    if not combined_input:
        await update.message.reply_text(
          "/chat `text`", parse_mode="MarkdownV2"
        )
        return

    try:
        token, expires_at = load_token()
        if time.time() >= expires_at:
            token, expires_at = get_new_token()

        model_name = "OPEN_AI_CHATGPT_4_0_CHAT_MODEL"
        parameters = {
            "temperature": 0.7,
            "topP": 1,
            "frequencyPenalty": 0,
            "presencePenalty": 0,
            "n": 1,
            "stop": []
        }
        messages = [
            {"role": "system", "content": "Kamu adalah AI bernama ChatGPT."},
            {"role": "user", "content": combined_input}
        ]
        data = {"model": model_name, "parameters": parameters, "messages": messages}

        response = send_request(data, token)
        assistant_response = process_response(response)

        # Escape semua karakter HTML
        safe_response = html.escape(assistant_response)

        # Format pesan dengan regex
        formatted_response = format_message(safe_response)

        await update.message.reply_text(formatted_response, parse_mode="HTML")

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def handle_reply(update: Update, context: CallbackContext):
    message = update.message
    if not message:
        return  # Tidak ada message, abaikan

    if message.reply_to_message and message.reply_to_message.from_user.id == context.bot.id:
        original_message = message.reply_to_message.text
        user_reply = message.text
        combined_input = f"{original_message}\n\n{user_reply}"

        try:
            token, expires_at = load_token()
            if time.time() >= expires_at:
                token, expires_at = get_new_token()

            model_name = "OPEN_AI_CHATGPT_4_0_CHAT_MODEL"
            parameters = {
                "temperature": 0.7,
                "topP": 1,
                "frequencyPenalty": 0,
                "presencePenalty": 0,
                "n": 1,
                "stop": []
            }
            messages = [
                {"role": "system", "content": "Kamu adalah AI bernama ChatGPT."},
                {"role": "user", "content": combined_input}
            ]
            data = {"model": model_name, "parameters": parameters, "messages": messages}

            response = send_request(data, token)
            chat_response = process_response(response)

            safe_response = html.escape(chat_response)
            formatted_response = format_message(safe_response)

            await message.reply_text(formatted_response, parse_mode='HTML')

        except Exception as e:
            await message.reply_text(f"Error: {e}")

def format_message(message):
    """Format message with markdown-like syntax."""
    message = re.sub(r"```(.*?)``", r"<pre><code>\1</code></pre>", message, flags=re.DOTALL)
    message = re.sub(r"`([^`]+)`", r"<code>\1</code>", message)
    message = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", message)
    message = re.sub(r"\*\*(.*?)", r"<b>\1</b>", message)
    message = re.sub(r"\#\#\#(.*?)", r"<b>\1</b>", message)
    message = re.sub(r"__(.*?)__", r"<i>\1</i>", message)
    message = re.sub(r"~~(.*?)~~", r"<s>\1</s>", message)
    return message

def send_request(data, token):
    url = "https://genie-production-yfvxbm4e6q-uc.a.run.app/v3/completions?stream=true"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    response = requests.post(url, headers=headers, json=data, stream=True)
    response.raise_for_status()
    return response

def process_response(response):
    chat_response = ""
    for chunk in response.iter_lines():
        line = chunk.decode("utf-8")
        if line.startswith("data:"):
            try:
                data_dict = json.loads(line[6:])
                chat_response += data_dict.get("content", "")
            except json.JSONDecodeError:
                continue
        if line.startswith("event: done"):
            break
    return chat_response.strip()

def load_token():
    try:
        with open("token_info.txt", "r") as file:
            token_info = json.load(file)
        if time.time() >= token_info['expires_at']:
            return get_new_token()
        return token_info["access_token"], token_info["expires_at"]
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return get_new_token()

def get_new_token():
    url = "https://securetoken.googleapis.com/v1/token?key=AIzaSyBkanDK4DjniXPjw7TWA1dp9bUeOyHov6c"
    headers = {"Content-Type": "application/json"}
    data = {
        "grantType": "refresh_token",
        "refreshToken": "AMf-vBxztAkcjH5-szemDJOy1l2cJJda4-Gfyl3J05wMDKGyy4WVs-ItlHEqhVPEMMoKii8LLYKV-z27l153-pbxZ6znyqEENOECofAs9QWXSaRUj3MUnUoWADI1YkPCgdSuumil-POoQqlBd4KaSxV4XsskgcRMwx2kFlyS0_HeBHO94AACOEM"
    }
    response = requests.post(url, headers=headers, json=data)
    response_data = response.json()

    access_token = response_data["access_token"]
    expires_in = int(response_data["expires_in"])
    expires_at = time.time() + expires_in

    with open("token_info.txt", "w") as file:
        token_info = json.dumps({"access_token": access_token, "expires_at": expires_at})
        file.write(token_info)

    return access_token, expires_at

async def handle_token(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    if not is_admin(user_id):
        username = update.effective_user.mention_html()
        sent_message = await update.message.reply_html(f"{username} not the admin, bro.")
        asyncio.create_task(delete_message_after_delay(update.message, 60))
        asyncio.create_task(delete_message_after_delay(sent_message, 60))
        return

    try:
        token, expires_at = get_new_token()
        sent_message = await update.message.reply_text("Token updated.")
    except Exception as e:
        sent_message = await update.message.reply_text(f"Error while updating token: {e}")

    # Hapus pesan setelah 60 detik
    asyncio.create_task(delete_message_after_delay(update.message, 60))
    asyncio.create_task(delete_message_after_delay(sent_message, 60))