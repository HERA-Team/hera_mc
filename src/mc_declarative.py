import os
import sys
from sqlalchemy import Column, ForeignKey, BigInteger, String
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()


class HeraObs(Base):
    __tablename__ = 'hera_obs'
    obsid = Coumn(BigInteger, primary key=True)
    starttime = Coumn(DOUBLE_PRECISION, nullable=False)
    stoptime = Coumn(DOUBLE_PRECISION, nullable=False)
    lststart = Coumn(DOUBLE_PRECISION, nullable=False)

engine = create_engine('postgresql://bryna:bryna@localhost:5432/bryna')
Base.metadata.create_all(engine)
