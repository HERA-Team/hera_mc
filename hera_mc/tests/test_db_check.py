# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD license.

from sqlalchemy import Column, Integer, String
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import ForeignKey

from ..db_check import is_valid_database
from ..db_check import check_connection
from .. import mc


def gen_test_model():

    Base = declarative_base()

    class ValidTestModel(Base):
        """A sample SQLAlchemy model to demostrate db conflicts."""

        __tablename__ = "validity_check_test"

        #: Running counter used in foreign key references
        id_ = Column(Integer, primary_key=True)

    return Base, ValidTestModel


def gen_relation_models():

    Base = declarative_base()

    class RelationTestModel(Base):
        __tablename__ = "validity_check_test_2"
        id_ = Column(Integer, primary_key=True)

    class RelationTestModel2(Base):
        __tablename__ = "validity_check_test_3"
        id_ = Column(Integer, primary_key=True)

        test_relationship_id = Column(ForeignKey("validity_check_test_2.id_"))
        test_relationship = relationship(
            RelationTestModel, primaryjoin=test_relationship_id == RelationTestModel.id_
        )

    return Base, RelationTestModel, RelationTestModel2


def gen_declarative():

    Base = declarative_base()

    class DeclarativeTestModel(Base):
        __tablename__ = "validity_check_test_4"
        id_ = Column(Integer, primary_key=True)

        @declared_attr
        def _password(self):
            return Column("password", String(256), nullable=False)

        @hybrid_property
        def password(self):
            return self._password

    return Base, DeclarativeTestModel


def test_argparser():
    ap = mc.get_mc_argument_parser()
    assert ap.description is None


def test_validity_pass():
    """
    See database validity check completes when tables and columns are created.
    """
    engine = mc.connect_to_mc_testing_db().engine
    conn = engine.connect()
    conn.begin()

    Base, ValidTestModel = gen_test_model()
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        Base.metadata.drop_all(engine, tables=[ValidTestModel.__table__])
    except sqlalchemy.exc.NoSuchTableError:
        pass

    base_is_none = is_valid_database(None, session)
    assert base_is_none

    Base.metadata.create_all(engine, tables=[ValidTestModel.__table__])

    try:
        assert is_valid_database(Base, session) is True
    finally:
        Base.metadata.drop_all(engine)


def test_validity_table_missing():
    """See check fails when there is a missing table"""
    engine = mc.connect_to_mc_testing_db().engine
    conn = engine.connect()
    conn.begin()

    Base, ValidTestModel = gen_test_model()
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        Base.metadata.drop_all(engine, tables=[ValidTestModel.__table__])
    except sqlalchemy.exc.NoSuchTableError:
        pass

    assert is_valid_database(Base, session) is False


def test_validity_column_missing():
    """See check fails when there is a missing table"""
    engine = mc.connect_to_mc_testing_db().engine
    conn = engine.connect()
    conn.begin()

    Session = sessionmaker(bind=engine)
    session = Session()
    Base, ValidTestModel = gen_test_model()
    try:
        Base.metadata.drop_all(engine, tables=[ValidTestModel.__table__])
    except sqlalchemy.exc.NoSuchTableError:
        pass
    Base.metadata.create_all(engine, tables=[ValidTestModel.__table__])

    # Delete one of the columns
    engine.execute("ALTER TABLE validity_check_test DROP COLUMN id_")

    assert is_valid_database(Base, session) is False


def test_validity_pass_relationship():
    """
    See database validity check understands about relationships and don't
    deem them as missing column.
    """
    engine = mc.connect_to_mc_testing_db().engine
    conn = engine.connect()
    conn.begin()

    Session = sessionmaker(bind=engine)
    session = Session()

    Base, RelationTestModel, RelationTestModel2 = gen_relation_models()
    try:
        Base.metadata.drop_all(
            engine, tables=[RelationTestModel.__table__, RelationTestModel2.__table__]
        )
    except sqlalchemy.exc.NoSuchTableError:
        pass

    Base.metadata.create_all(
        engine, tables=[RelationTestModel.__table__, RelationTestModel2.__table__]
    )

    try:
        assert is_valid_database(Base, session) is True
    finally:
        Base.metadata.drop_all(engine)


def test_validity_pass_declarative():
    """
    See database validity check understands about relationships and don't deem
    them as missing column.
    """
    engine = mc.connect_to_mc_testing_db().engine
    conn = engine.connect()
    conn.begin()

    Session = sessionmaker(bind=engine)
    session = Session()

    Base, DeclarativeTestModel = gen_declarative()
    try:
        Base.metadata.drop_all(engine, tables=[DeclarativeTestModel.__table__])
    except sqlalchemy.exc.NoSuchTableError:
        pass

    Base.metadata.create_all(engine, tables=[DeclarativeTestModel.__table__])

    try:
        assert is_valid_database(Base, session) is True
    finally:
        Base.metadata.drop_all(engine)


def test_check_connection():
    """Check that a missing database raises appropriate exception."""
    # Create database connection with fake url
    db = mc.DeclarativeDB("postgresql://hera@localhost/foo")
    with db.sessionmaker() as s:
        assert check_connection(s) is False
