import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters import BoundFilter

from decouple import config

from api import API
from sshControl import NodeRestart

logging.basicConfig(filename="log",
                    filemode='a',
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

bot = Bot(config('TELEGRAM_API_KEY'))
dp = Dispatcher(bot)

chat_id = str()
node_desc = str()
is_watchdog_running = False
watchdog_timeout = 180


class CommandFilter(BoundFilter):
    key = 'is_admin'

    def __init__(self, is_admin):
        self.is_admin = is_admin

    async def check(self, message: types.Message):
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        return member.user.username == config("ADMIN_ID")


dp.filters_factory.bind(CommandFilter)


@dp.message_handler(commands=["start"], is_admin=True)
async def send_keyboard(message: types.Message):
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
    await message.reply(text="Please make your selection", reply_markup=markup)


@dp.message_handler(commands=['Nodes', 'UpdateStatus'], is_admin=True)
async def send_nodes_status(message: types.Message):
    if "UpdateStatus" in message.text:
        API().get_forced_update_from_api()

    await message.answer(API().get_status_for_nodes(), disable_web_page_preview=True)


@dp.message_handler(commands=['ManageNodes'], is_admin=True)
async def get_node_details(message: types.Message):
    keyboard = types.InlineKeyboardMarkup()

    for node_name in API().get_node_list():
        keyboard.add(types.InlineKeyboardButton(text=node_name, callback_data=node_name))

    keyboard.add(types.InlineKeyboardButton(text="RESTART ALL", callback_data="restart_all"))

    try:
        await message.edit_text(
            text="Select the Node:",
            reply_markup=keyboard
        )
    except Exception:
        await message.answer(text="Select the Node:", reply_markup=keyboard)


@dp.callback_query_handler(lambda call: True)
async def callback_worker(call: types.CallbackQuery):
    global node_desc

    query = call.data
    logging.info(str(call).encode('utf-8'))

    keyboard = types.InlineKeyboardMarkup()

    keyboard.add(types.InlineKeyboardButton(text="Restart Node", callback_data="restart_node"))
    keyboard.add(types.InlineKeyboardButton(text="< Back", callback_data="back"))

    if query == "back":
        await get_node_details(message=call.message)
    elif query == "restart_node":
        await bot.send_message(chat_id=call.message.chat.id, text="Node was scheduled for restart")
        await bot.send_message(chat_id=call.message.chat.id, text=NodeRestart().restart(API().get_node_ip(node_desc)))
    elif query == "restart_all":
        await bot.send_message(chat_id=call.message.chat.id, text="Scheduling all nodes for restart")
        await bot.send_message(chat_id=call.message.chat.id, text="\n".join(API().restart_all_nodes()))
    else:
        node_desc = query
        await bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=API().get_status_for_node(query),
            reply_markup=keyboard
        )


@dp.message_handler(commands=['Help'], is_admin=True)
async def send_command_description(message: types.Message):
    await message.answer(
        text="""List of available commands: \
        \n/Nodes - used to show the aggregated details for each node (status, description, version, etc.) \
        \n/ManageNodes - used to show the details for particular node and restarts it (if needed) \
        \n/RunWatchdog - launches the monitoring script (it will check the status for each node and \
        restarts it if it goes offline) \
        \n/UpdateStatus - bypasses the limit of 1 minute for each api call and gets a fresh node statuses \
        \n/Help - get info about available commands
        """)


async def health_check():
    response = API().health_check()

    if len(response) > 0:
        await bot.send_message(chat_id=chat_id, text="\n".join(response))


def repeat(coro, loop):
    asyncio.ensure_future(coro(), loop=loop)
    loop.call_later(watchdog_timeout, repeat, coro, loop)


@dp.message_handler(commands=['RunWatchdog'], is_admin=True)
async def run_watch_dog(message: types.Message):
    global chat_id, is_watchdog_running

    if not is_watchdog_running:
        chat_id = message.chat.id
        await message.answer(text="Watching for node status change")
        is_watchdog_running = True

        loop.call_later(watchdog_timeout, repeat, health_check, loop)
        now = datetime.utcnow()
        logging.info(f"{now}")
    else:
        await message.answer(text="Watchdog is already launched")


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    executor.start_polling(dp, skip_updates=True)
