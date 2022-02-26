import datetime
import os
import threading
import time

import telegram.ext
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
import AlchemyDatabases as adb
import hashlib

LOG_BASE_FORMAT = logging.Formatter("%(asctime)s [%(levelname)-5.5s]  <%(name)s>  %(message)s")
LOG_ROOT_LOGGER = logging.getLogger(__name__)
LOG_FILE_LOGGER = logging.handlers.RotatingFileHandler("telegram.log", mode='a', maxBytes=10*1024*1024, backupCount=10, encoding='UTF-8')
LOG_FILE_LOGGER.setFormatter(LOG_BASE_FORMAT)
LOG_FILE_LOGGER.setLevel(logging.INFO)
LOG_ROOT_LOGGER.addHandler(LOG_FILE_LOGGER)
LOG_CONSOLE_LOGGER = logging.StreamHandler()
LOG_CONSOLE_LOGGER.setFormatter(LOG_BASE_FORMAT)
LOG_CONSOLE_LOGGER.setLevel(logging.DEBUG)
LOG_ROOT_LOGGER.addHandler(LOG_CONSOLE_LOGGER)
LOG_ROOT_LOGGER.setLevel(logging.DEBUG)

HTTP_API_KEY = os.environ['TGBOT_API_KEY']

ROOT_FOLDER = Path(__file__).parent
PHOTOS_FOLDER = ROOT_FOLDER / "photos"

ACCOUNT_MAX_NUMBER = 40

STORAGE_DEFAULT_TYPE = "local"


