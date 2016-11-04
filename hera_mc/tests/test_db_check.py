from sqlalchemy import create_engine, Column, Integer, String
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import ForeignKey

from hera_mc.db_check import is_sane_database
from hera_mc import mc


def setup_module(self):
    # Quiet log output for the tests
    import logging
    from hera_mc import logger
    # logger.setLevel(logging.FATAL)


def gen_test_model():

    Base = declarative_base()

    class SaneTestModel(Base):
        """A sample SQLAlchemy model to demostrate db conflicts. """

        __tablename__ = "sanity_check_test"

        #: Running counter used in foreign key references
        id = Column(Integer, primary_key=True)

    return Base, SaneTestModel


def gen_relation_models():

    Base = declarative_base()

    class RelationTestModel(Base):
        __tablename__ = "sanity_check_test_2"
        id = Column(Integer, primary_key=True)

    class RelationTestModel2(Base):
        __tablename__ = "sanity_check_test_3"
        id = Column(Integer, primary_key=True)

        test_relationship_id = Column(ForeignKey("sanity_check_test_2.id"))
        test_relationship = relationship(RelationTestModel,
                                         primaryjoin=test_relationship_id ==
                                         RelationTestModel.id)

    return Base, RelationTestModel, RelationTestModel2


def gen_declarative():

    Base = declarative_base()

    class DeclarativeTestModel(Base):
        __tablename__ = "sanity_check_test_4"
        id = Column(Integer, primary_key=True)

        @declared_attr
        def _password(self):
            return Column('password', String(256), nullable=False)

        @hybrid_property
        def password(self):
            return self._password

    return Base, DeclarativeTestModel


def test_sanity_pass():
    """
    See database sanity check completes when tables and columns are created.
    """
    engine = mc.connect_to_mc_testing_db().engine
    conn = engine.connect()
    trans = conn.begin()

    Base, SaneTestModel = gen_test_model()
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        Base.metadata.drop_all(engine, tables=[SaneTestModel.__table__])
    except sqlalchemy.exc.NoSuchTableError:
        pass

    Base.metadata.create_all(engine, tables=[SaneTestModel.__table__])

    try:
        assert is_sane_database(Base, session) is True
    finally:
        Base.metadata.drop_all(engine)


def test_sanity_table_missing():
    """See check fails when there is a missing table"""
    engine = mc.connect_to_mc_testing_db().engine
    conn = engine.connect()
    trans = conn.begin()

    Base, SaneTestModel = gen_test_model()
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        Base.metadata.drop_all(engine, tables=[SaneTestModel.__table__])
    except sqlalchemy.exc.NoSuchTableError:
        pass

    assert is_sane_database(Base, session) is False


def test_sanity_column_missing():
    """See check fails when there is a missing table"""
    engine = mc.connect_to_mc_testing_db().engine
    conn = engine.connect()
    trans = conn.begin()

    Session = sessionmaker(bind=engine)
    session = Session()
    Base, SaneTestModel = gen_test_model()
    try:
        Base.metadata.drop_all(engine, tables=[SaneTestModel.__table__])
    except sqlalchemy.exc.NoSuchTableError:
        pass
    Base.metadata.create_all(engine, tables=[SaneTestModel.__table__])

    # Delete one of the columns
    engine.execute("ALTER TABLE sanity_check_test DROP COLUMN id")

    assert is_sane_database(Base, session) is False


def test_sanity_pass_relationship():
    """
    See database sanity check understands about relationships and don't
    deem them as missing column.
    """
    engine = mc.connect_to_mc_testing_db().engine
    conn = engine.connect()
    trans = conn.begin()

    Session = sessionmaker(bind=engine)
    session = Session()

    Base, RelationTestModel, RelationTestModel2 = gen_relation_models()
    try:
        Base.metadata.drop_all(engine, tables=[RelationTestModel.__table__,
                                               RelationTestModel2.__table__])
    except sqlalchemy.exc.NoSuchTableError:
        pass

    Base.metadata.create_all(engine, tables=[RelationTestModel.__table__,
                                             RelationTestModel2.__table__])

    try:
        assert is_sane_database(Base, session) is True
    finally:
        Base.metadata.drop_all(engine)


def test_sanity_pass_declarative():
    """
    See database sanity check understands about relationships and don't deem
    them as missing column.
    """
    engine = mc.connect_to_mc_testing_db().engine
    conn = engine.connect()
    trans = conn.begin()

    Session = sessionmaker(bind=engine)
    session = Session()

    Base, DeclarativeTestModel = gen_declarative()
    try:
        Base.metadata.drop_all(engine, tables=[DeclarativeTestModel.__table__])
    except sqlalchemy.exc.NoSuchTableError:
        pass

    Base.metadata.create_all(engine, tables=[DeclarativeTestModel.__table__])

    try:
        assert is_sane_database(Base, session) is True
    finally:
        Base.metadata.drop_all(engine)
