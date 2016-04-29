from sqlalchemy import (
    create_engine, Column, BigInteger, DateTime, String, Boolean
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Link(Base):

    __tablename__ = 'link'

    amazon = Column(BigInteger, primary_key=True)
    ebay = Column(BigInteger, primary_key=True)
    date = Column(DateTime, default=func.now())

    def __repr__(self):
        return '<Link ({}, {})>'.format(self.amazon, self.ebay)


class UPC(Base):

    __tablename__ = 'upc'

    upc = Column(String(12), primary_key=True)
    available = Column(Boolean, default=True)

    @classmethod
    def random(cls, session):
        available = session.query(cls).filter_by(available=True)
        upc = available.order_by(func.random()).first()
        if not upc:
            raise('Please add new UPCs to the database!')

    def __repr__(self):
        return '<UPC {}>'.format(self.upc)


engine = create_engine('sqlite:///sqlite3.db')
Base.metadata.create_all(engine)
