# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Common subsystem_error table.

The columns in this module are documented in docs/mc_definition.tex,
the documentation needs to be kept up to date with any changes.
"""
from math import floor
from astropy.time import Time
from sqlalchemy import Column, String, Integer, BigInteger, Text

from . import MCDeclarativeBase


class SubsystemError(MCDeclarativeBase):
    """
    Definition of subsystem_error table.

    Attributes
    ----------
    id : BigInteger Column
        Autoincrementing error id. Primary_key
    time : BigInteger Column
        GPS time of this error, floored.
    subsystem : String Column
        Name of subsystem.
    mc_time : BigInteger Column
        GPS time error was report to M&C, floored.
    severity : Integer Column
        Integer indicating severity level, 1 is most severe.
    log : Text Column
        Error message.

    """

    __tablename__ = "subsystem_error"
    id = Column(BigInteger, primary_key=True, autoincrement=True)  # noqa A003
    time = Column(BigInteger, nullable=False)
    subsystem = Column(String(32), nullable=False)
    mc_time = Column(BigInteger, nullable=False)
    severity = Column(Integer, nullable=False)
    log = Column(Text, nullable=False)

    @classmethod
    def create(cls, db_time, time, subsystem, severity, log):
        """
        Create a new subsystem_error object.

        Parameters
        ----------
        db_time : astropy Time object
            Astropy time object based on a timestamp from the database.
            Usually generated from MCSession.get_current_db_time()
        time : astropy Time object
            Time of this error report.
        subsystem : str
            Name of subsystem with error.
        severity : int
            Integer indicating severity level, 1 is most severe.
        log : str
            error message or log file name (TBD).

        Returns
        -------
        SubsystemError object

        """
        if not isinstance(db_time, Time):
            raise ValueError("db_time must be an astropy Time object")
        mc_time = floor(db_time.gps)

        if not isinstance(time, Time):
            raise ValueError("time must be an astropy Time object")
        time = floor(time.gps)

        return cls(
            time=time, subsystem=subsystem, mc_time=mc_time, severity=severity, log=log
        )
