from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
from telegram.ext import messagequeue as mq
from telegram.bot import Bot
from telegram.utils.request import Request
from telegram.error import BadRequest
from telegram import constants
from menu import Menu
import logging
from bot_helper import BotHelper
import re
import configparser


class MQBot(Bot):

    '''A subclass of Bot which delegates send method handling to MQ'''
    def __init__(self, *args, is_queued_def=True, mqueue=None, **kwargs):
        super(MQBot, self).__init__(*args, **kwargs)
        # below 2 attributes should be provided for decorator usage
        self._is_messages_queued_default = is_queued_def
        self._msg_queue = mqueue or mq.MessageQueue()

        self.config = configparser.ConfigParser()
        self.config.read("config.ini")

    def __del__(self):
        try:
            self._msg_queue.stop()
        except:
            pass

    def split_message(self, *args, **kwargs):

        reply_markup = kwargs['reply_markup']
        message = kwargs['text']

        if len(message) > constants.MAX_MESSAGE_LENGTH:
            sub_msgs = []

            while len(message):

                split_point = message[:constants.MAX_MESSAGE_LENGTH].rfind('\n')

                if split_point != -1:
                    sub_msgs.append(message[:split_point])
                    message = message[split_point + 1:]

            for send_msg in sub_msgs[:-1]:
                kwargs['text'] = send_msg
                kwargs['reply_markup'] = None
                self.send_message(*args, **kwargs)

            kwargs['text'] = sub_msgs[-1]
            kwargs['reply_markup'] = reply_markup

            self.send_message(*args, **kwargs)

    @mq.queuedmessage
    def send_message(self, *args, **kwargs):

        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
        logger = logging.getLogger()

        try:
            return super(MQBot, self).send_message(*args, **kwargs)
        except BadRequest as e:
            if e.message == "Message is too long":
                self.split_message(*args, **kwargs)
            else:

                logger.info(str(kwargs))

                story_id = re.findall(r'id: [0-9]+', kwargs['text'])

                user_id = kwargs['chat_id']
                username = self.get_chat(user_id).username

                kwargs['text'] = "При обработке запроса возникла ошибка. Отчет отправлен разработчику. {}".format(story_id[-1])
                kwargs['reply_markup'] = None
                super(MQBot, self).send_message(*args, **kwargs)

                kwargs['chat_id'] = self.config["admin"]["id"]
                kwargs['text'] = e.message + "\n\nUser: {} {}".format("@" + username if username is not None else user_id, story_id[-1])
                super(MQBot, self).send_message(*args, **kwargs)

def start():

    config = configparser.ConfigParser()
    config.read("config.ini")

    menu = Menu(config)
    bot_helper = BotHelper()

    q = mq.MessageQueue(all_burst_limit=29, all_time_limit_ms=1018)
    request = Request(con_pool_size=8)
    mqbot = MQBot(config["bot"]["token"], request=request, mqueue=q)
    updater = Updater(bot=mqbot, use_context=True)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', menu.get_main_menu))
    dp.add_handler(CommandHandler('story', bot_helper.get_random_story))
    dp.add_handler(CommandHandler('get', bot_helper.get_by_id, pass_args=True))
    dp.add_handler(CommandHandler('tag', bot_helper.get_by_tag, pass_args=True))
    dp.add_handler(CommandHandler('info', bot_helper.show_info))
    dp.add_handler(CommandHandler('testlimit', bot_helper.test_limit))
    dp.add_handler(CallbackQueryHandler(menu.get_main_menu, pattern="show_main_menu"))
    dp.add_handler(CallbackQueryHandler(menu.get_main_menu, pattern="print_main_menu"))
    dp.add_handler(CallbackQueryHandler(menu.show_options, pattern="show_options"))
    dp.add_handler(CallbackQueryHandler(menu.toogle_menu_button, pattern="options_toggle_button"))
    dp.add_handler(CallbackQueryHandler(bot_helper.get_random_story, pattern="random_story"))
    dp.add_handler(CallbackQueryHandler(bot_helper.get_by_id, pattern="story_by_id"))
    dp.add_handler(CallbackQueryHandler(bot_helper.get_by_tag, pattern="story_by_tag"))
    dp.add_handler(MessageHandler(Filters.text, bot_helper.parse_request))
    dp.add_error_handler(bot_helper.error)

    updater.start_polling()


if __name__=="__main__":
    start()
