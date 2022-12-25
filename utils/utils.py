from datetime import datetime

import pytz
import requests
from telegram import InlineKeyboardButton

# from utils.constants import URL_CURR_WEATHER, URL_ONE_CALL, PARAMS_ONE_CALL, PARAMS_CURR_WATHER, REPLY_MARKUP
from utils.constants import REPLY_MARKUP


def send_keyboard(update, context, button=False):
    if button:
        chat_id = update.callback_query.message.chat.id
        context.bot.send_message(chat_id=chat_id,
                                 text="You can choose an action:",
                                 reply_markup=REPLY_MARKUP)
    else:
        context.bot.send_message(chat_id=update.message.chat_id,
                                 text="You can choose an action:",
                                 reply_markup=REPLY_MARKUP)
