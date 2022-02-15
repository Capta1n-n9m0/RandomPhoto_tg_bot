import os

import mysql.connector
import logging

from mysql.connector import MySQLConnection

STORAGE_DEFAULT_SIZE = 256*1024*1024
STORAGE_DEFAULT_TYPE = "local"

class Model:
    cnx: MySQLConnection = None
    cursor = None
    n_tries = 0
    max_tries = 5
    logger = logging.getLogger(__name__)
    config = {
        "host":     os.environ['TGBOT_DB_HOST'],
        "user":     os.environ['TGBOT_DB_USER'],
        "password": os.environ['TGBOT_DB_PASS'],
        "database": os.environ['TGBOT_DB_NAME'],
    }

    def __init__(self, table=None):
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

    def select_by_user_id(self, user_id):
        function_name = "User.select_by_user_id"
        self.logger.debug(f"{function_name} called for {user_id}")
        self.reconnect()
        self.cursor.execute("SELECT * FROM `users` WHERE user_id = %s;", (user_id,))
        return self.cursor.fetchall()

    def select_by_tg_id(self, tg_id):
        function_name = "User.select_by_tg_id"
        self.logger.debug(f"{function_name} for {tg_id}")
        self.reconnect()
        self.cursor.execute("SELECT * FROM `users` WHERE tg_id = %s;", (tg_id,))
        return self.cursor.fetchall()

    def count(self):
        function_name = "User.count"
        self.logger.debug(f"{function_name} called")
        self.reconnect()
        self.cursor.execute("SELECT * FROM `users`;")
        return self.cursor.rowcount

    def insert(self, tg_id):
        function_name = "User.insert"
        self.logger.debug(f"{function_name} called for {tg_id}")
        self.reconnect()
        self.cursor("INSERT INTO `users` (tg_id) VALUES (%s)", (tg_id,))
        return self.cursor.lastrowid


class Storage(Model):
    def __init__(self):
        super().__init__("storages")

    def select_by_storage_id(self, storage_id):
        function_name = "Storage.select_by_storage_id"
        self.logger.debug(f"{function_name} called for {storage_id}")
        self.reconnect()
        self.cursor.execute("SELECT * FROM `storages` WHERE storage_id = %s;", (storage_id,))
        return self.cursor.fetchall()

    def select_by_user_id(self, user_id):
        function_name = "Storage.select_by_user_id"
        self.logger.debug(f"{function_name} called for {user_id}")
        self.reconnect()
        self.cursor.execute("SELECT * FROM `storages` WHERE user_id = %s;", (user_id,))
        return self.cursor.fetchall()

    def insert(self, user_id, path, type=STORAGE_DEFAULT_TYPE, size=STORAGE_DEFAULT_SIZE):
        function_name = "Storage.insert"
        self.logger.debug(f"{function_name} called for user:{user_id}, path:{path}, type: {type}, size:{size}")
        self.reconnect()
        self.cursor.execute("INSERT INTO `storages` (user_id, path, type, size, used_space) VALUES (%s, %s, %s, %s, %s);",
                            (user_id, path, type, size, 0))
        return self.cursor.lastrowid

    def update_size_by_id(self, storage_id, used_size):
        function_name = "Storage.update_size_by_id"
        self.logger.debug(f"{function_name} called for storage_id:{storage_id}, used_size:{used_size}")
        self.reconnect()
        self.cursor("UPDATE `storages` SET used_space = %s WHERE storage_id = %s;", (used_size, storage_id))
        return self.cursor.lastrowid


class Photo(Model):
    def __init__(self):
        super().__init__("photos")

    def select_by_user_id(self, user_id):
        function_name = "Photo.select_by_user_id"
        self.logger.debug(f"{function_name} called for {user_id}")
        self.reconnect()
        self.cursor.execute("SELECT * FROM `photos` WHERE user_id = %s", (user_id,))
        return self.cursor.fetchall()

    def insert(self, filename, size, storage_id, user_id):
        function_name = "Photo.insert"
        self.logger.debug(f"{function_name} called for filename: {filename}, size: {size}, storage{storage_id}, user_id: {user_id}")
        self.reconnect()
        self.cursor.execute("INSERT INTO `photos` (filename, size, storage_id, user_id) VALUES (%s, %s, %s, %s);"
                            , (filename, size, storage_id, user_id))
        return self.cursor.lastrowid



