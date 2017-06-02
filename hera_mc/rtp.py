# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""RTP tables

"""

from astropy.time import Time
from sqlalchemy import Column, ForeignKey, Integer, BigInteger, String, Text, Float, Enum
from . import MCDeclarativeBase
from .server_status import ServerStatus


class RTPServerStatus(ServerStatus):
    __tablename__ = 'rtp_server_status'

rtp_process_enum = ['queued', 'started', 'finished', 'error']


class RTPStatus(MCDeclarativeBase):
    """
    Definition of rtp_status table.

    time: time of this status in gps seconds (double). Primary_key
    status: status (options TBD) (String)
    event_min_elapsed: minutes elapsed since last event (Float)
    num_processes: number of processes running (Integer)
    restart_hours_elapsed: hours elapsed since last restart (Float)
    """
    __tablename__ = 'rtp_status'
    time = Column(Float, primary_key=True)
    status = Column(String(64), nullable=False)  # should this be an enum? or text?
    event_min_elapsed = Column(Float, nullable=False)
    num_processes = Column(Integer, nullable=False)
    restart_hours_elapsed = Column(Float, nullable=False)

    tols = {'time': {'atol': 1e-3, 'rtol': 0},
            'event_min_elapsed': {'atol': 1e-3 * 60, 'rtol': 0},
            'restart_hours_elapsed': {'atol': 1e-3 * 3600, 'rtol': 0}}

    @classmethod
    def new_status(cls, time, status, event_min_elapsed, num_processes,
                   restart_hours_elapsed):
        """
        Create a new rtp_status object.

        Parameters:
        ------------
        time: astropy time object
            time of this status
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
        time = time.utc.gps

        return cls(time=time, status=status, event_min_elapsed=event_min_elapsed,
                   num_processes=num_processes, restart_hours_elapsed=restart_hours_elapsed)


class RTPProcessEvent(MCDeclarativeBase):
    """
    Definition of rtp_process_event table.

    time: time of this status in gps seconds (double). Part of primary_key.
    obsid: observation obsid (Long).  Part of primary_key. Foreign key into Observation table
    event: one of ["queued", "started", "finished", "error"] (rtp_process_enum)
    """
    __tablename__ = 'rtp_process_event'
    time = Column(Float, primary_key=True)
    obsid = Column(BigInteger, ForeignKey('hera_obs.obsid'), primary_key=True)
    event = Column(Enum(*rtp_process_enum, name='rtp_process_enum'), nullable=False)

    tols = {'time': {'atol': 1e-3, 'rtol': 0},
            'obsid': {'atol': 0.1, 'rtol': 0}}

    @classmethod
    def new_process_event(cls, time, obsid, event):
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
        time = time.utc.gps

        return cls(time=time, obsid=obsid, event=event)


class RTPProcessRecord(MCDeclarativeBase):
    """
    Definition of rtp_process_record table.

    time: time of this status in gps seconds (double). Part of primary_key
    obsid: observation obsid (Long). Part of primary_key. Foreign key into Observation table
    pipeline_list: concatentated list of RTP tasks (String)
    git_version: RTP git version (String)
    git_hash: RTP git hash (String)
    """
    __tablename__ = 'rtp_process_record'
    time = Column(Float, primary_key=True)
    obsid = Column(BigInteger, ForeignKey('hera_obs.obsid'), primary_key=True)
    pipeline_list = Column(Text, nullable=False)
    git_version = Column(String(32), nullable=False)
    git_hash = Column(String(64), nullable=False)

    tols = {'time': {'atol': 1e-3, 'rtol': 0},
            'obsid': {'atol': 0.1, 'rtol': 0}}

    @classmethod
    def new_process_record(cls, time, obsid, pipeline_list, git_version, git_hash):
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
        git_version: string
            RTP git version
        git_hash: string
            RTP git hash
        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        time = time.utc.gps

        return cls(time=time, obsid=obsid, pipeline_list=pipeline_list,
                   git_version=git_version, git_hash=git_hash)
