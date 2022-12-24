from datetime import datetime

import pytz
import requests
from telegram import InlineKeyboardButton

from utils.constants import URL_CURR_WEATHER, URL_ONE_CALL, PARAMS_ONE_CALL, PARAMS_CURR_WATHER, REPLY_MARKUP


def send_keyboard(update, context):
    context.bot.send_message(chat_id=update.message.chat_id,
                             text="You can choose an action:",
                             reply_markup=REPLY_MARKUP)
