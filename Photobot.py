import os

from telegram.ext import Updater, Dispatcher
from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters

from uuid import uuid4

from pathlib import Path

import mysql.connector

import logging
import logging.handlers

import random

LOG_BASE_FORMAT = logging.Formatter("%(asctime)s [%(levelname)-5.5s]  <%(name)>  %(message)s")
LOG_ROOT_LOGGER = logging.getLogger(__name__)
LOG_FILE_LOGGER = logging.handlers.RotatingFileHandler("telegram.log", mode='a', maxBytes=10*1024*1024, backupCount=10, encoding='UTF-8')
LOG_FILE_LOGGER.setFormatter(LOG_BASE_FORMAT)
LOG_FILE_LOGGER.setLevel("INFO")
LOG_ROOT_LOGGER.addHandler(LOG_FILE_LOGGER)
LOG_CONSOLE_LOGGER = logging.StreamHandler()
LOG_CONSOLE_LOGGER.setFormatter(LOG_BASE_FORMAT)
LOG_CONSOLE_LOGGER.setLevel("DEBUG")
LOG_ROOT_LOGGER.addHandler(LOG_CONSOLE_LOGGER)
LOG_ROOT_LOGGER.setLevel("DEBUG")


HTTP_API_KEY = os.environ['TGBOT_API_KEY']

ROOT_FOLDER = Path(__file__).parent
PHOTOS_FOLDER = ROOT_FOLDER / "photos"

DB_SETTINGS = {
    "host":         os.environ['TGBOT_DB_HOST'],
    "user":         os.environ['TGBOT_DB_USER'],
    "password":     os.environ['TGBOT_DB_PASS'],
    "database":     os.environ['TGBOT_DB_NAME'],
}

DB_HANDLER = mysql.connector.connect(**DB_SETTINGS)
DB_HANDLER.autocommit = True

DB_CURSOR = DB_HANDLER.cursor(buffered=True)

ACCOUNT_MAX_NUMBER = 40

STORAGE_DEFAULT_TYPE = "local"
STORAGE_DEFAULT_SIZE = 256*1024*1024


# DB_CURSOR.execute("SELECT * FROM `users` WHERE tg_id = 12356")
# print(DB_CURSOR.fetchone())


