import datetime
import os
import shutil
import time
import telegram.ext
from telegram.ext import Updater, Dispatcher
from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters
from uuid import uuid4
from pathlib import Path
import random
import hashlib
import logging
import logging.handlers
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
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)-5.5s]  <%(name)s>  %(message)s",
    handlers=(LOG_FILE_LOGGER, LOG_CONSOLE_LOGGER)
)
from AlchemyDatabases import User, Photo, Storage, SESSION

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
        self.sql = SESSION
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
        self.photo_handler = MessageHandler(Filters.photo, self.photo_saver)
        self.dispatcher.add_handler(self.photo_handler)
        self.random_handler = CommandHandler('random', self.random_photo)
        self.dispatcher.add_handler(self.random_handler)
        self.statistics_handler = CommandHandler('stats', self.statistics)
        self.dispatcher.add_handler(self.statistics_handler)
        # Test handlers; undocumented commands


        self.logger.info("Telegram bot has started")

    def cleaner(self, context: telegram.ext.CallbackContext):
        t = time.time()
        for ids in self.user_sessions.keys():
            if round(t - self.user_sessions[ids]["timestamp"], 2) >= 10:
                chat_id = self.user_sessions[ids]["chat_id"]
                photos = self.user_sessions[ids]["photos"]
                text = f"Transmission ended after {round(t - self.user_sessions[ids]['first_photo'], 2)} seconds! {photos} received!"
                context.bot.send_message(chat_id=chat_id, text=text)
                del self.user_sessions[ids]
                break
            if (delta := round(t - self.user_sessions[ids]["deleting"], 2)) >= 20:
                chat_id = self.user_sessions[ids]["chat_id"]
                text = f"Deleting operation aborted after {delta}s."
                del self.user_sessions[ids]
                break

    def start(self, update: Update, context: CallbackContext):
        tg_id = update.effective_user.id
        chat_id = update.effective_chat.id
        self.logger.debug(f"start called; user: {tg_id}")
        text = "Hello, i am a Random Photo Bot! I can select random photo, from photos provided!"
        context.bot.send_message(chat_id=chat_id, text=text)
        with self.sql.begin() as s:
            user: User = s.query(User).filter(User.tg_id == tg_id).first()
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
            user: User = s.query(User).filter(User.tg_id == tg_id).first()
            n_users = s.query(User).count()
        if user is None:
            if n_users < ACCOUNT_MAX_NUMBER:
                try:
                    with self.sql.begin() as s:
                        new_user: User = User(tg_id=tg_id, username=username, last_name=last_name, first_name=first_name)
                        s.add(new_user)
                    self.logger.info(f"Created user record for {tg_id}")
                    storage_name = f"{uuid4()}"
                    storage_fullpath = PHOTOS_FOLDER / storage_name
                    os.mkdir(f"{storage_fullpath}")
                    with self.sql.begin() as s:
                        storage = Storage(path=storage_name, user_id=new_user.user_id)
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
        chat_id = update.effective_chat.id
        self.logger.debug(f"photo_saver called; user: {tg_id}")
        with self.sql.begin() as s:
            user: User = s.query(User).filter(User.tg_id == tg_id).first()
        if user is None:
            text = "Sorry, you can't upload any photos, because you don't have an account!"
            context.bot.send_message(chat_id=chat_id, text=text)
            text = "Run /register to get an account!"
            context.bot.send_message(chat_id=chat_id, text=text)
            self.logger.warning(f"user {tg_id} failed uploading photo")
        else:
            user_id = user.user_id
            with self.sql.begin() as s:
                storage: Storage = s.query(Storage).filter(Storage.user_id == user_id).first()
                storage_size = storage.size
                storage_used_space = storage.used_space
                if storage_used_space < storage_size:
                    if self.user_sessions.get(tg_id, None) is None:
                        text = "Starting the transmission! If no photos will be detected in 10 seconds transmission of photos will be considered closed."
                        self.user_sessions[tg_id] = {}
                        self.user_sessions[tg_id]["uploading"] = True
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
                    photo_record = Photo(filename=filename, size=photo_size, hash=f"{sha.hexdigest()}", storage_id=storage_id, user_id=user_id)
                    s.add(photo_record)
                    storage.used_space += photo_size
                    self.logger.info(f"Photo {photo_record.photo_id} added to {storage.storage_id}")
                else:
                    text = "Sorry, you can't upload anymore photos, you are out of space!"
                    context.bot.send_message(chat_id=chat_id, text=text)
                    text = "If you want to resize you storage or delete some photos, contact alievabbas1@gmail.com"
                    context.bot.send_message(chat_id=chat_id, text=text)

    def random_photo(self, update: Update, context: CallbackContext):
        tg_id = update.effective_user.id
        self.logger.debug(f"random_photo called; user: {tg_id}")
        chat_id = update.effective_chat.id
        with self.sql.begin() as s:
            user: User = s.query(User).filter(User.tg_id == tg_id).first()
        if user is None:
            text = "Sorry, you can't call /random, because you don't have an account!"
            context.bot.send_message(chat_id=chat_id, text=text)
            text = "Run /register to get an account!"
            context.bot.send_message(chat_id=chat_id, text=text)
            self.logger.warning(f"user {tg_id} failed getting random photo")
        else:
            user_id = user.user_id
            with self.sql.begin() as s:
                photos: tuple[Photo] = s.query(Photo).filter(Photo.user_id == user_id).all()
                storage: Storage = s.query(Storage).filter(Storage.user_id == user_id).first()
                storage_path = storage.path
            if len(photos) == 0:
                text = "Sorry, you can't call /random, because you don't have any photos!"
                context.bot.send_message(chat_id=chat_id, text=text)
                text = "You can upload some just by sending them to the bot!"
                context.bot.send_message(chat_id=chat_id, text=text)
            else:
                random_photo_path = random.choice(photos).filename
                full_photo_path = PHOTOS_FOLDER / storage_path / random_photo_path
                with open(full_photo_path, "rb") as f:
                    context.bot.send_photo(chat_id=chat_id, photo=f)
                self.logger.info(f"Photo {full_photo_path} send to user {tg_id}")

    def statistics(self, update: Update, context: CallbackContext):
        tg_id = update.effective_user.id
        chat_id = update.effective_chat.id
        with self.sql.begin() as s:
            user: User = s.query(User).filter(User.tg_id == tg_id).first()
            storage: Storage = s.query(Storage).filter(Storage.user_id == user.user_id).first()
            n_photos: int = s.query(Photo).filter(Photo.user_id == user.user_id).count()
            used_space_mb = (storage.used_space / 1024) / 1024
            total_space_mb = (storage.size / 1024) / 1024
        text = f"You have {n_photos} photos!"
        context.bot.send_message(chat_id=chat_id, text=text)
        text = f"You have used {used_space_mb:3.4f}MB / {total_space_mb:3.4f}MB"
        context.bot.send_message(chat_id=chat_id, text=text)

    def leave(self, update: Update, context: CallbackContext):
        tg_id = update.effective_user.id
        chat_id = update.effective_chat.id
        if self.user_sessions.get(tg_id, None) is None:
            self.user_sessions[tg_id] = {}
            text = "If you are sure you want to delete an account, run /leave again."
            context.bot.send_message(chat_id=chat_id, text=text)
            self.user_sessions[tg_id]["deleting"] = time.time()
            self.user_sessions[tg_id]["chat_id"] = chat_id
            text = "If you are sure you want to delete an account, run /leave again."
            context.bot.send_message(chat_id=chat_id, text=text)
            text = "If it was a mistake, just wait, process will be aborted in 20 seconds."
            context.bot.send_message(chat_id=chat_id, text=text)
        else:
            if self.user_sessions[tg_id].get("uploading", None) is None:
                if self.user_sessions[tg_id].get("deleting", None) is None:
                    self.user_sessions[tg_id]["deleting"] = time.time()
                    self.user_sessions[tg_id]["chat_id"] = chat_id
                    text = "If you are sure you want to delete an account, run /leave again."
                    context.bot.send_message(chat_id=chat_id, text=text)
                    text = "If it was a mistake, just wait, process will be aborted in 20 seconds."
                    context.bot.send_message(chat_id=chat_id, text=text)
                else:
                    with self.sql.begin() as s:
                        text = "Your account is being deleted now."
                        context.bot.send_message(chat_id=chat_id, text=text)
                        user: User = s.query(User).filter(User.tg_id == tg_id).first()
                        storage: Storage = s.query(Storage).filter(Storage.user_id == user.user_id).first()
                        photos: list[Photo] = s.query(Photo).filter(Photo.user_id == user.user_id).all()
                        storage_fullpath = PHOTOS_FOLDER / storage.path
                        s.delete(user)
                        s.delete(storage)
                        for photo in photos:
                            s.delete(photo)
                        shutil.rmtree(storage_fullpath)
                    text = "Your account and all your photos have been successfully deleted, it was nice having you."
                    context.bot.send_message(chat_id=chat_id, text=text)
            else:
                text = "Please wait for photo uploading to finnish before deleting your account."
                context.bot.send_message(chat_id=chat_id, text=text)



    def run(self):
        self.updater.start_polling()
        self.updater.idle()
        self.jobs.start()



