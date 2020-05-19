from pymongo import MongoClient
import logging
from datetime import datetime


class UserHandler():


    def __init__(self, config):

        self.user = config["mongodb"]["user"] 
        self.password = config["mongodb"]["password"]  
        self.host = config["mongodb"]["host"]
        self.admin = config["admin"]["id"]


    def get_state(self, id):

        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
        logger = logging.getLogger()

        client = MongoClient("mongodb://" + self.user + ":" + self.password + "@" + self.host)
        state = client.itbot.users.find_one({"id": id})["state"]
        client.close()

        return state

    def set_state(self, id, state):

         
        client = MongoClient("mongodb://" + self.user + ":" + self.password + "@" + self.host)
        client.itbot.users.update_one({"id": id}, {"$set": {"state": state}})
        client.close()


    def get_show_menu_button_state(self, smth_dontknow, user):

        client = MongoClient("mongodb://" + self.user + ":" + self.password + "@" + self.host)
        state = client.itbot.users.find_one({"id": user.id})["show_menu_button"]
        client.close()

        return state

    def handle_user(self, user, context):

        now = datetime.now()
        date = now.strftime("%d.%m.%Y %H:%M")

        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
        logger = logging.getLogger()


        client = MongoClient("mongodb://" + self.user + ":" + self.password + "@" + self.host)
        users = client.itbot.users

        if not users.find_one({'id': user.id}):

            data = {
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'language': user.language_code,
                'show_menu_button': True,
                'state': 'ok',
                'date': date
            }
            users.insert_one(data)

            logger.info("Inserted. Name = {}, Id={}".format(user.username, user.id))

            context.bot.send_message(chat_id=self.admin, text="User: {}\n\nTotal: {}".format( 
                "@" + user.username if user.username is not None else user.first_name, self.get_info()))
        else:
            client.itbot.users.update_one({'id': user.id}, {"$set": {"date": date}})

        client.close()

    def get_info(self):

        client = MongoClient("mongodb://" + self.user + ":" + self.password + "@" + self.host)
        users = client.itbot.users.count()
        client.close()

        return users
