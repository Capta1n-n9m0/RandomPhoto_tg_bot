import os

import mysql.connector

import logging

from mysql.connector import MySQLConnection

from telegram.user import User as TgUser

import datetime

STORAGE_DEFAULT_SIZE = 256*1024*1024
STORAGE_DEFAULT_TYPE = "local"


class Model:
    data = None
    lastrowid = None
    rowcount = None
    cnx: MySQLConnection = None
    cursor = None
    n_tries = 0
    max_tries = 5
    config = {
        "host":     os.environ['TGBOT_DB_HOST'],
        "user":     os.environ['TGBOT_DB_USER'],
        "password": os.environ['TGBOT_DB_PASS'],
        "database": os.environ['TGBOT_DB_NAME'],
    }

    def __init__(self, table=None):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.table = table

    @property
    def is_connected(self):
        if self.cnx is None or self.cursor is None:
            return False
        return self.cnx.is_connected()

    def reconnect(self):
        if not self.is_connected:
            self.connect()

    def connect(self):
        try:
            self.n_tries += 1
            self.cnx = mysql.connector.connect(**self.config)
            self.cnx.autocommit = True
            self.cursor = self.cnx.cursor(buffered=True, dictionary=True)
            self.n_tries = 0
        except mysql.connector.Error as err:
            self.cursor = None
            self.logger.error(
                "Failed to connect to database. Try {} of {}".format(self.n_tries, self.max_tries))
            if self.n_tries < self.max_tries:
                self.logger.error("Trying to connect once again.")
                self.connect()
            else:
                self.logger.error(
                    "Failed to connect after {} tries.".format(self.max_tries))
                raise err

    def close(self):
        self.cursor.close()
        self.cnx.close()


class User(Model):
    def __init__(self):
        super().__init__("users")

    def select_by_user_id(self, user_id) -> list[dict]:
        function_name = "User.select_by_user_id"
        self.logger.debug(f"{function_name} called for {user_id}")
        self.reconnect()
        self.cursor.execute("SELECT * FROM `users` WHERE user_id = %s;", (user_id,))
        self.data = self.cursor.fetchall()
        return self.data

    def select_by_tg_id(self, tg_id) -> list[dict]:
        function_name = "User.select_by_tg_id"
        self.logger.debug(f"{function_name} for {tg_id}")
        self.reconnect()
        self.cursor.execute("SELECT * FROM `users` WHERE tg_id = %s;", (tg_id,))
        self.data = self.cursor.fetchall()
        return self.data

    def count(self) -> int:
        function_name = "User.count"
        self.logger.debug(f"{function_name} called")
        self.reconnect()
        self.cursor.execute("SELECT * FROM `users`;")
        self.rowcount = self.cursor.rowcount
        return self.rowcount

    def insert(self, tg_id) -> int:
        function_name = "User.insert"
        self.logger.debug(f"{function_name} called for {tg_id}")
        self.reconnect()
        self.cursor.execute("INSERT INTO `users` (tg_id) VALUES (%s)", (tg_id,))
        self.lastrowid = self.cursor.lastrowid
        return self.lastrowid

    def insert_by_tg_user(self, tg_user: TgUser, registrate: bool = False) -> int:
        self.logger.debug("")
        self.reconnect()
        tg_id = tg_user.id
        tg_username = tg_user.username
        tg_first_name = tg_user.first_name
        tg_last_name = tg_user.last_name if tg_user.last_name else None
        if registrate:
            first_seen_date = datetime.datetime.now()
            registration_date = datetime.datetime.now()
            last_seen_date = datetime.datetime.now()
            if tg_last_name:
                query = "INSERT INTO `users` (tg_id, username, first_name, last_name, first_seen_date, registration_date, last_seen_date, is_registered) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);"
                arguments = (tg_id, tg_username, tg_first_name, tg_last_name, first_seen_date, registration_date, last_seen_date, registrate)
            else:
                query = "INSERT INTO `users` (tg_id, username, first_name, first_seen_date, registration_date, last_seen_date, is_registered) VALUES (%s, %s, %s, %s, %s, %s, %s);"
                arguments = (tg_id, tg_username, tg_first_name, first_seen_date, registration_date, last_seen_date, registrate)
        else:
            first_seen_date = datetime.datetime.now()
            last_seen_date = datetime.datetime.now()
            if tg_last_name:
                query = "INSERT INTO `users` (tg_id, username, first_name, last_name, first_seen_date, last_seen_date, is_registered) VALUES (%s, %s, %s, %s, %s, %s, %s);"
                arguments = (tg_id, tg_username, tg_first_name, tg_last_name, first_seen_date, last_seen_date, registrate)
            else:
                query = "INSERT INTO `users` (tg_id, username, first_name, first_seen_date, last_seen_date, is_registered) VALUES (%s, %s, %s, %s, %s, %s);"
                arguments = (tg_id, tg_username, tg_first_name, first_seen_date, last_seen_date, registrate)
        self.cursor.execute(query, arguments)
        self.lastrowid = self.cursor.lastrowid
        return self.lastrowid


