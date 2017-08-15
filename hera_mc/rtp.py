# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
RTP tables

The columns in this module are documented in docs/mc_definition.tex,
the documentation needs to be kept up to date with any changes.
"""

from math import floor
from astropy.time import Time
from sqlalchemy import Column, ForeignKey, Integer, BigInteger, String, Text, Float, Enum
from . import MCDeclarativeBase, DEFAULT_MIN_TOL, DEFAULT_HOUR_TOL
from .server_status import ServerStatus

rtp_process_enum = ['queued', 'started', 'finished', 'error']


class RTPServerStatus(ServerStatus):
    __tablename__ = 'rtp_server_status'


class RTPStatus(MCDeclarativeBase):
    """
    Definition of rtp_status table.

    time: time of this status in floor(gps seconds) (BigInteger). Primary_key
    hostname: hostname of server (String)
    status: status (options TBD) (String)
    event_min_elapsed: minutes elapsed since last event (Float)
    num_processes: number of processes running (Integer)
    restart_hours_elapsed: hours elapsed since last restart (Float)
    """
    __tablename__ = 'rtp_status'
    time = Column(BigInteger, primary_key=True, autoincrement=False)
    hostname = Column(String(32), primary_key=True)
    status = Column(String(64), nullable=False)  # should this be an enum? or text?
    event_min_elapsed = Column(Float, nullable=False)
    num_processes = Column(Integer, nullable=False)
    restart_hours_elapsed = Column(Float, nullable=False)

    tols = {'event_min_elapsed': DEFAULT_MIN_TOL,
            'restart_hours_elapsed': DEFAULT_HOUR_TOL}

    @classmethod
    def create(cls, time, hostname, status, event_min_elapsed, num_processes,
               restart_hours_elapsed):
        """
        Create a new rtp_status object.

        Parameters:
        ------------
        time: astropy time object
            time of this status
        hostname: string
            name of server
        status: string
            status (options TBD)
        event_min_elapsed: float
            minutes since last event
        num_processes: integer
            number of processes running
        restart_hours_elapsed: float
            hours since last restart
        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        time = floor(time.gps)

        return cls(time=time, hostname=hostname, status=status,
                   event_min_elapsed=event_min_elapsed,
                   num_processes=num_processes,
                   restart_hours_elapsed=restart_hours_elapsed)


class RTPProcessEvent(MCDeclarativeBase):
    """
    Definition of rtp_process_event table.

    time: time of this status in floor(gps seconds) (BigInteger). Part of primary_key.
    obsid: observation obsid (BigInteger).  Part of primary_key. Foreign key into Observation table
    event: one of ["queued", "started", "finished", "error"] (rtp_process_enum)
    """
    __tablename__ = 'rtp_process_event'
    time = Column(BigInteger, primary_key=True)
    obsid = Column(BigInteger, ForeignKey('hera_obs.obsid'), primary_key=True)
    event = Column(Enum(*rtp_process_enum, name='rtp_process_enum'), nullable=False)

    @classmethod
    def create(cls, time, obsid, event):
        """
        Create a new rtp_process_event object.

        Parameters:
        ------------
        time: astropy time object
            time of this event
        obsid: long
            observation obsid (Foreign key into Observation)
        event: string
            must be one of ["queued", "started", "finished", "error"]
        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        time = floor(time.gps)

        return cls(time=time, obsid=obsid, event=event)


class RTPProcessRecord(MCDeclarativeBase):
    """
    Definition of rtp_process_record table.

    time: time of this status in floor(gps seconds) (BigInteger). Part of primary_key
    obsid: observation obsid (BigInteger). Part of primary_key. Foreign key into Observation table
    pipeline_list: concatentated list of RTP tasks (String)
    rtp_git_version: RTP git version (String)
    rtp_git_hash: RTP git hash (String)
    hera_qm_git_version: hera_qm git version (String)
    hera_qm_git_hash: hera_qm git hash (String)
    hera_cal_git_version: hera_cal git version (String)
    hera_cal_git_hash: hera_cal git hash (String)
    pyuvdata_git_version: pyuvdata git version (String)
    pyuvdata_git_hash: pyuvdata git hash (String)
    """
    __tablename__ = 'rtp_process_record'
    time = Column(BigInteger, primary_key=True)
    obsid = Column(BigInteger, ForeignKey('hera_obs.obsid'), primary_key=True)
    pipeline_list = Column(Text, nullable=False)
    rtp_git_version = Column(String(32), nullable=False)
    rtp_git_hash = Column(String(64), nullable=False)
    hera_qm_git_version = Column(String(32), nullable=False)
    hera_qm_git_hash = Column(String(64), nullable=False)
    hera_cal_git_version = Column(String(32), nullable=False)
    hera_cal_git_hash = Column(String(64), nullable=False)
    pyuvdata_git_version = Column(String(32), nullable=False)
    pyuvdata_git_hash = Column(String(64), nullable=False)

    @classmethod
    def create(cls, time, obsid, pipeline_list, rtp_git_version, rtp_git_hash, hera_qm_git_version,
               hera_qm_git_hash, hera_cal_git_version, hera_cal_git_hash, pyuvdata_git_version,
               pyuvdata_git_hash):
        """
        Create a new rtp_process_record object.

        Parameters:
        ------------
        time: astropy time object
            time of this event
        obsid: long
            observation obsid (Foreign key into Observation)
        pipeline_list: string
            concatentated list of RTP tasks
        rtp_git_version: string
            RTP git version
        rtp_git_hash: string
            RTP git hash
        hera_qm_git_version: string
            hera_qm git version
        hera_qm_git_hash: string
            hera_qm git hash
        hera_cal_git_version: string
            hera_cal git version
        hera_cal_git_hash: string
            hera_cal git hash
        pyuvdata_git_version: string
            pyuvdata git version
        pyuvdata_git_hash: string
            pyuvdata git hash
        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        time = floor(time.gps)

        return cls(time=time, obsid=obsid, pipeline_list=pipeline_list,
                   rtp_git_version=rtp_git_version, rtp_git_hash=rtp_git_hash,
                   hera_qm_git_version=hera_qm_git_version, hera_qm_git_hash=hera_qm_git_hash,
                   hera_cal_git_version=hera_cal_git_version, hera_cal_git_hash=hera_cal_git_hash,
                   pyuvdata_git_version=pyuvdata_git_version, pyuvdata_git_hash=pyuvdata_git_hash)
