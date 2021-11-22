# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Librarian tables.

The columns in this module are documented in docs/mc_definition.tex,
the documentation needs to be kept up to date with any changes.
"""

from math import floor
from astropy.time import Time
from sqlalchemy import Column, ForeignKey, Integer, BigInteger, String, Text, Float

from . import MCDeclarativeBase, DEFAULT_MIN_TOL
from .server_status import ServerStatus


class LibServerStatus(ServerStatus):
    """
    Librarian version of the ServerStatus object.

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

    __tablename__ = "lib_server_status"


class LibStatus(MCDeclarativeBase):
    """
    Definition of lib_status table.

    Attributes
    ----------
    time : BigInteger Column
        GPS time of this status, floored. Part of the primary key.
    num_files : BigInteger Column
        Number of files in librarian.
    data_volume_gb : Float Column
        Data volume in GB.
    free_space_gb : Float Column
        Free space in GB.
    upload_min_elapsed : Float Column
        Minutes elapsed since last file upload.
    num_processes : Integer Column
        Number of background tasks running.
    git_version : String Column
        Librarian git version.
    git_hash : String Column
        Librarian git hash.

    """

    __tablename__ = "lib_status"
    time = Column(BigInteger, primary_key=True, autoincrement=False)
    num_files = Column(BigInteger, nullable=False)
    data_volume_gb = Column(Float, nullable=False)
    free_space_gb = Column(Float, nullable=False)
    upload_min_elapsed = Column(Float, nullable=False)
    num_processes = Column(Integer, nullable=False)
    git_version = Column(String(32), nullable=False)
    git_hash = Column(String(64), nullable=False)

    tols = {
        "data_volume_gb": {"atol": 1e-3, "rtol": 0},
        "free_space_gb": {"atol": 1e-3, "rtol": 0},
        "upload_min_elapsed": DEFAULT_MIN_TOL,
    }

    @classmethod
    def create(
        cls,
        time,
        num_files,
        data_volume_gb,
        free_space_gb,
        upload_min_elapsed,
        num_processes,
        git_version,
        git_hash,
    ):
        """
        Create a new lib_status object.

        Parameters
        ----------
        time : astropy Time object
            Time of this status.
        num_files : int
            Number of files in librarian.
        data_volume_gb : float
            Data volume in GB.
        free_space_gb : float
            Free space in GB.
        upload_min_elapsed: float
            Minutes since last file upload.
        num_processes : int
            Number of background tasks running.
        git_version : str
            Librarian git version.
        git_hash : str
            Librarian git hash.

        Returns
        -------
        LibStatus object

        """
        if not isinstance(time, Time):
            raise ValueError("time must be an astropy Time object")
        time = floor(time.gps)

        return cls(
            time=time,
            num_files=num_files,
            data_volume_gb=data_volume_gb,
            free_space_gb=free_space_gb,
            upload_min_elapsed=upload_min_elapsed,
            num_processes=num_processes,
            git_version=git_version,
            git_hash=git_hash,
        )


class LibRAIDStatus(MCDeclarativeBase):
    """
    Definition of lib_raid_status table.

    Attributes
    ----------
    time : BigInteger Column
        GPS time of this status, floored. Part of the primary key.
    hostname : String Column
        Name of RAID server (String). Part of the primary key.
    num_disks : Integer Column
        Number of disks in RAID server.
    info : Text Column
        TBD info from megaraid controller (may become several columns).

    """

    __tablename__ = "lib_raid_status"
    time = Column(BigInteger, primary_key=True)
    hostname = Column(String(32), primary_key=True)
    num_disks = Column(Integer, nullable=False)
    info = Column(Text, nullable=False)

    @classmethod
    def create(cls, time, hostname, num_disks, info):
        """
        Create a new lib_raid_status object.

        Parameters
        ----------
        time : astropy Time object
            Time of this status.
        hostname : str
            Name of RAID server.
        num_disks : int
            Number of disks in RAID server.
        info : str
            TBD info from megaraid controller.

        Returns
        -------
        LibRAIDStatus object

        """
        if not isinstance(time, Time):
            raise ValueError("time must be an astropy Time object")
        time = floor(time.gps)

        return cls(time=time, hostname=hostname, num_disks=num_disks, info=info)


