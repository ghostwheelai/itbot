from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from user_helper import UserHandler
import logging
from pymongo import MongoClient


class Menu:

    def __init__(self, config):
        self.user_helper = UserHandler(config)
        self.config = config

    def build_menu(self, buttons,
                   n_cols,
                   header_buttons=None,
                   footer_buttons=None):
        menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
        if header_buttons:
            menu.insert(0, header_buttons)
        if footer_buttons:
            menu.append(footer_buttons)
        return menu

    def send_menu(self, update, context, reply_markup, message):

        # logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
        # logger = logging.getLogger()
        #
        # logger.info(update.callback_query)

        if not update.callback_query or update.callback_query.data == "print_main_menu":
            context.bot.send_message(chat_id=update.effective_chat.id, parse_mode='HTML', text=message,
                                 reply_markup=reply_markup)
        else:
            context.bot.edit_message_text(chat_id=update.effective_chat.id, parse_mode="HTML", message_id=update.callback_query.message.message_id,
                                      text=message, reply_markup=reply_markup)

    def get_main_menu(self, update, context):

        self.user_helper.handle_user(update.effective_user, context)

        button_list = [
            InlineKeyboardButton("Поиск по тегу", callback_data="story_by_tag"),
            InlineKeyboardButton("Поиск по id", callback_data="story_by_id"),
        ]

        self.send_menu(update, context, InlineKeyboardMarkup(self.build_menu(button_list, n_cols=2,
            header_buttons=[InlineKeyboardButton("Случайная история", callback_data="random_story")],
            footer_buttons=[InlineKeyboardButton("Настройки", callback_data="show_options")])
        ), "Выберите пункт меню")

    def get_next_button(self, update, context):

        button_state = self.user_helper.get_show_menu_button_state(self, update.effective_user)

        button_next = InlineKeyboardButton("Next", callback_data="random_story")
        button_menu = InlineKeyboardButton("Menu", callback_data="print_main_menu")

        if button_state:
            return InlineKeyboardMarkup(self.build_menu([button_menu, button_next], n_cols=2))
        else:
            return InlineKeyboardMarkup(self.build_menu([button_next], n_cols=1))

    def get_trakt_menu(self, update, context):

        button_list = [
            InlineKeyboardButton("Календарь", callback_data="trakt_menu_calendar"),
            InlineKeyboardButton("Опции", callback_data="trakt_menu_options"),
            InlineKeyboardButton("Назад", callback_data="main_menu")
        ]

        self.send_menu(update, context, InlineKeyboardMarkup(self.build_menu(button_list, n_cols=1)), "Выберите пункт меню")

    def get_trakt_menu_calendar(self, update, context):

        button_list = [
            InlineKeyboardButton("Сегодня", callback_data="trakt_calendar_today"),
            InlineKeyboardButton("7 дней", callback_data="trakt_calendar_7days"),
            InlineKeyboardButton("Назад", callback_data="trakt_menu_main")
        ]

        self.send_menu(update, context, InlineKeyboardMarkup(self.build_menu(button_list, n_cols=2)), "Выберите пункт меню")

    def show_options(self, update, context):

        state = self.user_helper.get_show_menu_button_state(self, update.effective_user)

        button_list = [
            InlineKeyboardButton("Показывать кнопку меню" if not state else "Скрыть кнопку меню", callback_data="options_toggle_button"),
            InlineKeyboardButton("Назад", callback_data="show_main_menu")
        ]

        self.send_menu(update, context, InlineKeyboardMarkup(self.build_menu(button_list, n_cols=1)), "Выберите пункт меню")


    def toogle_menu_button(self, update, context):


        client = MongoClient("mongodb://" + self.config["mongodb"]["user"] + ":" + self.config["mongodb"]["password"] + "@" + self.config["mongodb"]["host"])

        users = client.itbot.users
        id = update.effective_user.id

        state = users.find_one({"id": id})["show_menu_button"]

        users.update_one({"id": id}, {"$set": {"show_menu_button": False}}) if state else users.update_one({"id": id}, {
            "$set": {"show_menu_button": True}})

        self.show_options(update, context)

        client.close()
