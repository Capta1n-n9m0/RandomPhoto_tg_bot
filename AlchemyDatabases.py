from sqlalchemy import create_engine, MetaData, Table, Integer, String, \
    Column, DateTime, ForeignKey, Numeric, BigInteger, Boolean

from datetime import datetime
from sqlalchemy.orm import relationship, declarative_base
import sqlalchemy.orm as sqla_orm
import sqlalchemy as sqla


Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    user_id             = Column(Integer, primary_key=True)
    tg_id               = Column(BigInteger, nullable=True)
    username            = Column(String(32), nullable=True)
    first_name          = Column(String(64), nullable=True)
    last_name           = Column(String(64), nullable=True)
    first_seen_date     = Column(DateTime, nullable=True)
    registration_date   = Column(DateTime, nullable=True)
    last_seen_date      = Column(DateTime, nullable=True)
    is_registered       = Column(Boolean, nullable=True)
    photos              = relationship("Photo")
    storages            = relationship("Storage")

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

class Photo(Base):
    __tablename__ = "photos"
    photo_id            = Column(Integer, primary_key=True)
    filename            = Column(String(40), nullable=False)
    size                = Column(BigInteger, nullable=False)
    hash                = Column(String(64), nullable=True)
    upload_date         = Column(DateTime, nullable=True)
    storage_id          = Column(Integer, ForeignKey("storages.storage_id"))
    user_id             = Column(Integer, ForeignKey("users.user_id"))