class Storage(Model):
    def __init__(self):
        super().__init__("storages")

    def select_by_storage_id(self, storage_id) -> list[dict]:
        function_name = "Storage.select_by_storage_id"
        self.logger.debug(f"{function_name} called for {storage_id}")
        self.reconnect()
        self.cursor.execute("SELECT * FROM `storages` WHERE storage_id = %s;", (storage_id,))
        self.data = self.cursor.fetchall()
        return self.data

    def select_by_user_id(self, user_id) -> list[dict]:
        function_name = "Storage.select_by_user_id"
        self.logger.debug(f"{function_name} called for {user_id}")
        self.reconnect()
        self.cursor.execute("SELECT * FROM `storages` WHERE user_id = %s;", (user_id,))
        self.data = self.cursor.fetchall()
        return self.data

    def insert(self, user_id, path, type=STORAGE_DEFAULT_TYPE, size=STORAGE_DEFAULT_SIZE) -> int:
        function_name = "Storage.insert"
        self.logger.debug(f"{function_name} called for user:{user_id}, path:{path}, type: {type}, size:{size}")
        self.reconnect()
        created_date = datetime.datetime.now()
        query = "INSERT INTO `storages` (user_id, path, type, size, used_space, created_date, modified_date) VALUES (%s, %s, %s, %s, %s, %s, %s);"
        arguments = (user_id, path, type, size, 0, created_date, created_date)
        self.cursor.execute(query, arguments)
        self.lastrowid = self.cursor.lastrowid
        return self.lastrowid

    def update_size_by_id(self, storage_id, used_size) -> int:
        function_name = "Storage.update_size_by_id"
        self.logger.debug(f"{function_name} called for storage_id:{storage_id}, used_size:{used_size}")
        self.reconnect()
        modified_date = datetime.datetime.now()
        query = "UPDATE `storages` SET used_space = %s, modified_date = %s WHERE storage_id = %s;"
        arguments = (used_size, modified_date, storage_id)
        self.cursor.execute(query, arguments)
        self.lastrowid = self.cursor.lastrowid
        return self.lastrowid


class Photo(Model):
    def __init__(self):
        super().__init__("photos")

    def select_by_user_id(self, user_id) -> list[dict]:
        function_name = "Photo.select_by_user_id"
        self.logger.debug(f"{function_name} called for {user_id}")
        self.reconnect()
        self.cursor.execute("SELECT * FROM `photos` WHERE user_id = %s", (user_id,))
        self.data = self.cursor.fetchall()
        return self.data

    def count_by_user_id(self, user_id) -> int:
        function_name = "Photo.count_by_user_id"
        self.logger.debug(f"{function_name} called for {user_id}")
        self.reconnect()
        query = "SELECT * FROM `photos` WHERE user_id = %s;"
        arguments = (user_id,)
        self.cursor.execute(query, arguments)
        self.rowcount = self.rowcount
        return self.rowcount


    def insert(self, filename, size, storage_id, user_id, hash=None) -> int:
        function_name = "Photo.insert"
        self.logger.debug(f"{function_name} called for filename: {filename}, size: {size}, storage{storage_id}, user_id: {user_id}")
        self.reconnect()
        upload_date = datetime.datetime.now()
        query = "INSERT INTO `photos` (filename, size, storage_id, user_id, hash, upload_date) VALUES (%s, %s, %s, %s, %s, %s);"
        arguments = (filename, size, storage_id, user_id, hash, upload_date)
        self.cursor.execute(query, arguments)
        return self.cursor.lastrowid




