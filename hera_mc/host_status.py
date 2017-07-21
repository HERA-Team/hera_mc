# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""M&C logging of the uptime, load, etc., on our computers out in the Karoo.

NOTE: this is superseded by the server_status set of tables!

"""

from __future__ import absolute_import, division, print_function

import datetime
import os
import socket
import uptime
import numpy as np

from sqlalchemy import BigInteger, Column, DateTime, Float, String, func

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
        self.uptime = uptime.uptime() / 86400.

    def __repr__(self):
        return('<HostStatus id={self.id} time={self.time} hostname={self.hostname} '
               'load_average={self.load_average} uptime={self.uptime}>').format(self=self)


def plot_host_status_for_plotly(session):
    from plotly import graph_objs as go, plotly as py
    internal_hosts = ['per210-1', 'paper1']
    internal_to_ui = {
        'per210-1': 'qmaster',
    }

    # Fill in arrays from the DB.

    data = []

    for host in internal_hosts:
        times = []
        loads = []

        q = (session.query(HostStatus).
             filter(func.age(HostStatus.time) < '30 day').
             filter(HostStatus.hostname == host).
             order_by(HostStatus.time).
             all())

        for item in q:
            times.append(item.time)
            loads.append(item.load_average)

        data.append(go.Scatter(x=times,
                               y=loads,
                               name=internal_to_ui.get(host, host)))

    # Finish plot

    layout = go.Layout(showlegend=True,
                       title='Karoo host load averages',
                       xaxis={'title': 'Date',
                              },
                       yaxis={'title': '5-minute load average',
                              },
                       )
    fig = go.Figure(data=data,
                    layout=layout,
                    )
    py.plot(fig,
            auto_open=False,
            filename='karoo_host_load_averages',
            )
