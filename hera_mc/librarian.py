# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Librarian tables

The columns in this module are documented in docs/mc_definition.tex,
the documentation needs to be kept up to date with any changes.
"""
from math import floor
from astropy.time import Time
from sqlalchemy import Column, ForeignKey, Integer, BigInteger, String, Text, Float
from . import MCDeclarativeBase, DEFAULT_MIN_TOL
from .server_status import ServerStatus


class LibServerStatus(ServerStatus):
    __tablename__ = 'lib_server_status'


class LibStatus(MCDeclarativeBase):
    """
    Definition of lib_status table.

    time: time of this status in floor(gps seconds) (BigInteger). Primary_key
    num_files: number of files in librarian (BigInteger)
    data_volume_gb: data volume in GB (Float)
    free_space_gb: free space in GB (Float)
    upload_min_elapsed: minutes elapsed since last file upload (Float)
    num_processes: number of background tasks running (Integer)
    git_version: librarian git version (String)
    git_hash: librarian git hash (String)
    """
    __tablename__ = 'lib_status'
    time = Column(BigInteger, primary_key=True)
    num_files = Column(BigInteger, nullable=False)
    data_volume_gb = Column(Float, nullable=False)
    free_space_gb = Column(Float, nullable=False)
    upload_min_elapsed = Column(Float, nullable=False)
    num_processes = Column(Integer, nullable=False)
    git_version = Column(String(32), nullable=False)
    git_hash = Column(String(64), nullable=False)

    tols = {'data_volume_gb': {'atol': 1e-3, 'rtol': 0},
            'free_space_gb': {'atol': 1e-3, 'rtol': 0},
            'upload_min_elapsed': DEFAULT_MIN_TOL}

    @classmethod
    def create(cls, time, num_files, data_volume_gb, free_space_gb,
               upload_min_elapsed, num_processes, git_version, git_hash):
        """
        Create a new lib_status object.

        Parameters:
        ------------
        time: astropy time object
            time of this status
        num_files: integer
            number of files in librarian
        data_volume_gb: float
            data volume in GB
        free_space_gb: float
            free space in GB
        upload_min_elapsed: float
            minutes since last file upload
        num_processes: integer
            number of background tasks running
        git_version: string
            Librarian git version
        git_hash: string
            Librarian git hash
        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        time = floor(time.gps)

        return cls(time=time, num_files=num_files, data_volume_gb=data_volume_gb,
                   free_space_gb=free_space_gb, upload_min_elapsed=upload_min_elapsed,
                   num_processes=num_processes, git_version=git_version,
                   git_hash=git_hash)


class LibRAIDStatus(MCDeclarativeBase):
    """
    Definition of lib_raid_status table.

    time: time of this status in floor(gps seconds) (BigInteger). Part of primary_key
    hostname: name of RAID server (String). Part of primary_key
    num_disks: number of disks in RAID server (Integer)
    info: TBD info from megaraid controller (may become several columns) (Text)
    """
    __tablename__ = 'lib_raid_status'
    time = Column(BigInteger, primary_key=True)
    hostname = Column(String(32), primary_key=True)
    num_disks = Column(Integer, nullable=False)
    info = Column(Text, nullable=False)

    @classmethod
    def create(cls, time, hostname, num_disks, info):
        """
        Create a new lib_raid_status object.

        Parameters:
        ------------
        time: astropy time object
            time of this status
        hostname: string
            name of RAID server
        num_disks: integer
            number of disks in RAID server
        info: string
            TBD info from megaraid controller
        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        time = floor(time.gps)

        return cls(time=time, hostname=hostname, num_disks=num_disks, info=info)


class LibRAIDErrors(MCDeclarativeBase):
    """
    Definition of lib_raid_errors table.

    time: time of this status in floor(gps seconds) (BigInteger). Part of primary_key
    hostname: name of RAID server with error (String). Part of primary_key
    disk: name of disk with error (String). Part of primary_key
    log: error message or log file name (TBD) (Text)
    """
    __tablename__ = 'lib_raid_errors'
    time = Column(BigInteger, primary_key=True)
    hostname = Column(String(32), primary_key=True)
    disk = Column(String, primary_key=True)
    log = Column(Text, nullable=False)

    @classmethod
    def create(cls, time, hostname, disk, log):
        """
        Create a new lib_raid_error object.

        Parameters:
        ------------
        time: astropy time object
            time of this error report
        hostname: string
            name of RAID server with error
        disk: string
            name of disk with error
        log: string
            error message or log file name (TBD)
        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        time = floor(time.gps)

        return cls(time=time, hostname=hostname, disk=disk, log=log)


class LibRemoteStatus(MCDeclarativeBase):
    """
    Definition of lib_remote_status table.

    time: time of this status in floor(gps seconds) (BigInteger). Part of primary_key
    remote_name: name of remote librarian (String). Part of primary_key
    ping_time: ping time in seconds (Float)
    num_file_uploads: number of file uploads to remote in last 15 minutes (Integer)
    bandwidth_mbs: bandwidth to remote in Mb/s, 15 minute average
    """
    __tablename__ = 'lib_remote_status'
    time = Column(BigInteger, primary_key=True)
    remote_name = Column(String(32), primary_key=True)
    ping_time = Column(Float, primary_key=True)
    num_file_uploads = Column(Integer, nullable=False)
    bandwidth_mbs = Column(Float, nullable=False)

    @classmethod
    def create(cls, time, remote_name, ping_time, num_file_uploads, bandwidth_mbs):
        """
        Create a new lib_remote_status object.

        Parameters:
        ------------
        time: astropy time object
            time of this status
        remote_name: string
            name of remote server
        ping_time: float
            ping time to remote in seconds
        num_file_uploads: integer
            number of file uploads to remote in last 15 minutes
        bandwidth_mbs: float
            bandwidth to remote in Mb/s, 15 minute average
        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        time = floor(time.gps)

        return cls(time=time, remote_name=remote_name, ping_time=ping_time,
                   num_file_uploads=num_file_uploads, bandwidth_mbs=bandwidth_mbs)


class LibFiles(MCDeclarativeBase):
    """
    Definition of lib_files table.

    filename: name of file created (String). Primary_key
    obsid: observation obsid (Long). Foreign key into Observation table
    time: time this file was created in floor(gps seconds) (BigInteger)
    size_gb: file size in gb (Float)
    """
    __tablename__ = 'lib_files'
    filename = Column(String(32), primary_key=True)
    obsid = Column(BigInteger, ForeignKey('hera_obs.obsid'), nullable=False)
    time = Column(BigInteger, nullable=False)
    size_gb = Column(Float, nullable=False)

    @classmethod
    def create(cls, filename, obsid, time, size_gb):
        """
        Create a new lib_file object.

        Parameters:
        ------------
        filename: string
            name of file created
        obsid: long
            observation obsid (Foreign key into Observation)
        time: astropy time object
            time file was created
        size_gb: float
            file size in GB
        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        time = floor(time.gps)

        return cls(filename=filename, obsid=obsid, time=time, size_gb=size_gb)
