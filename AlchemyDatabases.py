from sqlalchemy import create_engine, MetaData, Table, Integer, String, \
    Column, DateTime, ForeignKey, Numeric, BigInteger, Boolean

import os
from datetime import datetime
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
import sqlalchemy.orm as sqla_orm
import sqlalchemy as sqla


Base = declarative_base()

CONFIG = {
    "host": os.environ['TGBOT_DB_HOST'],
    "user": os.environ['TGBOT_DB_USER'],
    "password": os.environ['TGBOT_DB_PASS'],
    "database": os.environ['TGBOT_DB_NAME'],
}

ENGINE = create_engine("mysql://%s:%s(%s):3306/%s" %
                       (CONFIG["user"], CONFIG["password"], CONFIG["host"], CONFIG["database"]),
                       echo=True)

SESSION = sqla_orm.Session(binds=ENGINE, autoflush=True, autocommit=True)

class User(Base):
    __tablename__ = "users"
    user_id             = Column(Integer, primary_key=True)
    tg_id               = Column(BigInteger, nullable=False)
    username            = Column(String(32), nullable=True)
    first_name          = Column(String(64), nullable=True)
    last_name           = Column(String(64), nullable=True)
    first_seen_date     = Column(DateTime, nullable=True)
    registration_date   = Column(DateTime, nullable=True)
    last_seen_date      = Column(DateTime, nullable=True)
    is_registered       = Column(Boolean, nullable=True)
    photos              = relationship("Photo")
    storages            = relationship("Storage")

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

    def __repr__(self):
        res = "<Photo(filename=%s, size=%s)>" % (
            self.filename, self.size)
        return res







