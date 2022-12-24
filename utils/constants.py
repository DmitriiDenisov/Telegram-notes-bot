from telegram import ReplyKeyboardMarkup, InlineKeyboardButton
import json



tokens_path = 'tokens.json'

with open(tokens_path) as json_file:
    TOKENS = json.load(json_file)

EXISTING_NOTES = '📝 Existing Notes'
ADD_NOTE = '✍️ Add Note'
SHARING = '🔗 Shared docs'

querystring_goog = {"language": 'en', "sensor": "false",
                    "units": 'metric', "exclude": 'minutely,hourly'}
PARAMS_ONE_CALL = \
    {
        #"appid": TOKENS['one_call'],
        "units": 'metric',
        "exclude": 'minutely,hourly'
    }
PARAMS_CURR_WATHER = \
    {
        #"appid": TOKENS['curr_weather'],
        "units": 'metric'
    }

URL_GOOGLE_GEO = "https://maps.googleapis.com/maps/api/geocode/json?"
URL_ONE_CALL = "https://api.openweathermap.org/data/2.5/onecall"
URL_CURR_WEATHER = " https://api.openweathermap.org/data/2.5/weather"

main_keyboard = [[EXISTING_NOTES], [ADD_NOTE], [SHARING]]
REPLY_MARKUP = ReplyKeyboardMarkup(main_keyboard, one_time_keyboard=False)
