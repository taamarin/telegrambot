import os

from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from handlers.aa import init_db as init_limit_db, register_limit_handlers
from handlers.user_store import init_db as init_user_db, add_user, add_chat
from handlers.help import handle_help, help_callback
from handlers.info import info_menu, info_callback_handler
from handlers.stats import handle_botinfo
from handlers.restart import restart
from handlers.bash import handle_bash
from handlers.post import handle_post
from handlers.hostip import hostip
from handlers.broadcast import handle_broadcast
from handlers.yaml_checker import handle_checkyaml
from handlers.github import upload
from handlers.tcp import tcp_command, button_handler
from handlers.download import download_command
from handlers.dashboard import button_dashboard, start_dashboard
from handlers.clash import convert_handler
from handlers.clash_bfr import template_handler
from handlers.flclash import template_flclash_handler
from handlers.cmfa import template_cmfa_handler
from handlers.revclash import revclash
from handlers.sing import handle_sing
from handlers.sing_bfr import handle_bfr_sing
from handlers.sing_sfa import handle_sfa
from handlers.xray import handle_xray
from handlers.xbox import handle_box, handle_box_callback

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
NOTIFICATION_CHAT_ID = os.getenv("NOTIFICATION_CHAT_ID")


async def notify_startup(application):
    if NOTIFICATION_CHAT_ID:
        await application.bot.send_message(
            chat_id=NOTIFICATION_CHAT_ID,
            text="bot is running!!",
        )


def create_application():
    application = Application.builder().token(TOKEN).post_init(notify_startup).build()

    application.add_handler(CommandHandler("start", handle_help))
    application.add_handler(CommandHandler("stats", handle_botinfo))
    application.add_handler(CommandHandler("help", handle_help))
    application.add_handler(CommandHandler("restart", restart))
    application.add_handler(CommandHandler("upload", upload))
    application.add_handler(CommandHandler("sing", handle_sing))
    application.add_handler(CommandHandler("sbfr", handle_bfr_sing))
    application.add_handler(CommandHandler("sfa", handle_sfa))
    application.add_handler(CommandHandler("clash", convert_handler))
    application.add_handler(CommandHandler("cbfr", template_handler))
    application.add_handler(CommandHandler("flclash", template_flclash_handler))
    application.add_handler(CommandHandler("cmfa", template_cmfa_handler))
    application.add_handler(CommandHandler("revclash", revclash))
    application.add_handler(CommandHandler("xray", handle_xray))
    application.add_handler(CommandHandler("yaml", handle_checkyaml))
    application.add_handler(CommandHandler("sh", handle_bash))
    application.add_handler(CommandHandler("dpost", handle_post))
    application.add_handler(CommandHandler("hostip", hostip))
    application.add_handler(CommandHandler("broadcast", handle_broadcast))
    application.add_handler(CommandHandler("tcp", tcp_command))
    application.add_handler(CommandHandler("down", download_command))
    application.add_handler(CommandHandler("yacd", start_dashboard))
    application.add_handler(CommandHandler("xclash", handle_box))
    application.add_handler(CommandHandler("info", info_menu))

    application.add_handler(CallbackQueryHandler(help_callback, pattern="^help_|contact_admin|donate"))
    application.add_handler(CallbackQueryHandler(info_callback_handler, pattern="^info_"))
    application.add_handler(CallbackQueryHandler(handle_box_callback, pattern=r"^box_(status|restart|ceks|upk)$"))
    application.add_handler(CallbackQueryHandler(button_handler, pattern="^(set_westwood|set_bbr|cek_aktif|cek_tersedia)$"))
    application.add_handler(CallbackQueryHandler(button_dashboard))

    async def track_chat(update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        if chat:
            add_chat(chat.id, chat.type)

    application.add_handler(MessageHandler(filters.ALL, track_chat), group=-2)

    async def register_user(update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user:
            add_user(update.effective_user.id)

    application.add_handler(MessageHandler(filters.ALL, register_user), group=-1)

    register_limit_handlers(application)
    return application


def run_bot():
    if not TOKEN:
        raise RuntimeError("Set the TELEGRAM_BOT_TOKEN environment variable.")

    init_limit_db()
    init_user_db()
    application = create_application()
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    run_bot()
