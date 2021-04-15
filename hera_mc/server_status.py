# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Common server_status table.

The columns in this module are documented in docs/mc_definition.tex,
the documentation needs to be kept up to date with any changes.
"""
from math import floor
from astropy.time import Time
from sqlalchemy import Column, Integer, String, Float, BigInteger

from . import MCDeclarativeBase, DEFAULT_GPS_TOL, DEFAULT_DAY_TOL


class ServerStatus(MCDeclarativeBase):
    """
    Definition of server_status table.

    Attributes
    ----------
    hostname : String Column
        Name of server. Part of the primary key.
    mc_time : BigInteger Column
        GPS time report received by M&C, floored. Part of the primary key.
    ip_address : String Column
        IP address of server.
    mc_system_timediff : Float Column
        Difference between M&C time and time report sent by server in seconds.
    num_cores : Integer Column
        Number of cores on server.
    cpu_load_pct : Float Column
        CPU load percent = total load / num_cores, 5 min average.
    uptime_days : Float Column
        Server uptime in decimal days.
    memory_used_pct : Float Column
        Percent of memory used, 5 min average.
    memory_size_gb : Float Column
        Amount of memory on server in GB .
    disk_space_pct : Float Column
        Percent of disk used.
    disk_size_gb : Float Column
        Amount of disk space on server in GB.
    network_bandwidth_mbs : Float Column
        Network bandwidth in MB/s, 5 min average. Can be null if not applicable.

    """

    __abstract__ = True
    hostname = Column(String(32), primary_key=True)
    mc_time = Column(BigInteger, primary_key=True)
    ip_address = Column(String(32), nullable=False)
    mc_system_timediff = Column(Float, nullable=False)
    num_cores = Column(Integer, nullable=False)
    cpu_load_pct = Column(Float, nullable=False)
    uptime_days = Column(Float, nullable=False)
    memory_used_pct = Column(Float, nullable=False)
    memory_size_gb = Column(Float, nullable=False)
    disk_space_pct = Column(Float, nullable=False)
    disk_size_gb = Column(Float, nullable=False)
    network_bandwidth_mbs = Column(Float)

    tols = {'mc_system_timediff': DEFAULT_GPS_TOL,
            'uptime_days': DEFAULT_DAY_TOL}

    @classmethod
    def create(cls, db_time, hostname, ip_address, system_time, num_cores,
               cpu_load_pct, uptime_days, memory_used_pct, memory_size_gb,
               disk_space_pct, disk_size_gb, network_bandwidth_mbs=None):
        """
        Create a new server_status object.

        Parameters
        ----------
        db_time : astropy Time object
            Astropy time object based on a timestamp from the database.
            Usually generated from MCSession.get_current_db_time()
        hostname : str
            Name of server.
        ip_address : str
            IP address of server
        system_time : astropy Time object
            Time report sent by server.
        num_cores : int
            Number of cores on server.
        cpu_load_pct : float
            CPU load percent = total load / num_cores, 5 min average.
        uptime_days : float
            Server uptime in decimal days.
        memory_used_pct : float
            Percent of memory used, 5 min average.
        memory_size_gb : float
            Amount of memory on server in GB.
        disk_space_pct : float
            Percent of disk used.
        disk_size_gb : float
            Amount of disk space on server in GB.
        network_bandwidth_mbs : float
            Network bandwidth in MB/s, 5 min average. Can be null if not
            applicable.

        """
        if not isinstance(db_time, Time):
            raise ValueError('db_time must be an astropy Time object')
        mc_time = floor(db_time.gps)

        if not isinstance(system_time, Time):
            raise ValueError('system_time must be an astropy Time object')
        mc_system_timediff = db_time.gps - system_time.gps

        return cls(hostname=hostname, mc_time=mc_time, ip_address=ip_address,
                   mc_system_timediff=mc_system_timediff, num_cores=num_cores,
                   cpu_load_pct=cpu_load_pct, uptime_days=uptime_days,
                   memory_used_pct=memory_used_pct, memory_size_gb=memory_size_gb,
                   disk_space_pct=disk_space_pct, disk_size_gb=disk_size_gb,
                   network_bandwidth_mbs=network_bandwidth_mbs)


def plot_host_status_for_plotly(session):
    """
    Plot host status using plotly.

    Parameters
    ----------
    session : MCSession object
        MCSession object to get data from database with.

    """
    from astropy.time import Time
    from plotly import graph_objects as go

    from chart_studio import plotly as chart_plotly

    thirty_days = 24 * 3600 * 30
    gps_time_cutoff = Time.now().gps - thirty_days
    plot_items = []

    # Gather data about Librarian servers

    from .librarian import LibServerStatus

    librarian_hosts_of_interest = [
        'qmaster',
        # 'pot1',
        # 'pot6.karoo.kat.ac.za',
        'pot7.still.pvt',
        'pot8.still.pvt',
    ]

    internal_hostname_to_ui_hostname = {
        'pot7.still.pvt': 'pot7',
        'pot8.still.pvt': 'pot8',
    }

    for host in librarian_hosts_of_interest:
        times = []
        loads = []

        q = (session.query(LibServerStatus)
             .filter(LibServerStatus.mc_time > gps_time_cutoff)
             .filter(LibServerStatus.hostname == host)
             .order_by(LibServerStatus.mc_time)
             .all())

        for item in q:
            times.append(Time(item.mc_time, format='gps').datetime)
            loads.append(item.cpu_load_pct)

        ui_hostname = internal_hostname_to_ui_hostname.get(host, host)

        plot_items.append(go.Scatter(
            x=times,
            y=loads,
            name=ui_hostname,
        ))

    # Finish plot

    layout = go.Layout(
        showlegend=True,
        title='Host load averages',
        xaxis={
            'title': 'Date',
        },
        yaxis={
            'title': '5-minute load average (percent per CPU)',
        },
    )

    fig = go.Figure(
        data=plot_items,
        layout=layout,
    )

    chart_plotly.plot(
        fig,
        auto_open=False,
        filename='karoo_host_load_averages',
    )
