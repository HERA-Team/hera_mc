import os
import sys
from sqlalchemy import Column, ForeignKey, BigInteger, String
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import numpy as np

Base = declarative_base()
test_db = 'postgresql://bryna:bryna@localhost:5432/test'


class HeraObs(Base):
    __tablename__ = 'hera_obs'
    obsid = Column(BigInteger, primary_key=True)
    starttime = Column(DOUBLE_PRECISION, nullable=False)
    stoptime = Column(DOUBLE_PRECISION, nullable=False)
    lststart = Column(DOUBLE_PRECISION, nullable=False)

    def __repr__(self):
        return ("<HeraObs('{self.obsid}', '{self.starttime}', "
                "'{self.stoptime}', '{self.lststart}')>".format(self=self))

    def __eq__(self, other):
        return isinstance(other, HeraObs) and (
            other.obsid == self.obsid and
            np.allclose(other.starttime, self.starttime) and
            np.allclose(other.stoptime, self.stoptime) and
            np.allclose(other.lststart, self.lststart))


class DB():
    engine = None
    DBSession = sessionmaker()

    def __init__(self, db_name=test_db):
        self.engine = create_engine(db_name)
        self.DBSession.configure(bind=self.engine)

    def create_tables(self):
        Base.metadata.create_all(self.engine)

    def drop_tables(self):
        Base.metadata.bind = self.engine
        Base.metadata.drop_all(self.engine)
