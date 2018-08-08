# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Common subsystem_error table

The columns in this module are documented in docs/mc_definition.tex,
the documentation needs to be kept up to date with any changes.
"""
from __future__ import absolute_import, division, print_function

from math import floor
from astropy.time import Time
from sqlalchemy import Column, String, Integer, BigInteger, Text

from . import MCDeclarativeBase


class SubsystemError(MCDeclarativeBase):
    """
    Definition of subsystem_error table.

    id: autoincrementing error id (BigInteger). Primary_key
    time: time of error in floor(gps seconds) (BigInteger)
    subsystem: name of subsystem (String)
    mc_time: time error was report to M&C in floor(gps seconds) (BigInteger)
    severity: integer indicating severity level, 1 is most severe (Integer)
    log: error message (Text)
    """
    __tablename__ = 'subsystem_error'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    time = Column(BigInteger, nullable=False)
    subsystem = Column(String(32), nullable=False)
    mc_time = Column(BigInteger, nullable=False)
    severity = Column(Integer, nullable=False)
    log = Column(Text, nullable=False)

    @classmethod
    def create(cls, db_time, time, subsystem, severity, log):
        """
        Create a new subsystem_error object.

        Parameters:
        ------------
        db_time: astropy time object
            astropy time object based on a timestamp from the database.
            Usually generated from MCSession.get_current_db_time()
        time: astropy time object
            time of this error report
        subsystem: string
            name of subsystem with error
        severity: integer
            integer indicating severity level, 1 is most severe
        log: string
            error message or log file name (TBD)
        """
        if not isinstance(db_time, Time):
            raise ValueError('db_time must be an astropy Time object')
        mc_time = floor(db_time.gps)

        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        time = floor(time.gps)

        return cls(time=time, subsystem=subsystem, mc_time=mc_time,
                   severity=severity, log=log)
