import logging
import json
from collections import defaultdict
from functools import partial
from telegram import ParseMode, Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import ConversationHandler, MessageHandler, Filters, \
    PicklePersistence, CallbackQueryHandler, ContextTypes
from utils.constants import REPLY_MARKUP, ADD_NOTE, EXISTING_NOTES, SHARING, TOKENS

from utils.utils import send_keyboard
from telegram.ext import Updater, CommandHandler

# update.message.type - "private", "supergroup"
# update.message.chat_id - chat_id
# update.effective_user.name - user Telegram Nick
# update.effective_user.id - user_id

# STRUCT FOR NOTES:
# chat_data: {'notes': {'note_id':{'note_name': "", 'note': ""}}}

# STRUCT FOR ACCESS:
# Access_dict_owner:
# {'owner_id': {'note1_id' : [user1_nick, user2_nick], 'note2_id': [user3_nick]}}
# Access_dict_viewer
# {'viewer_nick': [(owner1_id, note1_id), (owner2_id, note2_id)] }
# STRUCT FOR MATCHING user_nick -> user_id
# {user_nick: user_id, ...}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


def max_(A: set):
    if A:
        return max(A)
    else:
        return 0


class NotesBot:
    def __init__(self, token):
        # self.access_dict = defaultdict(set)
        my_persistence = PicklePersistence(filename='data_storage')
        self.updater = Updater(token, persistence=my_persistence, use_context=True)

        if not self.updater.dispatcher.bot_data.get('access_dict_owner'):
            self.updater.dispatcher.bot_data['access_dict_owner'] = defaultdict(partial(defaultdict, set))

        if not self.updater.dispatcher.bot_data.get('access_dict_viewer'):
            self.updater.dispatcher.bot_data['access_dict_viewer'] = defaultdict(set)

        if not self.updater.dispatcher.bot_data.get('matching_user_nick_chatid'):
            self.updater.dispatcher.bot_data['matching_user_nick_chatid'] = dict()

        if not self.updater.dispatcher.bot_data.get('matching_chat_id_nick'):
            self.updater.dispatcher.bot_data['matching_chat_id_nick'] = dict()

        if not self.updater.dispatcher.bot_data.get('ids_notes'):
            self.updater.dispatcher.bot_data['ids_notes'] = set()

        dp = self.updater.dispatcher

        # if not context.get('access_dict'):

        add_note = ConversationHandler(
            entry_points=[MessageHandler(Filters.regex(f"^({ADD_NOTE})$"), self.add_note_intention)],

            states={
                1: [
                    MessageHandler(Filters.text, self.add_note_name)
                ],
                2: [
                    MessageHandler(Filters.text, self.add_note)
                ]
            },
            fallbacks=[]
        )

        edit_note = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.button)],
            states={
                'edit': [
                    MessageHandler(Filters.text, self.edit_note)
                ],
                'delete':
                    [
                        # here is empty because 'delete' option is handled insude self.button
                    ],
                'share': [
                    MessageHandler(Filters.text, self.share_add)
                ]
            },
            fallbacks=[]
        )

        # START
        dp.add_handler(CommandHandler('start', self.start))

        # NOTES
        dp.add_handler(add_note)
        dp.add_handler(MessageHandler(Filters.regex(f"^({EXISTING_NOTES})$"), self.existing_notes))
        dp.add_handler(edit_note)  # includes edit+delete+sharing

        # SHARING DOCS
        dp.add_handler(MessageHandler(Filters.regex(f"^({SHARING})$"), self.note_sharing_all))

        # SYSTEM / DEV
        dp.add_handler(CommandHandler('get', self.get))

        # If do not understand
        dp.add_handler(MessageHandler(Filters.text, self.not_understand))
        # Error handler:
        # dp.add_error_handler(self.error)

        # Start pooling
        self.updater.start_polling()
        self.updater.idle()

    def start(self, update, context):
        first_name = update.effective_user.first_name
        update.message.reply_text(f'Hi {first_name}!')

        user_nick = update.effective_user.name
        chat_id = update.message.chat_id
        context.bot_data['matching_user_nick_chatid'][user_nick] = chat_id
        context.bot_data['matching_chat_id_nick'][chat_id] = user_nick

        send_keyboard(update, context)
        return 1

    def add_note_intention(self, update, context):
        update.message.reply_text('Please send the name of your new Note:', reply_markup=ForceReply(True))
        return 1

    def add_note_name(self, update, context):
        if context.chat_data.get('notes'):
            if context.chat_data['notes'].get(update.message.text):
                update.message.reply_text('Note with such name already exists! Please delete it first')
                return ConversationHandler.END
            else:
                new_id = max_(context.bot_data['ids_notes']) + 1
                context.chat_data['notes'][new_id] = {"note_name": update.message.text, "note": ""}
        else:
            new_id = max_(context.bot_data['ids_notes']) + 1
            context.chat_data['notes'] = defaultdict(dict)
            context.chat_data['notes'][new_id] = {"note_name": update.message.text, "note": ""}
        context.chat_data['wants_to_add_note_id'] = new_id
        context.bot_data['ids_notes'].add(new_id)
        update.message.reply_text('Please add your Note:', reply_markup=ForceReply(True))
        return 2

    def add_note(self, update, context):
        note_id = context.chat_data['wants_to_add_note_id']
        context.chat_data['notes'][note_id]["note"] = update.message.text
        update.message.reply_text('Your note successfully saved!')
        context.chat_data['wants_to_add_note_id'] = None
        send_keyboard(update, context)
        return ConversationHandler.END

    def existing_notes(self, update, context):
        flag = False
        for note_id, note_dict in context.chat_data.get('notes', dict()).items():
            flag = True
            keyboard = [
                [
                    InlineKeyboardButton("Edit", switch_inline_query_current_chat="aaa",
                                         callback_data=json.dumps({"type": "edit", "note_id": note_id,
                                                                   "user_type": "owner"}))
                ],
                [
                    InlineKeyboardButton("Delete",
                                         callback_data=json.dumps({"type": "delete", "note_id": note_id,
                                                                   "user_type": "owner"}))
                ],
                [
                    InlineKeyboardButton("Share",
                                         callback_data=json.dumps({"type": "share", "note_id": note_id,
                                                                   "user_type": "owner"}))
                ]

            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text(f'*{note_dict["note_name"]}* \n{note_dict["note"]}',
                                      parse_mode=ParseMode.MARKDOWN,
                                      reply_markup=reply_markup)

        user_nick = update.effective_user.name
        # for groups
        if update.message.chat.type != 'private':
            if not flag:
                update.message.reply_text("Not found any existing notes!")
            return ConversationHandler.END
        for chat_id, note_id in context.bot_data['access_dict_viewer'][user_nick]:
            flag = True
            note_dict = self.updater.dispatcher.chat_data[chat_id]['notes'][note_id]
            keyboard = [
                [
                    InlineKeyboardButton("Edit", callback_data=json.dumps({"type": "edit", "note_id": note_id,
                                                                           "user_type": "guest"}))
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text(f'*[SHARED] {note_dict["note_name"]}* \n{note_dict["note"]}',
                                      parse_mode=ParseMode.MARKDOWN,
                                      reply_markup=reply_markup)

        if not flag:
            update.message.reply_text("Not found any existing notes!")
        return ConversationHandler.END

    def edit_note(self, update, context):
        data = context.chat_data['wants_to_edit_note']
        if data['user_type'] == 'owner':
            context.chat_data['notes'][data['note_id']]['note'] = update.message.text
            update.message.reply_text("Your note successfully updated!")
            context.chat_data['wants_to_edit_note'] = None
            send_keyboard(update, context, button=False)
            return ConversationHandler.END
        else:
            # find owner
            user_nick = update.effective_user.name
            for owner, note_id in context.bot_data['access_dict_viewer'][user_nick]:
                if note_id == data['note_id']:
                    self.updater.dispatcher.chat_data[owner]['notes'][note_id]['note'] = update.message.text
                    update.message.reply_text("Your note successfully updated!")
                    context.chat_data['wants_to_edit_note'] = None
                    send_keyboard(update, context, button=False)
                    return ConversationHandler.END
        update.message.reply_text(
            f"Something went wrong, I didn't find this note!")
        return ConversationHandler.END

    def delete_note(self, update, context, note_id_to_delete):
        chat_id = update.callback_query.message.chat.id
        # owner_id = update.effective_user.id

        if context.chat_data.get('notes').get(note_id_to_delete):
            # 1. Delete from user's notes
            del context.chat_data['notes'][note_id_to_delete]
            # 2. Delete fro unique ids
            self.updater.dispatcher.bot_data['ids_notes'].remove(note_id_to_delete)
            # 3. Remove from access_dict_owner
            if note_id_to_delete in context.bot_data['access_dict_owner'][chat_id].keys():
                del context.bot_data['access_dict_owner'][chat_id][note_id_to_delete]
            # 4. Remove from access_dict_viewer
            for user_nick_invite, set_notes in context.bot_data['access_dict_viewer'].items():
                set_notes.discard((chat_id, note_id_to_delete))

            context.bot.send_message(chat_id=chat_id, text="Your note successfully deleted!")
            return ConversationHandler.END

        note_name = context.chat_data.get('notes')[note_id_to_delete]
        context.bot.send_message(chat_id=chat_id, text=f"I didn't find note with name {note_name}!")
        return ConversationHandler.END

    def button(self, update: Update, context):
        """Parses the  cCallbackQuery and updates the message text."""
        # update.message.reply_text('Please send the name of your new Note:')
        query = update.callback_query

        # CallbackQueries need to be answered, even if no notification to the user is needed
        # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
        query.answer()

        chat_id = update.callback_query.message.chat.id
        data = json.loads(query.data)
        if data['user_type'] == 'guest':
            # find owner
            note_name = None
            user_nick = update.effective_user.name
            for owner, note_id in context.bot_data['access_dict_viewer'][user_nick]:
                if note_id == data['note_id']:
                    note_name = self.updater.dispatcher.chat_data[owner]['notes'][note_id]['note_name']
            if not note_name:
                context.bot.send_message(chat_id=chat_id, text="Something went wrong, I didn't find this note!")
                return ConversationHandler.END
        else:
            note_name = context.chat_data['notes'][data['note_id']]['note_name']

        if data['type'] == 'edit':
            text = f"Selected Note: {note_name}. Please type your updated Note:"
            context.bot.send_message(chat_id=chat_id, text=text, reply_markup=ForceReply(True))
            context.chat_data['wants_to_edit_note'] = {'note_id': data['note_id'], 'user_type': data['user_type']}
            return 'edit'
        elif data['type'] == 'delete':
            text = f"Selected Note: {note_name}"
            context.bot.send_message(chat_id=chat_id, text=text)
            self.delete_note(update, context, note_id_to_delete=data['note_id'])
            return ConversationHandler.END
        elif data['type'] == 'share':
            text = f"Write user's nick which will get access *(Use @ before users nickname)*:"
            context.bot.send_message(chat_id=chat_id, text=text, reply_markup=ForceReply(True))
            context.chat_data['wants_to_share_note'] = {'note_id': data['note_id'], 'note_name': note_name}
            return 'share'

    def share_add(self, update, context):
        # owner_id = update.effective_user.id
        chat_id = update.message.chat_id
        user_nick_invite = update.message.text
        note_id = context.chat_data.get('wants_to_share_note').get('note_id')
        note_name = context.chat_data.get('wants_to_share_note').get('note_name')
        context.chat_data['wants_to_share_note'] = None
        if note_name:
            # STRUCT FOR ACCESS:
            # Access_dict_owner:
            # {'owner': {'note_name' : [user1, user2], 'note_name2': [user3]}}
            # Access_dict_viewer
            # {'viewer': [(owner1, note_name1), (owner2, note_name2)] }
            context.bot_data['access_dict_owner'][chat_id][note_id].add(user_nick_invite)
            context.bot_data['access_dict_viewer'][user_nick_invite].add((chat_id, note_id))
            update.message.reply_text(f'User {user_nick_invite} got access to {note_name}!')
            send_keyboard(update, context)
            return ConversationHandler.END
        else:
            update.message.reply_text(f'Something went wrong, could not find the name of note')
            return ConversationHandler.END

    def note_sharing_all(self, update, context):
        # update.message.reply_text('Below you will see info about notes that you share and that are shared with you')
        user_nick = update.effective_user.name
        # user_id = update.effective_user.id

        # send all notes that are shared with you
        if not context.bot_data.get('access_dict_viewer').get(user_nick):
            update.message.reply_text('You have no notes shared with you')
        else:
            for chat_id, note_id in context.bot_data.get('access_dict_viewer').get(user_nick):
                note = self.updater.dispatcher.chat_data[chat_id]['notes'][note_id]
                owner_nick = context.bot_data['matching_chat_id_nick'][chat_id]
                update.message.reply_text(
                    f"Owner {owner_nick} sharing note '{note['note_name']}' with you, it is below: \n{note['note']}")

        chat_id = update.message.chat_id
        # send all notes that you sharing
        you_sharing = context.bot_data.get('access_dict_owner').get(chat_id)
        if you_sharing:
            for note_id, set_user in you_sharing.items():
                if set_user:
                    note_name = context.chat_data['notes'][note_id]['note_name']
                    update.message.reply_text(
                        f"Note '{note_name}' shared with users: {set_user}."
                        f" Note is below:\n{context.chat_data['notes'][note_id]['note']}")
        else:
            update.message.reply_text('You do not share any notes')

    def not_understand(self, update, context):
        context.bot.send_message(chat_id=update.message.chat_id,
                                 text="I didn't get your request. You can choose an action:",
                                 reply_markup=REPLY_MARKUP)

        # This function is only for development purposes, you can call from bot with commad /get ...

    def get(self, update, context):
        chat_id = str(update.message.chat_id)
        key = update.message.text.partition(' ')[2]

        if key == 'jobs':
            ans = ''
            jobs = context.job_queue.jobs()
            for job in jobs:
                if job.name.startswith(chat_id):
                    tz = str(job.tzinfo)
                    rem = str(job.removed)
                    name = str(str(job.name).split('_')[1])
                    next_t = str(job.next_t)
                    ans += f'Name: {name}\n Tz info: {tz}\n rem: {rem}\n nex_t: {next_t}\n'
                    ans += '-------------------------\n'
            if ans:
                update.message.reply_text(ans)
            else:
                update.message.reply_text('Queue is empty!')
            return True
        value = context.user_data.get(key)
        if value:
            update.message.reply_text(value)
        else:
            update.message.reply_text('Not found scheduled notifications')

    def error(self, update, context):
        """Log Errors caused by Updates."""
        chat_id = update.message.chat_id
        if not self.updater.persistence.user_data.get(chat_id).get('notifs'):
            update.message.reply_text('Please start the bot again by typing /start')
        # update.message.text
        logger.warning(f'Message {update.message.text} caused error {context.error} \
            Date: {update.message.date}')


def main():
    NotesBot(token=TOKENS["telegram_token"])


if __name__ == '__main__':
    main()
