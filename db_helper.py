import psycopg2
import json
import configparser
from psycopg2.extras import RealDictCursor

config = configparser.ConfigParser()
config.read("config.ini")

def exec(query):
    
    db = psycopg2.connect(
        host=config["postgres"]["host"],
        user=config["postgres"]["user"],
        password=config["postgres"]["password"],
        dbname=config["postgres"]["database"])

    cursor = db.cursor(cursor_factory=RealDictCursor)

    cursor.execute(query)

    result = cursor.fetchone()

    db.close()

    return result


def get_story_by_id(id):

    if not id.isdigit(): id = 99999999

    return json.dumps(exec("SELECT * FROM storydb WHERE story_id={}".format(id)), ensure_ascii=False).encode('utf8')


def get_story_by_tag(tag):
    return json.dumps(exec("SELECT * FROM storydb WHERE tags SIMILAR TO '%{}%' ORDER BY RANDOM() LIMIT 1;".format(tag.lower())), ensure_ascii=False).encode('utf8')


def get_random_story():
    return json.dumps(exec("SELECT * FROM storydb ORDER BY RANDOM() LIMIT 1"), ensure_ascii=False)
