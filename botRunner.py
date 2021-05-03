import logging

import telebot
from decouple import config
from telebot import types

from api import API
from sshControl import NodeRestart

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = telebot.logger
telebot.logger.setLevel(logging.INFO)

bot = telebot.TeleBot(config('TELEGRAM_API_KEY'), parse_mode=None)
chat_id = str()
node_desc = str()
is_watchdog_running = False


@bot.message_handler(commands=["start"])
def send_keyboard(message):
    global chat_id

    chat_id = message.chat.id

    resize_keyboard = True
    one_time_keyboard = False
    selective = True

    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=resize_keyboard,
        one_time_keyboard=one_time_keyboard,
        selective=selective
    )

    nodes = types.KeyboardButton('/Nodes')
    manage = types.KeyboardButton("/ManageNodes")
    watchdog = types.KeyboardButton("/RunWatchdog")

    force_update = types.KeyboardButton("/UpdateStatus")
    get_help = types.KeyboardButton("/Help")

    markup.row(nodes, manage, watchdog)
    markup.row(force_update, get_help)
    bot.send_message(chat_id, "Please make your selection", reply_markup=markup)


@bot.message_handler(commands=['Nodes', 'UpdateStatus'])
def send_nodes_status(message):
    if "UpdateStatus" in message.text:
        API().get_forced_update_from_api()

    bot.send_message(message.chat.id, API().get_status_for_nodes(), disable_web_page_preview=True)


@bot.message_handler(commands=['ManageNodes'])
def get_node_details(message):
    keyboard = types.InlineKeyboardMarkup()

    for node_name in API().get_node_list():
        keyboard.add(types.InlineKeyboardButton(text=node_name, callback_data=node_name))

    try:
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.json['message_id'],
            text="Select the Node:",
            reply_markup=keyboard
        )
    except Exception:
        bot.send_message(message.from_user.id, text="Select the Node:", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    global node_desc

    query = call.data

    keyboard = types.InlineKeyboardMarkup()

    keyboard.add(types.InlineKeyboardButton(text="Restart Node", callback_data="restart_node"))
    keyboard.add(types.InlineKeyboardButton(text="< Back", callback_data="back"))

    if query == "back":
        get_node_details(message=call.message)
    elif query == "restart_node":
        bot.send_message(chat_id=call.message.chat.id, text="Node was scheduled for restart")
        bot.send_message(chat_id=call.message.chat.id, text=NodeRestart().restart(API().get_node_ip(node_desc)))
    else:
        node_desc = query
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.json['message_id'],
            text=API().get_status_for_node(query),
            reply_markup=keyboard
        )


@bot.message_handler(commands=['Help'])
def send_command_description(message):
    bot.send_message(
        chat_id=message.chat.id,
        text="""List of available commands: \
        \n/Nodes - used to show the aggregated details for each node (status, description, version, etc.) \
        \n/ManageNodes - used to show the details for particular node and restarts it (if needed) \
        \n/RunWatchdog - launches the monitoring script (it will check the status for each node and restarts it if it goes offline) \
        \n/UpdateStatus - bypasses the limit of 1 minute for each api call and gets a fresh node statuses \
        \n/Help - get info about available commands
        """)


def health_check(message):
    response = API().health_check()

    if len(response) > 0:
        bot.send_message(chat_id=message.chat.id, text="\n".join(response))


@bot.message_handler(commands=['RunWatchdog'])
def run_watch_dog(message):
    global chat_id, is_watchdog_running

    if not is_watchdog_running:
        chat_id = message.chat.id
        bot.send_message(chat_id=chat_id, text="Watching for node status change")
        is_watchdog_running = True

        #  TODO: make it run with scheduler
        bot.polling.runjob_queue.run_repeating(health_check, interval=180, first=1,
                                        context=update.message.chat_id)
    else:
        bot.send_message(chat_id=message.chat.id, text="Watchdog is already launched")


if __name__ == '__main__':
    bot.polling()
