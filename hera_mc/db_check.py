# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.
"""Database consistency checking functions."""

from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError

from . import logger


def check_connection(session):
    """
    Check whether the database connection is live and responsive.

    Parameters
    ----------
    session : SQLAlchemy session
        Session to use to check the connection, bound to an engine.

    Returns
    -------
    True if database responds to simple SQL query. Otherwise False.

    """
    result = True
    try:
        session.execute("SELECT 1")
    except OperationalError:
        result = False
    return result


def is_valid_database(base, session):
    """
    Check that the current database matches the models declared in model base.

    Currently we check that all tables exist with all columns.

    What is not checked:

    * Column types are not verified
    * Relationships are not verified (TODO)

    Parameters
    ----------
    base : Declarative Base
        Instance of SQLAlchemy Declarative Base to check.
    session : SQLAlchemy session
        Session to use, bound to an engine.

    Returns
    -------
    True if all declared models have corresponding tables and columns.

    """
    if base is None:
        from . import MCDeclarativeBase

        base = MCDeclarativeBase

    engine = session.get_bind()
    try:  # This tries thrice with 5sec sleeps in between
        iengine = inspect(engine)
    except OperationalError:  # pragma: no cover
        import time

        time.sleep(5)
        try:
            iengine = inspect(engine)
        except OperationalError:
            time.sleep(5)
            iengine = inspect(engine)

    errors = False

    tables = iengine.get_table_names()

    # Go through all SQLAlchemy models

    for table, klass in base.metadata.tables.items():

        if table in tables:
            # Check all columns are found
            # Looks like [{'default':
            #               "nextval('validity_check_test_id_seq'::regclass)",
            #              'autoincrement': True, 'nullable': False,
            #              'type': INTEGER(), 'name': 'id'}]

            columns = [c["name"] for c in iengine.get_columns(table)]
            mapper = inspect(klass)

            for column in mapper.columns:
                # Assume normal flat column
                if column.key not in columns:
                    logger.error(
                        f"Model {klass} declares column {column.key} which does not "
                        "exist in database {engine}"
                    )
                    errors = True
            # TODO: Add validity checks for relations
        else:
            logger.error(
                "Model %s declares table %s which does not exist " "in database %s",
                klass,
                table,
                engine,
            )
            errors = True

    return not errors