class Photobot:
    def __init__(self):
        # Presetting variables; could be moved to class definition
        self.user_sessions = {}
        self.logger = LOG_ROOT_LOGGER
        self.updater = Updater(token=HTTP_API_KEY, use_context=True)
        self.dispatcher: Dispatcher = self.updater.dispatcher
        self.jobs: telegram.ext.JobQueue = self.updater.job_queue
        self.user = Databases.User()
        self.storage = Databases.Storage()
        self.photo = Databases.Photo()
        self.sql = adb.SESSION
        # Jobs
        self.cleaning_job = self.jobs.run_repeating(self.cleaner, interval=5, first=1)
        # Basic handlers for testing and reference
        self.echo_handler = MessageHandler(Filters.text & (~Filters.command), self.echo)
        self.dispatcher.add_handler(self.echo_handler)
        self.caps_handler = CommandHandler('caps', self.caps)
        self.dispatcher.add_handler(self.caps_handler)
        # Actually useful handlers
        self.start_handler = CommandHandler('start', self.start)
        self.dispatcher.add_handler(self.start_handler)
        self.register_handler = CommandHandler('register', self.register)
        self.dispatcher.add_handler(self.register_handler)
        self.photo_handler = MessageHandler(Filters.photo, self.photo_saver_)
        self.dispatcher.add_handler(self.photo_handler)
        self.random_handler = CommandHandler('random', self.random_photo)
        self.dispatcher.add_handler(self.random_handler)
        self.statistics_handler = CommandHandler('stats', self.statistics)
        self.dispatcher.add_handler(self.statistics_handler)
        # Test handlers; undocumented commands
        # self.TEST_start_handler = CommandHandler('start_test', self.start_)
        # self.dispatcher.add_handler(self.TEST_start_handler)
        # self.TEST_register_handler = CommandHandler('register_test', self.register_)
        # self.dispatcher.add_handler(self.TEST_register_handler)

        self.logger.info("Telegram bot has started")

    def cleaner(self, context: telegram.ext.CallbackContext):
        t = time.time()
        for ids in self.user_sessions.keys():
            if (delta := int(t - self.user_sessions[ids]["timestamp"])) >= 10:
                chat = self.user_sessions[ids]["chat_id"]
                photos = self.user_sessions[ids]["photos"]
                text = f"Transmission ended after {round(t - self.user_sessions[ids]['first_photo'], 2)} seconds! {photos} received!"
                context.bot.send_message(chat_id=chat, text=text)
                del self.user_sessions[ids]
                break

    def start(self, update: Update, context: CallbackContext):
        tg_id = update.effective_user.id
        chat_id = update.effective_chat.id
        self.logger.debug(f"start called; user: {tg_id}")
        text = "Hello, i am a Random Photo Bot! I can select random photo, from photos provided!"
        context.bot.send_message(chat_id=chat_id, text=text)
        with self.sql.begin() as s:
            user: adb.User = s.query(adb.User).filter(adb.User.tg_id == tg_id).first()
            if user is None:
                text = "Welcome! Looks like you are not registered yet."
                context.bot.send_message(chat_id=chat_id, text=text)
                text = "Run /register to registrate. You will get 256MB of storage for your photos!"
                context.bot.send_message(chat_id=chat_id, text=text)
            else:
                text = "Welcome! You can run /random to get a random photo from your storage or upload more photos."
                context.bot.send_message(chat_id=chat_id, text=text)

    def register(self, update: Update, context: CallbackContext):
        tg_id = update.effective_user.id
        username = update.effective_user.username
        first_name = update.effective_user.first_name
        last_name = update.effective_user.last_name
        chat_id = update.effective_chat.id
        self.logger.debug(f"register called; user: {tg_id}")
        text = "Welcome! Now we will now try to create an account for you!"
        context.bot.send_message(chat_id=chat_id, text=text)
        with self.sql.begin() as s:
            user: adb.User = s.query(adb.User).filter(adb.User.tg_id == tg_id).first()
            n_users = s.query(adb.User).count()
        if user is None:
            if n_users < ACCOUNT_MAX_NUMBER:
                try:
                    with self.sql.begin() as s:
                        new_user: adb.User = adb.User(tg_id=tg_id, username=username, last_name=last_name, first_name=first_name)
                        s.add(new_user)
                    self.logger.info(f"Created user record for {tg_id}")
                    storage_name = f"{uuid4()}"
                    storage_fullpath = PHOTOS_FOLDER / storage_name
                    os.mkdir(f"{storage_fullpath}")
                    with self.sql.begin() as s:
                        storage = adb.Storage(path=storage_name, user_id=new_user.user_id)
                        s.add(storage)
                    self.logger.info(f"Created storage {storage.storage_id} for user {new_user.user_id} tg_id {tg_id}")
                    self.logger.info(f"user {tg_id} successfully registered")
                    text = "Congratulations! Now you have a profile and 256MB of storage for your photos!"
                    context.bot.send_message(chat_id=update.effective_chat.id, text=text)
                except Exception as e:
                    # Cleaning sequence if registration failed
                    # TODO: Create cleaning sequence
                    ...
            else:
                logging.warning(f"user {tg_id} couldn't register: user limit reached")
                text = "I am very sorry, we couldn't create an account for you! We are out of storage space!"
                context.bot.send_message(chat_id=update.effective_chat.id, text=text)
                text = "Try again latter(much latter) or contact alievabbas1@gmail.com for any questions."
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
                    if self.user_sessions.get(tg_id, None) is None:
                        text = "Starting the transmission! If no photos will be detected in 10 seconds transmission of photos will be considered closed."
                        self.user_sessions[tg_id] = {}
                        self.user_sessions[tg_id]["photos"] = 0
                        self.user_sessions[tg_id]["chat_id"] = update.effective_chat.id
                        self.user_sessions[tg_id]["first_photo"] = time.time()
                        context.bot.send_message(chat_id=update.effective_chat.id, text=text)
                    self.user_sessions[tg_id]["timestamp"] = time.time()
                    self.user_sessions[tg_id]["photos"] += 1
                    storage_id = storage_data["storage_id"]
                    storage = storage_data["path"]
                    photo = update.message.photo[len(update.message.photo) - 1]
                    photo_size = photo.file_size
                    filename = f"{uuid4()}.png"
                    self.logger.info(f"File sent. id:{photo.file_id}, uid:{photo.file_unique_id}, size:{photo.file_size}, new_name:{filename}")
                    filepath = PHOTOS_FOLDER / storage / filename
                    photo.get_file(timeout=2).download(custom_path=filepath)
                    sha = hashlib.sha256()
                    with open(filepath, "rb") as f:
                        while data := f.read(1024*8):
                            sha.update(data)
                    self.photo.insert(filename, photo_size, storage_id, user_id, f"{sha.hexdigest()}")
                    self.logger.info(f"File downloaded to {filepath} from {tg_id}")
                    self.storage.update_size_by_id(storage_id, used_space + photo_size)
                else:
                    self.logger.warning(f"Wrong storage type: {storage_type}, storage_id: {storage_data[0]}")
                    text = "Failed to upload photo. Contact alievabbas1@gmail.com"
                    context.bot.send_message(chat_id=update.effective_chat.id, text=text)

            else:
                text = "Sorry, you can't upload anymore photos, you are out of space!"
                context.bot.send_message(chat_id=update.effective_chat.id, text=text)
                text = "If you want to resize you storage or delete some photos, contact alievabbas1@gmail.com"
                context.bot.send_message(chat_id=update.effective_chat.id, text=text)

    def photo_saver_(self, update: Update, context: CallbackContext):
        tg_id = update.effective_user.id
        chat_id = update.effective_chat.id
        self.logger.debug(f"photo_saver called; user: {tg_id}")
        with self.sql.begin() as s:
            user: adb.User = s.query(adb.User).filter(adb.User.tg_id == tg_id).first()
        if user is None:
            text = "Sorry, you can't upload any photos, because you don't have an account!"
            context.bot.send_message(chat_id=chat_id, text=text)
            text = "Run /register to get an account!"
            context.bot.send_message(chat_id=chat_id, text=text)
            self.logger.warning(f"user {tg_id} failed uploading photo")
        else:
            user_id = user.user_id
            with self.sql.begin() as s:
                storage: adb.Storage = s.query(adb.Storage).filter(adb.Storage.user_id == user_id).first()
                storage_size = storage.size
                storage_used_space = storage.used_space
            if storage_used_space < storage_size:
                if self.user_sessions.get(tg_id, None) is None:
                    text = "Starting the transmission! If no photos will be detected in 10 seconds transmission of photos will be considered closed."
                    self.user_sessions[tg_id] = {}
                    self.user_sessions[tg_id]["photos"] = 0
                    self.user_sessions[tg_id]["chat_id"] = update.effective_chat.id
                    self.user_sessions[tg_id]["first_photo"] = time.time()
                    context.bot.send_message(chat_id=chat_id, text=text)
                self.user_sessions[tg_id]["timestamp"] = time.time()
                self.user_sessions[tg_id]["photos"] += 1
                storage_id = storage.storage_id
                photo = update.message.photo[len(update.message.photo) - 1]
                photo_size = photo.file_size
                filename = f"{uuid4()}.png"
                self.logger.info(f"File received. id:{photo.file_id}, uid:{photo.file_unique_id}, size:{photo.file_size}, new_name:{filename}")
                filepath = PHOTOS_FOLDER / storage.path / filename
                photo.get_file(timeout=2).download(custom_path=filepath)
                sha = hashlib.sha256()
                with open(filepath, "rb") as f:
                    while data := f.read(8 * 1024):
                        sha.update(data)
                with self.sql.begin() as s:
                    photo_record = adb.Photo(filename=filename, size=photo_size, hash=f"{sha.hexdigest()}", storage_id=storage_id, user_id=user_id)
                    s.add(photo_record)
                    storage.size += photo_size
                    self.logger.info(f"Photo {photo_record.photo_id} added to {storage.storage_id}")
            else:
                text = "Sorry, you can't upload anymore photos, you are out of space!"
                context.bot.send_message(chat_id=chat_id, text=text)
                text = "If you want to resize you storage or delete some photos, contact alievabbas1@gmail.com"
                context.bot.send_message(chat_id=chat_id, text=text)



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

    def statistics(self, update: Update, context: CallbackContext):
        tg_id = update.effective_user.id
        self.logger.debug(f"statistics called for user {tg_id}")
        user_data = self.user.select_by_tg_id(tg_id)[0]
        storage_data = self.storage.select_by_user_id(user_data["user_id"])[0]
        n_photos = self.photo.count_by_user_id(user_data["user_id"])
        used_space_mb = (storage_data["used_space"] / 1024) / 1024
        total_space_mb = (storage_data["size"] / 1024) / 1024
        text = f"You have {n_photos} photos!"
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        text = f"You have used {used_space_mb:3.4f}MB / {total_space_mb:3.4f}MB"
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)





    def run(self):
        self.updater.start_polling()
        self.updater.idle()
        self.jobs.start()



