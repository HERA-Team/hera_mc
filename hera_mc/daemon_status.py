# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
M&C daemon_status table.

The columns in this module are documented in docs/mc_definition.tex,
the documentation needs to be kept up to date with any changes.
"""

from math import floor
from astropy.time import Time
from sqlalchemy import Column, String, BigInteger

from . import MCDeclarativeBase


status_list = ["good", "errored"]


class DaemonStatus(MCDeclarativeBase):
    """
    Definition of daemon_status table.

    Attributes
    ----------
    name : String Column
        Name of daemon. Part of the primary key.
    hostname : String Column
        Hostname where daemon is running. Part of the primary key.
    jd : BigInteger Column
        Julian date of the status. Part of the primary key.
    time : BigInteger Column
        GPS time of latest update, floored.
    status : String Column
        Status, one of the values in status_list.

    """

    __tablename__ = "daemon_status"
    name = Column(String(32), primary_key=True)
    hostname = Column(String(32), primary_key=True)
    jd = Column(BigInteger, primary_key=True)
    time = Column(BigInteger, nullable=False)
    status = Column(String(32), nullable=False)

    @classmethod
    def create(cls, name, hostname, time, status):
        """
        Create a new daemon_status object.

        Parameters
        ----------
        name : str
            Name of the daemon
        hostname : str
            Name of server where daemon is running
        time : astropy time object
            Time of this status report, updated on every iteration of the daemon
        status : str
            Status, one of the values in status_list.

        """
        if not isinstance(time, Time):
            raise ValueError("time must be an astropy Time object")
        jd = floor(time.jd)
        time = floor(time.gps)

        if status not in status_list:
            raise ValueError(
                "Status must be one of: [{statlist}]".format(
                    statlist=", ".join(status_list)
                )
            )

        return cls(name=name, hostname=hostname, jd=jd, time=time, status=status)
