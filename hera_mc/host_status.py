# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""M&C logging of the uptime, load, etc., on our computers out in the Karoo.

"""

from __future__ import absolute_import, division, print_function

import datetime
import os
import socket

import numpy as np

from sqlalchemy import BigInteger, Column, DateTime, Float, String

from . import MCDeclarativeBase, NotNull


class HostStatus(MCDeclarativeBase):
    """A table logging the status of HERA computers.

    """
    __tablename__ = 'host_status'

    id = Column(BigInteger, primary_key=True)
    "A unique ID number for each record; no intrinsic meaning."

    time = NotNull(DateTime)
    "The time when the information was generated; stored as SqlAlchemy UTC DateTime."

    hostname = Column(String(64))
    "The hostname of the computer that this record pertains to."

    load_average = NotNull(Float)
    "The CPU load average on this host, averaged over the past 5 minutes."

    uptime = NotNull(Float)
    "How long this host has been running since it booted; measured in days."


    def __init__(self):
        """Create a new record, gathering information relevant to the machine on which
        this code is running.

        """
        self.time = datetime.datetime.utcnow()
        self.hostname = socket.gethostname()
        self.load_average = os.getloadavg()[1]

        with open ('/proc/uptime', 'r') as f:
            self.uptime = float (f.readline ().split ()[0]) / 86400.


    def __repr__(self):
        return ('<HostStatus id={self.id} time={self.time} hostname={self.hostname} '
                'load_average={self.load_average} uptime={self.uptime}>').format (self=self)
