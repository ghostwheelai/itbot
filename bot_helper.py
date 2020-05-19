from telegram import ChatAction, constants
from telegram.error import BadRequest
from functools import wraps
from menu import Menu
import re
import html
from db_helper import get_story_by_id, get_random_story, get_story_by_tag
import json
from user_helper import UserHandler
from utils import Utils
import logging
import configparser

def send_action(action):
    """Sends `action` while processing func command."""

    def decorator(func):
        @wraps(func)
        def command_func(self, update, context, *args, **kwargs):
            context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=action)
            return func(self, update, context, *args, **kwargs)

        return command_func

    return decorator


class BotHelper():

    def __init__(self):
        self.config =  configparser.ConfigParser()
        self.config.read("config.ini")
        self.user_helper = UserHandler(self.config)
        self.admin_id = self.config["admin"]["id"]
        self.menu = Menu(self.config)

    def error(self, update, context):

        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
        logger = logging.getLogger()
        logger.info(context.error)

        user = update.effective_user
        context.bot.send_message(chat_id=self.admin_id, text=str(context.error) + "\n\nUser: {}".format("@" + user.username if user.username is not None else user.first_name + " " + user.id))

    def send_message(self, update, context, message, show_button=True, story_id=None):

        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
        logger = logging.getLogger()
        
        self.user_helper.handle_user(update.effective_user, context)

        try:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message,
                parse_mode='HTML',
                reply_markup=self.menu.get_next_button(update, context) if show_button else None,
                disable_web_page_preview=True)
        except BadRequest as e:
            if e.message == "Message is too long":
                self.split_message(update, context, message)
            else:
                user = update.effective_user
                context.bot.send_message(chat_id=self.admin_id, text=e.message + "\n\nUser: {} id: {}".format("@" + user.username if user.username is not None else user.first_name, story_id))
                context.bot.send_message(chat_id=update.effective_chat.id, text="При обработке истории возникла ошибка. Отчет отправлен разработчику. id: {}".format(story_id))

    @send_action(ChatAction.TYPING)
    def get_random_story(self, update, context):

        story = json.loads(get_random_story())

        self.send_message(update, context, "Что-то пошло не так") if not story else self.send_story(update, context, story)

    @send_action(ChatAction.TYPING)
    def get_by_id(self, update, context, id=None):

        if context.args is not None or id is not None:

            if context.args is not None:
                if len(context.args) == 0:
                    self.set_state(update, context, "id")

            story = json.loads(get_story_by_id(id if id is not None else context.args[0]))
            self.send_message(update, context, "Истории с таким id нет") if not story else self.send_story(update, context, story)
        else:
            self.set_state(update, context, "id")

    def set_state(self, update, context, state):
        self.user_helper.set_state(update.effective_user.id, state)
        self.send_message(update, context, "Введите " + state, show_button=False)

    def get_by_tag(self, update, context, tag=None):

        if context.args is None and tag is None:
            self.set_state(update, context, "tag")
            return

        if context.args is not None:
            if len(context.args) != 0:
                story = json.loads(get_story_by_tag(" ".join(context.args)))
            else:
                self.set_state(update, context, "tag")
                return
        else:
            story = json.loads(get_story_by_tag(tag))

        self.send_message(update, context, "История с таким тегом не найдена") if not story else self.send_story(update, context, story)

    def send_story(self, update, context, story):

        tags = "" if story["tags"] == "" else "<i>{}</i>\n".format(story["tags"].replace(",", ", "))

        self.send_message(update, context,

                          ("<b>{}</b>\n".format(html.unescape(story["title"])) +
                          "<i>{}</i>\n".format(story["date"]) + tags +
                          self.format_story(story["story"]) +
                          "\n<a href='https://ithappens.me/story/{}'>ithappens.me</a> ".format(story["story_id"]) +
                          "id: {}\n".format(str(story["story_id"]))).replace("\n\n\n", "\n\n"),
                          story_id=story["story_id"]
                          )
        self.user_helper.set_state(update.effective_user.id, "ok")

    def format_story(self, story):

        story = html.unescape(story)
        story = self.check_internal_links(story)
        story = self.check_list(story)

        replacements = [('</p><blockquote><p>', '\n\n<i>'),
                        ('</p></blockquote><p>', '</i>\n\n'),
                        ('<blockquote><p>', '\n<i>'),
                        ('<p>', '\n'),
                        ('</p>', '\n'),
                        ('<br/>', '\n'),
                        ('<nobr>', ''),
                        ('</nobr>', ''),
                        ('<hr />', '\n<b>***</b>\n'),
                        ('<blockquote>', '\n<i>'),
                        ('</blockquote>', '</i>\n'),
                        ("<sup>",""),
                        ("</sup>","")]

        for tag, replacement in replacements:
            while re.search(tag, story) is not None:
                story = story.replace(tag, replacement)

        story = story.replace('<a href="…">', '&lt;a href="…"></a>')

        return story

    def check_internal_links(self, string):

        list = re.findall("[0-9]*[0-9].html", string)

        if len(list) > 0:
            for value in list:
                string = string.replace(value, "https://ithappens.me/story/" + value)

        return string

    def split_message(self, update, context, message):

        if len(message) > constants.MAX_MESSAGE_LENGTH:
            sub_msgs = []

            while len(message):

                split_point = message[:constants.MAX_MESSAGE_LENGTH].rfind('\n')

                if split_point != -1:
                    sub_msgs.append(message[:split_point])
                    message = message[split_point + 1:]

            for send_msg in sub_msgs[:-1]:
                self.send_message(update, context, send_msg, show_button=False)

            self.send_message(update, context, sub_msgs[-1])

    def check_list(self, message):

        tags = ["ul", "ol"]

        for tag in tags:

            while re.search("<{}><li><p>".format(tag), message) is not None:

                i = 1

                point = message.find("</p></li></{}>".format(tag))

                message = message.replace("<{}><li><p>".format(tag), "\n\n{}. ".format(i), 1)

                while message[:point].find("</p></li><li><p>") != -1:
                    i += 1
                    message = message.replace("</p></li><li><p>", "\n{}. ".format(i), 1)

                message = message.replace("</p></li></{}>".format(tag), "\n")

        return message

    def parse_request(self, update, context):

        state = self.user_helper.get_state(update.effective_user.id)

        if state == "id":
            self.get_by_id(update, context, id=update.message.text)
            self.user_helper.set_state(update.effective_user.id, "ok")
        elif state == "tag":
            self.get_by_tag(update, context, tag=update.message.text)
            self.user_helper.set_state(update.effective_user.id, "ok")

    def show_info(self, update, context):

        if update.effective_message.chat_id == self.admin_id:
            self.send_message(update, context, "Users: <b>{}</b>".format(self.user_helper.get_info()), show_button=False)

    def test_limit(self, update, context):

        for i in range(150):
            self.send_message(update, context, "<b>{}</b>".format(i), show_button=False)
