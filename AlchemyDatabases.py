from sqlalchemy import create_engine, MetaData, Table, Integer, String, \
    Column, DateTime, ForeignKey, Numeric, BigInteger, Boolean

import os
from datetime import datetime
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
import sqlalchemy.orm as sqla_orm
import sqlalchemy as sqla


CONFIG = {
    "host": os.environ['TGBOT_DB_HOST'],
    "user": os.environ['TGBOT_DB_USER'],
    "password": os.environ['TGBOT_DB_PASS'],
    "database": os.environ['TGBOT_DB_NAME'],
}

ENGINE = create_engine("mysql://%s:%s@%s:3306/%s" %
                       (CONFIG["user"], CONFIG["password"], CONFIG["host"], CONFIG["database"]),
                       echo=True)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    user_id             = Column(Integer, primary_key=True)
    tg_id               = Column(BigInteger, nullable=False)
    username            = Column(String(32), nullable=True)
    first_name          = Column(String(64), nullable=True)
    last_name           = Column(String(64), nullable=True)
    registration_date   = Column(DateTime, nullable=True)
    last_seen_date      = Column(DateTime, nullable=True)
    photos              = relationship("Photo")
    storages            = relationship("Storage")

    def __init__(self, tg_id, username, first_name, last_name=None):
        self.tg_id = tg_id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.registration_date = datetime.utcnow()
        self.last_seen_date = datetime.utcnow()

    def __repr__(self):
        res = "<User(tg_id=%s, username=%s, first_name=%s, last_name=%s)>" % (
            self.tg_id, self.username, self.first_name, self.last_name)
        return res




class Storage(Base):
    __tablename__ = "storages"
    storage_id          = Column(Integer, primary_key=True)
    path                = Column(String(36), nullable=False)
    type                = Column(String(8), nullable=False)
    size                = Column(BigInteger, nullable=False)
    used_space          = Column(BigInteger, nullable=False)
    created_date        = Column(DateTime, nullable=True)
    modified_date       = Column(DateTime, nullable=True)
    user_id             = Column(Integer, ForeignKey("users.user_id"))
    photos              = relationship("Photo")

    def __init__(self, path, user_id, type="local", size=256*1024*1024):
        self.path = path
        self.type = type
        self.size = size
        self.used_space = 0
        self.created_date = datetime.utcnow()
        self.modified_date = datetime.utcnow()
        self.user_id = user_id

    def __repr__(self):
        res = "<Storage(path=%s, type=%s, size=%s, used_space=%s)>" % (
            self.path, self.type, self.size, self.created_date)
        return res


class Photo(Base):
    __tablename__ = "photos"
    photo_id            = Column(Integer, primary_key=True)
    filename            = Column(String(40), nullable=False)
    size                = Column(BigInteger, nullable=False)
    hash                = Column(String(64), nullable=True)
    upload_date         = Column(DateTime, nullable=True)
    storage_id          = Column(Integer, ForeignKey("storages.storage_id"))
    user_id             = Column(Integer, ForeignKey("users.user_id"))

    def __init__(self, filename, size, hash, storage_id, user_id):
        self.filename = filename
        self.size = size
        self.hash = hash
        self.storage_id = storage_id
        self.user_id = user_id
        self.upload_date = datetime.utcnow()

    def __repr__(self):
        res = "<Photo(filename=%s, size=%s)>" % (
            self.filename, self.size)
        return res


Base.metadata.create_all(bind=ENGINE)

SESSION: sqla_orm.Session = sqla_orm.sessionmaker(bind=ENGINE, autoflush=True, autocommit=False)()

