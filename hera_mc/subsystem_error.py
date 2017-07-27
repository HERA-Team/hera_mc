# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Common subsystem_error table

The columns in this module are documented in docs/mc_definition.tex,
the documentation needs to be kept up to date with any changes.
"""
from math import floor
from astropy.time import Time
from sqlalchemy import Column, String, BigInteger, Text
from . import MCDeclarativeBase


class SubsystemError(MCDeclarativeBase):
    """
    Definition of subsystem_error table.

    subsystem: name of subsystem (String). Part of primary_key
    time: time of error in floor(gps seconds) (BigInteger). Part of primary_key
    log: error message (Text)
    """
    __tablename__ = 'subsystem_error'
    subsystem = Column(String(32), primary_key=True)
    time = Column(BigInteger, primary_key=True)
    log = Column(Text, nullable=False)

    @classmethod
    def create(cls, subsystem, time, log):
        """
        Create a new server_status object.

        Parameters:
        ------------
        subsystem: string
            name of subsystem (e.g. 'librarian', 'rtp')
        time: astropy time object
            time of this error report
        log: string
            error message or log file name (TBD)
        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        time = floor(time.gps)

        return cls(subsystem=subsystem, time=time, log=log)
