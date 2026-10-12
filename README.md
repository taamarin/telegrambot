# Telegram bot

Set `TELEGRAM_BOT_TOKEN` to the bot token before starting the bot. The optional
`NOTIFICATION_CHAT_ID` environment variable enables the startup notification.
Set `OPENAI_API_KEY` to enable the `/ask` AI command. The optional `OPENAI_MODEL`
environment variable selects the model (default: `gpt-4o-mini`).

Start, stop, restart, or check the bot with `sh main.sh start`, `sh main.sh stop`,
`sh main.sh restart`, and `sh main.sh status`.
