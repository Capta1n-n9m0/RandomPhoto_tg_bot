import os

import mysql.connector
import logging

STORAGE_DEFAULT_TYPE = 256*1024*1024


class Database:
    cnx = None
    cursor = None
    n_tries = 0
    max_tries = 5
    logger = logging.getLogger(__name__)

    def __init__(self):
        self.config = {
            "host":         os.environ['TGBOT_DB_HOST'],
            "user":         os.environ['TGBOT_DB_USER'],
            "password":     os.environ['TGBOT_DB_PASS'],
            "database":     os.environ['TGBOT_DB_NAME'],
        }

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

    def if_user_exists(self, tg_id):
        self.logger.debug(f"if_user_exists called for {tg_id}")
        if not self.cnx.is_connected():
            self.connect()
        self.cursor.execute("SELECT * FROM `users` WHERE tg_id = %s;", (tg_id,))
        return self.cursor.rowcount > 0

    def get_user_by_id(self, user_id):
        self.logger.debug(f"get_user_by_id called for {user_id}")
        if not self.cnx.is_connected():
            self.connect()
        self.cursor.execute("SELECT * FROM `users` WHERE id = %s;", (user_id,))
        return self.cursor.fetchone()

    def get_user_by_tg_id(self, tg_id):
        self.logger.debug(f"get_user_by_tg_id called for {tg_id}")
        if not self.cnx.is_connected():
            self.connect()
        self.cursor.execute("SELECT * FROM `users` WHERE tg_id = %s;", (tg_id,))
        return self.cursor.fetchone()

    def get_user_count(self):
        self.logger.debug(f"get_user_count called")
        if not self.cnx.is_connected():
            self.connect()
        return self.cursor.rowcount

    def add_user(self, tg_id):
        self.logger.debug(f"add_user called {tg_id}")
        if not self.cnx.is_connected():
            self.connect()
        self.cursor.execute("INSERT INTO `users` (tg_id) VALUES (%s);", (tg_id,))
        return self.cursor.lastrowid

    def add_storage(self, path, user_id):

        query = "INSERT INTO `storages` (type, path, size, used_space, user_id) VALUES (%s, %s, %s, %s, %s);"

        self.cursor.execute("")