class LibRAIDErrors(MCDeclarativeBase):
    """
    Definition of lib_raid_errors table.

    Attributes
    ----------
    id : BigInteger Column
        autoincrementing error id. The Primary key.
    time : BigInteger Column
        GPS time of this status, floored.
    hostname : String Column
        Name of RAID server with error.
    disk : String Column
        Name of disk with error.
    log : Text Column
        Error message or log file name (TBD).

    """

    __tablename__ = "lib_raid_errors"
    id = Column(BigInteger, primary_key=True, autoincrement=True)  # noqa A003
    time = Column(BigInteger, nullable=False)
    hostname = Column(String(32), nullable=False)
    disk = Column(String, nullable=False)
    log = Column(Text, nullable=False)

    @classmethod
    def create(cls, time, hostname, disk, log):
        """
        Create a new lib_raid_error object.

        Parameters
        ----------
        time : astropy Time object
            Time of this error report.
        hostname : str
            Name of RAID server with error.
        disk : str
            Name of disk with error.
        log : str
            Error message or log file name (TBD).

        Returns
        -------
        LibRAIDErrors object

        """
        if not isinstance(time, Time):
            raise ValueError("time must be an astropy Time object")
        time = floor(time.gps)

        return cls(time=time, hostname=hostname, disk=disk, log=log)


class LibRemoteStatus(MCDeclarativeBase):
    """
    Definition of lib_remote_status table.

    Attributes
    ----------
    time : BigInteger Column
        GPS time of this status, floored. Part of the primary key.
    remote_name : String Column
        Name of remote librarian. Part of the primary key.
    ping_time : Float Column
        Ping time in seconds.
    num_file_uploads : Integer Column
        Number of file uploads to remote in last 15 minutes.
    bandwidth_mbs : Float Column
        Bandwidth to remote in Mb/s, 15 minute average.

    """

    __tablename__ = "lib_remote_status"
    time = Column(BigInteger, primary_key=True)
    remote_name = Column(String(32), primary_key=True)
    ping_time = Column(Float, primary_key=True)
    num_file_uploads = Column(Integer, nullable=False)
    bandwidth_mbs = Column(Float, nullable=False)

    @classmethod
    def create(cls, time, remote_name, ping_time, num_file_uploads, bandwidth_mbs):
        """
        Create a new lib_remote_status object.

        Parameters
        ----------
        time : astropy Time object
            Time of this status.
        remote_name : str
            Name of remote server.
        ping_time : float
            Ping time to remote in seconds.
        num_file_uploads : int
            Number of file uploads to remote in last 15 minutes.
        bandwidth_mbs: float
            Bandwidth to remote in Mb/s, 15 minute average.

        Returns
        -------
        LibRemoteStatus object

        """
        if not isinstance(time, Time):
            raise ValueError("time must be an astropy Time object")
        time = floor(time.gps)

        return cls(
            time=time,
            remote_name=remote_name,
            ping_time=ping_time,
            num_file_uploads=num_file_uploads,
            bandwidth_mbs=bandwidth_mbs,
        )


class LibFiles(MCDeclarativeBase):
    """
    Definition of lib_files table.

    Attributes
    ----------
    filename : String Column
        name of file created. The primary key.
    obsid : BigInteger Column
        Observation obsid (Long). Foreign key into Observation table.
        Null values allowed for maintenance files not associated with
        particular observations.
    time : BigInteger Column
        GPS time this file was created, floored.
    size_gb : Float Column
        File size in gb.

    """

    __tablename__ = "lib_files"
    filename = Column(String(256), primary_key=True)
    obsid = Column(BigInteger, ForeignKey("hera_obs.obsid"), nullable=True)
    time = Column(BigInteger, nullable=False)
    size_gb = Column(Float, nullable=False)

    @classmethod
    def create(cls, filename, obsid, time, size_gb):
        """
        Create a new lib_file object.

        Parameters
        ----------
        filename : str
            Name of file created.
        obsid : long or None
            Observation obsid (Foreign key into Observation), or None if
            this file is a maintenance file not associated with a
            particular observation.
        time : astropy Time object
            Time file was created.
        size_gb : float
            File size in GB.

        Returns
        -------
        LibFiles object

        """
        if not isinstance(time, Time):
            raise ValueError("time must be an astropy Time object")
        time = floor(time.gps)

        return cls(filename=filename, obsid=obsid, time=time, size_gb=size_gb)
