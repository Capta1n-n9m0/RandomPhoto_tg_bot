import os

from telegram.ext import Updater, Dispatcher
from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters

from uuid import uuid4

from pathlib import Path

import logging
import logging.handlers

import random

import Databases

LOG_BASE_FORMAT = logging.Formatter("%(asctime)s [%(levelname)-5.5s]  <%(name)s>  %(message)s")
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

ACCOUNT_MAX_NUMBER = 40

STORAGE_DEFAULT_TYPE = "local"

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

        self.user = Databases.User()
        self.storage = Databases.Storage()
        self.photo = Databases.Photo()

        self.logger.info("Telegram bot has started")

    def start(self, update: Update, context: CallbackContext):
        tg_id = update.effective_user.id
        self.logger.debug(f"start called; user: {tg_id}")
        text = "Hello, i am a Random Photo Bot! I can select random photo, from photos provided!"
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        text = "You will have small storage of 256MB for you photos."
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        if len(self.user.select_by_tg_id(tg_id)) > 0:
            text = "Welcome! You can run /random to get a random photo from your storage or load more photos."
            context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        else:
            text = "Welcome! Looks like you are not registered yet."
            context.bot.send_message(chat_id=update.effective_chat.id, text=text)
            text = "Run /register to registrate. You will get 256MB of storage for your photos!"
            context.bot.send_message(chat_id=update.effective_chat.id, text=text)

    def register(self, update: Update, context: CallbackContext):
        tg_id = update.effective_user.id
        self.logger.debug(f"register called; user: {tg_id}")
        text = "Welcome! Now we will try to create an account for you!"
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        temp = self.user.select_by_tg_id(tg_id)
        if len(temp) == 0:
            if self.user.count() < ACCOUNT_MAX_NUMBER:
                user_id = self.user.insert(tg_id)
                storage_name = f"{uuid4()}"
                storage_fullpath = PHOTOS_FOLDER / f"{storage_name}"
                os.mkdir(f"{storage_fullpath}")
                self.storage.insert(user_id, storage_name)
                self.logger.info(f"user {tg_id} successfully registered")
                text = "Congratulations! Now you have a profile and 256MB of storage for your photos!"
                context.bot.send_message(chat_id=update.effective_chat.id, text=text)
            else:
                logging.warning(f"user {tg_id} couldn't register: user limit reached")
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
        tg_id = update.effective_user.id
        self.logger.debug(f"photo_saver called; user: {tg_id}")
        user_data = self.user.select_by_tg_id(tg_id)
        if len(user_data) == 0:
            text = "Sorry, you can't upload any photos, because you don't have an account!"
            context.bot.send_message(chat_id=update.effective_chat.id, text=text)
            text = "Run /register to get an account!"
            context.bot.send_message(chat_id=update.effective_chat.id, text=text)
            self.logger.warning(f"user {tg_id} failed uploading photo")
        else:
            user_data = user_data[0]
            user_id = user_data["user_id"]
            storage_data = self.storage.select_by_user_id(user_id)[0]
            size = storage_data["size"]
            used_space = storage_data["used_space"]
            if used_space < size:
                storage_type = storage_data["type"]
                if storage_type == "local":
                    storage_id = storage_data["storage_id"]
                    storage = storage_data["path"]
                    photo = update.message.photo[len(update.message.photo) - 1]
                    photo_size = photo.file_size
                    filename = f"{uuid4()}.png"
                    self.logger.info(f"File sent. id:{photo.file_id}, uid:{photo.file_unique_id}, size:{photo.file_size}, new_name:{filename}")
                    filepath = PHOTOS_FOLDER / storage / filename
                    photo.get_file(timeout=2).download(custom_path=filepath)
                    self.photo.insert(filename, photo_size, storage_id, user_id)
                    self.logger.info(f"File downloaded to {filepath} from {tg_id}")
                    self.storage.update_size_by_id(storage_id, used_space + photo_size)
                    text = "Photo uploaded!"
                    context.bot.send_message(chat_id=update.effective_chat.id, text=text)
                else:
                    self.logger.warning(f"Wrong storage type: {storage_type}, storage_id: {storage_data[0]}")
                    text = "Failed to upload photo. Contact alievabbas1@gmail.com"
                    context.bot.send_message(chat_id=update.effective_chat.id, text=text)

            else:
                text = "Sorry, you can't upload anymore photos, you are out of space!"
                context.bot.send_message(chat_id=update.effective_chat.id, text=text)
                text = "If you want to resize you storage or delete some photos, contact alievabbas1@gmail.com"
                context.bot.send_message(chat_id=update.effective_chat.id, text=text)

    def random_photo(self, update: Update, context: CallbackContext):
        tg_id = update.effective_user.id
        self.logger.debug(f"random_photo called; user: {tg_id}")
        user_data = self.user.select_by_tg_id(tg_id)
        if len(user_data) == 0:
            text = "Sorry, you can't call /random, because you don't have an account!"
            context.bot.send_message(chat_id=update.effective_chat.id, text=text)
            text = "Run /register to get an account!"
            context.bot.send_message(chat_id=update.effective_chat.id, text=text)
            self.logger.warning(f"user {tg_id} failed getting random photo")
        else:
            user_id = user_data[0]["user_id"]
            photo_data = self.photo.select_by_user_id(user_id)
            if len(photo_data) == 0:
                text = "Sorry, you can't call /random, because you don't have any photos!"
                context.bot.send_message(chat_id=update.effective_chat.id, text=text)
                text = "You can upload some just by sending them to the bot!"
                context.bot.send_message(chat_id=update.effective_chat.id, text=text)
            else:
                random_photo_path = random.choice(photo_data)["filename"]
                storage_path = self.storage.select_by_user_id(user_id)[0]["path"]
                full_photo_path = PHOTOS_FOLDER / storage_path / random_photo_path
                with open(full_photo_path, "rb") as f:
                    context.bot.send_photo(chat_id=update.effective_chat.id, photo=f)
                self.logger.info(f"Photo {full_photo_path} send to user {tg_id}")

    def run(self):
        self.updater.start_polling()



