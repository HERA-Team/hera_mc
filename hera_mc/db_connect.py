from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine

default_db = 'postgresql://bryna:bryna@localhost:5432/hera_mc'


class DB():
    engine = None
    Base = automap_base()
    DBSession = sessionmaker()

    def __init__(self, db_name=default_db):
        self.engine = create_engine(db_name)
        self.Base.prepare(self.engine, reflect=True)
        self.DBSession.configure(bind=self.engine)
