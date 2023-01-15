import os

import asyncio
import logging
from aiogram.types import InputFile

from datetime import datetime
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters import BoundFilter
from aiogram.dispatcher.filters import Text
from decouple import config

from api_control.api import API
from api_control.stats import Stats
from graph import Graph
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
stats_parsing_timeout = 12 * 60 * 60  # 12 hours


class CommandFilter(BoundFilter):
    key = 'is_admin'

    def __init__(self, is_admin):
        self.is_admin = is_admin

    async def check(self, message: types.Message):
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        return member.user.username == config("ADMIN_ID")


dp.filters_factory.bind(CommandFilter)


async def set_commands(dp):
    await dp.bot.set_my_commands([
        types.BotCommand(command="nodes", description="Show Nodes"),
        types.BotCommand(command="managenodes", description="Show Nodes Details Or Restart"),
        types.BotCommand(command="runwatchdog", description="Start Node Monitoring Script"),
        types.BotCommand(command="stats", description="Show Nodes Stats"),
        types.BotCommand(command="updatestatus", description="Update Nodes"),
        types.BotCommand(command="updatestats", description="Update Stats"),
        types.BotCommand(command="help", description="Show Help"),
        types.BotCommand(command="graph", description="Display Earnings Graph Per Node Per Day"),
        types.BotCommand(command="aggregatedgraph", description="Display Aggregated Earnings Graph Per Day")
    ])


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

    nodes = types.KeyboardButton('Nodes')
    manage = types.KeyboardButton("Manage Nodes")
    force_update = types.KeyboardButton("Update Status")

    stats = types.KeyboardButton("Stats")
    force_update_stats = types.KeyboardButton("Update Stats")
    watchdog = types.KeyboardButton("Run Watchdog")

    get_help = types.KeyboardButton("Help")
    get_graph = types.KeyboardButton("Graph")
    get_aggregated_graph = types.KeyboardButton("Aggregated Graph")

    markup.row(nodes, manage, force_update)
    markup.row(stats, force_update_stats, watchdog)
    markup.row(get_help, get_graph, get_aggregated_graph)
    await message.reply(text="Please make your selection", reply_markup=markup)


@dp.message_handler(Text(equals=['Nodes'], ignore_case=True), is_admin=True)
@dp.message_handler(Text(equals=['Update Status'], ignore_case=True), is_admin=True)
@dp.message_handler(commands=["Nodes", "UpdateStatus"], is_admin=True)
async def send_nodes_status(message: types.Message):
    if "UpdateStatus" in message.text:
        API().get_forced_update_from_api()

    await message.answer(API().get_status_for_nodes(), disable_web_page_preview=True)


@dp.message_handler(Text(equals=['Stats'], ignore_case=True), is_admin=True)
@dp.message_handler(Text(equals=['Update Stats'], ignore_case=True), is_admin=True)
@dp.message_handler(commands=["Stats", "UpdateStats"], is_admin=True)
async def send_nodes_stats(message: types.Message):
    if "UpdateStats" in message.text:
        API().get_stats_for_nodes(True)

    count = 1
    nodes_reports = API().get_nodes_stats_report()

    for i in range(0, len(nodes_reports)):
        await message.answer(
            nodes_reports[i].replace("XX", count).replace("YY", len(nodes_reports)), disable_web_page_preview=True
        )
        count += 1


@dp.message_handler(Text(equals=['Manage Nodes'], ignore_case=True), is_admin=True)
@dp.message_handler(commands=["ManageNodes"], is_admin=True)
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


@dp.message_handler(Text(equals=['Help'], ignore_case=True), is_admin=True)
@dp.message_handler(commands=["Help"], is_admin=True)
async def send_command_description(message: types.Message):
    await message.answer(
        text="""List of available commands: \
        \n/Nodes - used to show the aggregated details for each node (status, description, version, etc.) \
        \n/ManageNodes - used to show the details for particular node and restarts it (if needed) \
        \n/RunWatchdog - launches the monitoring script (it will check the status for each node and \
        restarts it if it goes offline) \
        \n/UpdateStatus - bypasses the limit of 1 minute for each api call and gets a fresh node statuses \
        \n/Stats - display aggregated stats for each node \
        \n/UpdateStats - bypasses the limit of 1 minute for each api call and gets a fresh node stats \
        \n/Graph - displaying earnings per each node for a past month \
        \n/AggregatedGraph - displaying aggregated graph for all nodes per day for a past month \
        \n/Help - get info about available commands
        """)


@dp.message_handler(Text(equals=['Graph'], ignore_case=True), is_admin=True)
@dp.message_handler(commands=["Graph"], is_admin=True)
async def display_graph(message: types.Message):
    await message.answer("Generating a graph. Please wait!")
    Stats().store_nodes_earnings_stats()
    Graph().generate_graph_per_node()
    await message.answer("Graph were generated. Sending the picture")
    await message.answer_photo(InputFile(os.path.dirname(__file__) + "/img/graph.png"), "Earnings Graph")


@dp.message_handler(Text(equals=['Aggregated Graph'], ignore_case=True), is_admin=True)
@dp.message_handler(commands=["AggregatedGraph"], is_admin=True)
async def display_graph_aggregated(message: types.Message):
    await message.answer("Generating an aggregated graph. Please wait!")
    Stats().store_nodes_earnings_stats()
    Graph().generate_graph_per_day_for_all_nodes()
    await message.answer("Graph were generated. Sending the picture")
    await message.answer_photo(InputFile(os.path.dirname(__file__) + "/img/graph.png"), "Aggregated Earnings Graph")


async def health_check():
    response = API().health_check()

    if len(response) > 0:
        await bot.send_message(chat_id=chat_id, text="\n".join(response))


async def get_stats():
    logging.info("Getting updated stats in watchdog loop")
    Stats().store_nodes_earnings_stats()
    logging.info("Done")


def repeat(coro, loop):
    asyncio.ensure_future(coro(), loop=loop)
    loop.call_later(watchdog_timeout, repeat, coro, loop)


def repeat_for_stats(coro, loop):
    asyncio.ensure_future(coro(), loop=loop)
    loop.call_later(stats_parsing_timeout, repeat, coro, loop)


@dp.message_handler(Text(equals=['Run Watchdog'], ignore_case=True), is_admin=True)
@dp.message_handler(commands=["RunWatchdog"], is_admin=True)
async def run_watch_dog(message: types.Message):
    global chat_id, is_watchdog_running

    if not is_watchdog_running:
        chat_id = message.chat.id
        await message.answer(text="Watching for node status change")
        is_watchdog_running = True

        loop.call_later(watchdog_timeout, repeat, health_check, loop)
        loop.call_later(stats_parsing_timeout, repeat_for_stats, get_stats, loop)
        now = datetime.utcnow()
        logging.info(f"{now}")
    else:
        await message.answer(text="Watchdog is already launched")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    executor.start_polling(dp, skip_updates=True, on_startup=set_commands)
