import logging
import telegram
from decouple import config
from telegram import ParseMode, Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, Filters

from api import API
from sshControl import NodeRestart

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
chat_id = str()
node_desc = str()


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def send_keyboard(update, context):
    keyboard = [[KeyboardButton('/nodes'), KeyboardButton('/manage'), KeyboardButton('/watchdog')]]
    resize_keyboard = True
    one_time_keyboard = True
    selective = True

    json_dict = {
        'keyboard': [[keyboard[0][0].to_dict(), keyboard[0][1].to_dict()]],
        'resize_keyboard': resize_keyboard,
        'one_time_keyboard': one_time_keyboard,
        'selective': selective,
    }

    message = update.message.reply_text(
        "Make your selection",
        reply_markup=telegram.ReplyKeyboardMarkup(keyboard, update))


def send_nodes_status(update, context):
    update.message.reply_text(API().get_status_for_nodes(), parse_mode=ParseMode.HTML, disable_web_page_preview=True)


def get_node_details(update, context):
    keyboard = []

    for node_name in API().get_node_list():
        keyboard.append([InlineKeyboardButton(text=node_name, callback_data=node_name)])

    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        update.callback_query.edit_message_text('please select the node',
                                                reply_markup=reply_markup)
    except Exception:
        update.message.reply_text('please select the node',
                                  reply_markup=reply_markup)


def button(update: Update, _: CallbackContext) -> None:
    global node_desc

    query = update.callback_query
    query.answer()

    keyboard = [
        [InlineKeyboardButton(text="Restart Node", callback_data="restart_node")],
        [InlineKeyboardButton(text="< Back", callback_data="back")]
    ]

    if query.data == "back":
        get_node_details(update, "getUpdates")
    elif query.data == "restart_node":
        NodeRestart().restart(API().get_node_api(node_desc))
        query.message.reply_text(text="Node was scheduled for restart")
        send_nodes_status(update)
    else:
        node_desc = query.data
        query.edit_message_text(text=API().get_status_for_node(node_desc), reply_markup=InlineKeyboardMarkup(keyboard))


def health_check(context):
    response = API().health_check()

    if len(response) > 0:
        context.bot.send_message(chat_id=chat_id,
                                 text="\n".join(response))


def run_watch_dog(update, context):
    global chat_id

    chat_id = update.message.chat_id
    context.bot.send_message(chat_id=update.message.chat_id,
                             text="Watching for node status change")

    context.job_queue.run_repeating(health_check, interval=180, first=1,
                                    context=update.message.chat_id)


def main():
    updater = Updater(config('TELEGRAM_API_KEY'), use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', send_keyboard, Filters.user(username=config('ADMIN_ID'))))
    dp.add_handler(CommandHandler('nodes', send_nodes_status, Filters.user(username=config('ADMIN_ID'))))
    dp.add_handler(CommandHandler('manage', get_node_details, Filters.user(username=config('ADMIN_ID'))))
    dp.add_handler(CallbackQueryHandler(button))
    dp.add_handler(
        CommandHandler('watchdog', run_watch_dog, Filters.user(username=config('ADMIN_ID')), pass_job_queue=True))

    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
