# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
RTP tables

The columns in this module are documented in docs/mc_definition.tex,
the documentation needs to be kept up to date with any changes.
"""
from __future__ import absolute_import, division, print_function

from math import floor
from astropy.time import Time
from sqlalchemy import Column, ForeignKey, Integer, BigInteger, String, Text, Float, Enum
from sqlalchemy.ext.hybrid import hybrid_property

from . import MCDeclarativeBase, DEFAULT_MIN_TOL, DEFAULT_HOUR_TOL
from .server_status import ServerStatus

rtp_process_enum = ['queued', 'started', 'finished', 'error']


class RTPServerStatus(ServerStatus):
    __tablename__ = 'rtp_server_status'


class RTPStatus(MCDeclarativeBase):
    """
    Definition of rtp_status table.

    time: time of this status in floor(gps seconds) (BigInteger). Primary_key
    status: status (options TBD) (String)
    event_min_elapsed: minutes elapsed since last event (Float)
    num_processes: number of processes running (Integer)
    restart_hours_elapsed: hours elapsed since last restart (Float)
    """
    __tablename__ = 'rtp_status'
    time = Column(BigInteger, primary_key=True, autoincrement=False)
    status = Column(String(64), nullable=False)  # should this be an enum? or text?
    event_min_elapsed = Column(Float, nullable=False)
    num_processes = Column(Integer, nullable=False)
    restart_hours_elapsed = Column(Float, nullable=False)

    tols = {'event_min_elapsed': DEFAULT_MIN_TOL,
            'restart_hours_elapsed': DEFAULT_HOUR_TOL}

    @classmethod
    def create(cls, time, status, event_min_elapsed, num_processes,
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
        time = floor(time.gps)

        return cls(time=time, status=status, event_min_elapsed=event_min_elapsed,
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


class RTPTaskResourceRecord(MCDeclarativeBase):
    """
    Definition of rtp_task_resource_record table.

    obsid: observation obsid (BigInteger). Part of primary_key. Foreign key into Observation table
    task_name: name of task in pipeline (e.g., OMNICAL) (String). Part of primary_key
    start_time: start time of the task in floor(gps_seconds) (BigInteger)
    stop_time: stop time of the task in floor(gps_seconds) (BigInteger)
    max_memory: the maximum amount of memory consumed by a task, in MB (Float)
    avg_cpu_load: the average amount of CPU used by the task, as number of cores (e.g.,
                  2.00 means 2 CPUs used) (Float)
    """
    __tablename__ = 'rtp_task_resource_record'
    obsid = Column(BigInteger, ForeignKey('hera_obs.obsid'), primary_key=True)
    task_name = Column(Text, primary_key=True)
    start_time = Column(BigInteger, nullable=False)
    stop_time = Column(BigInteger, nullable=False)
    max_memory = Column(Float, nullable=True)
    avg_cpu_load = Column(Float, nullable=True)

    @hybrid_property
    def elapsed(self):
        return self.stop_time - self.start_time

    @classmethod
    def create(cls, obsid, task_name, start_time, stop_time, max_memory=None,
               avg_cpu_load=None):
        """
        Create a new rtp_process_record object.

        Parameters:
        ------------
        obsid: long
            observation obsid (Foreign key into Observation)
        task_name: string
            name of the task in the pipeline (e.g., OMNICAL)
        start_time: astropy time object
            start time of the task
        stop_time: astropy time object
            stop time of the task
        max_memory: float
            max amount of memory used, in MB
        avg_cpu_load: float
            average cpu load, in number of cores
        """
        if not isinstance(start_time, Time):
            raise ValueError('start_time must be an astropy Time object')
        if not isinstance(stop_time, Time):
            raise ValueError('stop_time must be an astropy Time object')
        start_time = floor(start_time.gps)
        stop_time = floor(stop_time.gps)

        return cls(obsid=obsid, task_name=task_name, start_time=start_time, stop_time=stop_time,
                   max_memory=max_memory, avg_cpu_load=avg_cpu_load)