class Photobot:
    def __init__(self):
        self.logger = LOG_ROOT_LOGGER
        self.updater = Updater(token=HTTP_API_KEY, use_context=True)
        self.dispatcher: Dispatcher = self.updater.dispatcher

        self.start_handler = CommandHandler('start', self.start)
        self.updater.dispatcher.add_handler(self.start_handler)

        self.register_handler = CommandHandler('register', self.register)
        self.updater.dispatcher.add_handler(self.register_handler)

        self.echo_handler = MessageHandler(Filters.text & (~Filters.command), self.echo)
        self.updater.dispatcher.add_handler(self.echo_handler)

        self.caps_handler = CommandHandler('caps', self.caps)
        self.updater.dispatcher.add_handler(self.caps_handler)

        self.photo_handler = MessageHandler(Filters.photo, self.photo_saver)
        self.updater.dispatcher.add_handler(self.photo_handler)

        self.random_handler = CommandHandler('random', self.random_photo)
        self.updater.dispatcher.add_handler(self.random_handler)

        self.logger.info("Telegram bot has started")





    def start(self, update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        self.logger.debug(f"start called; user: {user_id}")
        text = "Hello, i am a Random Photo Bot! I can select random photo, from photos provided!"
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        text = "You will have small storage of 256MB for you photos."
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        DB_CURSOR.execute("SELECT * FROM `users` WHERE tg_id = %s;", (user_id,))
        if DB_CURSOR.rowcount:
            text = "Welcome! You can run /random to get a random photo from your storage or load more photos."
            context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        else:
            text = "Welcome! Looks like you are not registered yet."
            context.bot.send_message(chat_id=update.effective_chat.id, text=text)
            text = "Run /register to registrate. You will get 256MB of storage for your photos!"
            context.bot.send_message(chat_id=update.effective_chat.id, text=text)

    def register(self, update: Update, context: CallbackContext):
        tg_user_id = update.effective_user.id
        self.logger.debug(f"register called; user: {tg_user_id}")
        text = "Welcome! Now we will try to create an account for you!"
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        DB_CURSOR.execute("SELECT * FROM `users` WHERE tg_id = %s;", (tg_user_id,))
        temp = DB_CURSOR.fetchone()
        if temp is None:
            DB_CURSOR.execute("SELECT * FROM `users`;")
            if(DB_CURSOR.rowcount < ACCOUNT_MAX_NUMBER):
                DB_CURSOR.execute("INSERT INTO `users` (tg_id) VALUES (%s);", (tg_user_id,))
                DB_CURSOR.execute("SELECT * FROM `users` WHERE tg_id = %s;", (tg_user_id,))
                user_id = DB_CURSOR.fetchone()[0]
                storage_name = f"{uuid4()}"
                storage_fullpath = PHOTOS_FOLDER / f"{storage_name}"
                os.mkdir(f"{storage_fullpath}")
                DB_CURSOR.execute("INSERT INTO `storages` (type, path, size, used_space, user_id) VALUES (%s, %s, %s, %s, %s);",
                                  (STORAGE_DEFAULT_TYPE, storage_name, STORAGE_DEFAULT_SIZE, 0, user_id,))
                self.logger.info(f"user {tg_user_id} successfully registered")
                text = "Congratulations! Now you have a profile and 256MB of storage for your photos!"
                context.bot.send_message(chat_id=update.effective_chat.id, text=text)
            else:
                logging.warning(f"user {tg_user_id} couldn't register: user limit reached")
                text = "I am very sorry! There is now enough space for you... You can contact alievabbas@gmail.com for any questions."
                context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        else:
            text = "Looks like you already have registered! You can upload photos or run /random command!"
            context.bot.send_message(chat_id=update.effective_chat.id, text=text)


    def echo(self, update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        message = update.message.text
        text = f"Echo[Chat: {chat_id}, User: {user_id}]: \"{message}\""
        print("echo called")
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)

    def caps(self, update: Update, context: CallbackContext):
        text_caps = ' '.join(context.args).upper()
        print("caps called")
        context.bot.send_message(chat_id=update.effective_chat.id, text=text_caps)

    def photo_saver(self, update: Update, context: CallbackContext):
        tg_user_id = update.effective_user.id
        self.logger.debug(f"photo_saver called; user: {tg_user_id}")
        DB_CURSOR.execute("SELECT * FROM `users` WHERE tg_id = %s", (tg_user_id,))
        if DB_CURSOR.rowcount == 0:
            text = "Sorry, you can't upload any photos, because you don't have an account!"
            context.bot.send_message(chat_id=update.effective_chat.id, text=text)
            text = "Run /register to get an account!"
            context.bot.send_message(chat_id=update.effective_chat.id, text=text)
            self.logger.warning(f"user {tg_user_id} failed uploading photo")
        else:
            user_id = DB_CURSOR.fetchone()[0]
            DB_CURSOR.execute("SELECT * FROM `storages` WHERE user_id = %s;", (user_id,))
            query = DB_CURSOR.fetchone()
            size = query[3]
            used_space = query[4]
            if used_space < size:
                storage_type = query[1]
                if(storage_type == "local"):
                    storage_id = query[0]
                    storage = query[2]
                    photo = update.message.photo[len(update.message.photo) - 1]
                    photo_size = photo.file_size
                    filename = f"{uuid4()}.png"
                    filepath = PHOTOS_FOLDER / storage / filename
                    photo.get_file(timeout=2).download(custom_path=filepath)
                    DB_CURSOR.execute("INSERT INTO `photos` (storage_id, filename, size, owner_id) VALUES (%s, %s, %s, %s);",
                                      (storage_id, filename, photo_size, user_id))
                    self.logger.info(f"File downloaded to {filepath} from {tg_user_id}")
                    used_space += photo_size
                    DB_CURSOR.execute("UPDATE `storages` SET used_space = %s WHERE id = %s;", (used_space, storage_id))
                    text = "Photo uploaded!"
                    context.bot.send_message(chat_id=update.effective_chat.id, text=text)
                else:
                    self.logger.warning(f"Wrong storage type: {storage_type}, storage_id: {query[0]}")
                    text = "Failed to upload photo. Contact alievabbas1@gmail.com"
                    context.bot.send_message(chat_id=update.effective_chat.id, text=text)

            else:
                text = "Sorry, you can't upload anymore photos, you are out of space!"
                context.bot.send_message(chat_id=update.effective_chat.id, text=text)
                text = "If you want to resize you storage or delete some photos, contact alievabbas1@gmail.com"
                context.bot.send_message(chat_id=update.effective_chat.id, text=text)

        # photo = update.message.photo[len(update.message.photo) - 1]
        # filename = PHOTOS_FOLDER / f"{uuid4()}.png"
        # photo.get_file(timeout=30).download(custom_path=filename)
        # print(f"Photo saved to {filename}")

    def random_photo(self, update: Update, context: CallbackContext):
        tg_user_id = update.effective_user.id
        self.logger.debug(f"photo_saver called; user: {tg_user_id}")
        DB_CURSOR.execute("SELECT * FROM `users` WHERE tg_id = %s;", (tg_user_id,))
        if DB_CURSOR.rowcount == 0:
            text = "Sorry, you can't call /random, because you don't have an account!"
            context.bot.send_message(chat_id=update.effective_chat.id, text=text)
            text = "Run /register to get an account!"
            context.bot.send_message(chat_id=update.effective_chat.id, text=text)
            self.logger.warning(f"user {tg_user_id} failed getting random photo")
        else:
            user_id = DB_CURSOR.fetchone()[0]
            DB_CURSOR.execute("SELECT filename FROM `photos` WHERE owner_id = %s;", (user_id,))
            if DB_CURSOR.rowcount == 0:
                text = "Sorry, you can't call /random, because you don't have any photos!"
                context.bot.send_message(chat_id=update.effective_chat.id, text=text)
                text = "You can upload some just by sending them to the bot!"
                context.bot.send_message(chat_id=update.effective_chat.id, text=text)
            else:
                random_photo_path = random.choice(DB_CURSOR.fetchall())[0]
                DB_CURSOR.execute("SELECT path FROM `storages` WHERE user_id = %s;", (user_id,))
                storage_path = DB_CURSOR.fetchone()[0]
                full_photo_path = PHOTOS_FOLDER / storage_path / random_photo_path
                with open(full_photo_path, "rb") as f:
                    context.bot.send_photo(chat_id=update.effective_chat.id, photo=f)
                self.logger.info(f"Photo {full_photo_path} send to user {tg_user_id}")





    def run(self):
        self.updater.start_polling()



