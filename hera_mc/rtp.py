# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
RTP tables.

The columns in this module are documented in docs/mc_definition.tex,
the documentation needs to be kept up to date with any changes.
"""
from math import floor
from astropy.time import Time
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    BigInteger,
    String,
    Text,
    Float,
    Enum,
)
from sqlalchemy.ext.hybrid import hybrid_property

from . import MCDeclarativeBase, DEFAULT_MIN_TOL, DEFAULT_HOUR_TOL
from .server_status import ServerStatus

rtp_process_enum = ["queued", "started", "finished", "error"]
rtp_task_process_enum = ["started", "finished", "error"]
rtp_task_multiple_process_enum = ["started", "finished", "error"]


class RTPServerStatus(ServerStatus):
    """
    RTP version of the ServerStatus object.

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

    __tablename__ = "rtp_server_status"


class RTPStatus(MCDeclarativeBase):
    """
    Definition of rtp_status table.

    Attributes
    ----------
    time : BigInteger Column
        GPS time of this status, floored. The primary key.
    status : String Column
        status (options TBD).
    event_min_elapsed : Float Column
        Minutes elapsed since last event.
    num_processes : Integer Column
        Number of processes running.
    restart_hours_elapsed : Float Column
        Hours elapsed since last restart.

    """

    __tablename__ = "rtp_status"
    time = Column(BigInteger, primary_key=True, autoincrement=False)
    # should this be an enum? or text?
    status = Column(String(64), nullable=False)
    event_min_elapsed = Column(Float, nullable=False)
    num_processes = Column(Integer, nullable=False)
    restart_hours_elapsed = Column(Float, nullable=False)

    tols = {
        "event_min_elapsed": DEFAULT_MIN_TOL,
        "restart_hours_elapsed": DEFAULT_HOUR_TOL,
    }

    @classmethod
    def create(
        cls, time, status, event_min_elapsed, num_processes, restart_hours_elapsed
    ):
        """
        Create a new rtp_status object.

        Parameters
        ----------
        time : astropy Time object
            time of this status
        status : str
            status (options TBD)
        event_min_elapsed : float
            minutes since last event
        num_processes : int
            number of processes running
        restart_hours_elapsed : float
            hours since last restart

        Returns
        -------
        RTPStatus object

        """
        if not isinstance(time, Time):
            raise ValueError("time must be an astropy Time object")
        time = floor(time.gps)

        return cls(
            time=time,
            status=status,
            event_min_elapsed=event_min_elapsed,
            num_processes=num_processes,
            restart_hours_elapsed=restart_hours_elapsed,
        )


class RTPProcessEvent(MCDeclarativeBase):
    """
    Definition of rtp_process_event table.

    Attributes
    ----------
    time : BigInteger Column
        GPS time of this status, floored. The primary key.
    obsid : BigInteger Column
        Observation obsid.  Part of primary_key. Foreign key into
        Observation table.
    event : Enum Column
        One of ["queued", "started", "finished", "error"] (rtp_process_enum).

    """

    __tablename__ = "rtp_process_event"
    time = Column(BigInteger, primary_key=True)
    obsid = Column(BigInteger, ForeignKey("hera_obs.obsid"), primary_key=True)
    event = Column(Enum(*rtp_process_enum, name="rtp_process_enum"), nullable=False)

    @classmethod
    def create(cls, time, obsid, event):
        """
        Create a new rtp_process_event object.

        Parameters
        ----------
        time : astropy Time object
            Time of this event
        obsid : long
            Observation obsid (Foreign key into Observation)
        event : {"queued", "started", "finished", "error"}
            Process event type.

        Returns
        -------
        RTPProcessEvent object

        """
        if not isinstance(time, Time):
            raise ValueError("time must be an astropy Time object")
        time = floor(time.gps)

        return cls(time=time, obsid=obsid, event=event)


class RTPTaskProcessEvent(MCDeclarativeBase):
    """
    Definition of rtp_task_process_event table.

    Attributes
    ----------
    time : BigInteger Column
        GPS time of this status, floored. The primary key.
    obsid : BigInteger Column
        Observation obsid.  Part of primary_key. Foreign key into
        Observation table.
    task_name : String Column
        Name of task in pipeline (e.g., OMNICAL). Part of primary key.
    event : Enum Column
        One of ["queued", "started", "finished", "error"] (rtp_process_enum).

    """

    __tablename__ = "rtp_task_process_event"
    time = Column(BigInteger, primary_key=True)
    obsid = Column(BigInteger, ForeignKey("hera_obs.obsid"), primary_key=True)
    task_name = Column(Text, primary_key=True)
    event = Column(
        Enum(*rtp_task_process_enum, name="rtp_task_process_enum"),
        nullable=False,
    )

    @classmethod
    def create(cls, time, obsid, task_name, event):
        """
        Create a new rtp_task_process_event object.

        Parameters
        ----------
        time : astropy Time object
            Time of this event
        obsid : long
            Observation obsid (Foreign key into Observation)
        task_name : str
            Name of task in pipeline (e.g., OMNICAL).
        event : {"queued", "started", "finished", "error"}
            Process event type.

        Returns
        -------
        RTPTaskProcessEvent object

        """
        if not isinstance(time, Time):
            raise ValueError("time must be an astropy Time object")
        time = floor(time.gps)

        return cls(time=time, obsid=obsid, task_name=task_name, event=event)


class RTPTaskMultipleProcessEvent(MCDeclarativeBase):
    """
    Definition of rtp_task_multiple_process_event table.

    Attributes
    ----------
    time : BigInteger Column
        GPS time of this status, floored. Part of the primary key.
    obsid_start : BigInteger Column
        Starting obsid for the set of obsids included in the task. Part of
        primary_key. Foreign key into Observation table.
    task_name : String Column
        Name of task in pipeline (e.g., OMNICAL). Part of primary_key
    event : Enum Column
        One of ["queued", "started", "finished", "error"]
        (rtp_task_multiple_process_enum).
    """

    __tablename__ = "rtp_task_multiple_process_event"
    time = Column(BigInteger, primary_key=True)
    obsid_start = Column(BigInteger, ForeignKey("hera_obs.obsid"), primary_key=True)
    task_name = Column(Text, primary_key=True)
    event = Column(
        Enum(*rtp_task_multiple_process_enum, name="rtp_task_multiple_process_enum"),
        nullable=False,
    )

    @classmethod
    def create(cls, time, obsid_start, task_name, event):
        """
        Create a new rtp_task_multiple_process_event object.

        Parameters
        ----------
        time : astropy Time object
            Time of this event
        obsid_start : long
            Observation obsid (Foreign key into Observation)
        task_name : str
            Name of task in pipeline (e.g., OMNICAL).
        event : {"started", "finished", "error"}
            Process event type.

        Returns
        -------
        RTPTaskMultipleProcessEvent object
        """
        if not isinstance(time, Time):
            raise ValueError("time must be an astropy Time object")
        time = floor(time.gps)

        return cls(time=time, obsid_start=obsid_start, task_name=task_name, event=event)


class RTPProcessRecord(MCDeclarativeBase):
    """
    Definition of rtp_process_record table.

    Attributes
    ----------
    time : BigInteger Column
        GPS time of this record, floored. The primary key.
    obsid : BigInteger Column
        Observation obsid.  Part of primary_key. Foreign key into
        Observation table.
    pipeline_list : String Column
        Concatentated list of RTP tasks.
    rtp_git_version : String Column
        RTP git version.
    rtp_git_hash : String Column
        RTP git hash.
    hera_qm_git_version : String Column
        hera_qm git version.
    hera_qm_git_hash : String Column
        hera_qm git hash.
    hera_cal_git_version : String Column
        hera_cal git version.
    hera_cal_git_hash : String Column
        hera_cal git hash.
    pyuvdata_git_version : String Column
        pyuvdata git version.
    pyuvdata_git_hash : String Column
        pyuvdata git hash.

    """

    __tablename__ = "rtp_process_record"
    time = Column(BigInteger, primary_key=True)
    obsid = Column(BigInteger, ForeignKey("hera_obs.obsid"), primary_key=True)
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
    def create(
        cls,
        time,
        obsid,
        pipeline_list,
        rtp_git_version,
        rtp_git_hash,
        hera_qm_git_version,
        hera_qm_git_hash,
        hera_cal_git_version,
        hera_cal_git_hash,
        pyuvdata_git_version,
        pyuvdata_git_hash,
    ):
        """
        Create a new rtp_process_record object.

        Parameters
        ----------
        time : astropy Time object
            time of this event
        obsid : long
            observation obsid (Foreign key into Observation)
        pipeline_list : str
            concatentated list of RTP tasks
        rtp_git_version : str
            RTP git version
        rtp_git_hash : str
            RTP git hash
        hera_qm_git_version : str
            hera_qm git version
        hera_qm_git_hash : str
            hera_qm git hash
        hera_cal_git_version : str
            hera_cal git version
        hera_cal_git_hash : str
            hera_cal git hash
        pyuvdata_git_version : str
            pyuvdata git version
        pyuvdata_git_hash : str
            pyuvdata git hash

        Returns
        -------
        RTPProcessRecord object

        """
        if not isinstance(time, Time):
            raise ValueError("time must be an astropy Time object")
        time = floor(time.gps)

        return cls(
            time=time,
            obsid=obsid,
            pipeline_list=pipeline_list,
            rtp_git_version=rtp_git_version,
            rtp_git_hash=rtp_git_hash,
            hera_qm_git_version=hera_qm_git_version,
            hera_qm_git_hash=hera_qm_git_hash,
            hera_cal_git_version=hera_cal_git_version,
            hera_cal_git_hash=hera_cal_git_hash,
            pyuvdata_git_version=pyuvdata_git_version,
            pyuvdata_git_hash=pyuvdata_git_hash,
        )


class RTPTaskJobID(MCDeclarativeBase):
    """
    Definition of rtp_task_jobid table.

    Holds the SLURM job id associated with each obsid/task so statistics can be
    associated with that obsid/task after the run completes (to fill out the
    rtp_task_resource_record table).

    Attributes
    ----------
    obsid : BigInteger Column
        Observation obsid.  Part of primary_key. Foreign key into
        Observation table.
    task_name : String Column
        Name of task in pipeline (e.g., OMNICAL). Part of primary_key.
    start_time : BigInteger Column
        Start time of the job in floor(gps_seconds). Part of primary_key.
    job_id : BigInteger Column
        Job ID of the task.

    """

    __tablename__ = "rtp_task_jobid"
    obsid = Column(BigInteger, ForeignKey("hera_obs.obsid"), primary_key=True)
    task_name = Column(Text, primary_key=True)
    start_time = Column(BigInteger, nullable=False, primary_key=True)
    job_id = Column(BigInteger, nullable=False)

    @classmethod
    def create(cls, obsid, task_name, start_time, job_id):
        """
        Create a new RTPTaskJobID object.

        Parameters
        ----------
        obsid : long
            Observation obsid (Foreign key into Observation).
        task_name : str
            Name of the task in the pipeline (e.g., OMNICAL).
        start_time : astropy Time object
            Start time of the task.
        job_id : int
            Job ID of the task

        Returns
        -------
        RTPTaskJobID object

        """
        if not isinstance(start_time, Time):
            raise ValueError("start_time must be an astropy Time object")
        start_time = floor(start_time.gps)

        return cls(
            obsid=obsid, task_name=task_name, start_time=start_time, job_id=job_id
        )


class RTPTaskResourceRecord(MCDeclarativeBase):
    """
    Definition of rtp_task_resource_record table.

    Attributes
    ----------
    obsid : BigInteger Column
        Observation obsid.  Part of primary_key. Foreign key into
        Observation table.
    task_name : String Column
        Name of task in pipeline (e.g., OMNICAL). Part of primary_key
    start_time : BigInteger Column
        Start time of the task in floor(gps_seconds).
    stop_time : BigInteger Column
        Stop time of the task in floor(gps_seconds).
    max_memory : Float Column
        The maximum amount of memory consumed by a task, in MB.
    avg_cpu_load : Float Column
        The average amount of CPU used by the task, as number of cores
        (e.g., 2.00 means 2 CPUs used).

    """

    __tablename__ = "rtp_task_resource_record"
    obsid = Column(BigInteger, ForeignKey("hera_obs.obsid"), primary_key=True)
    task_name = Column(Text, primary_key=True)
    start_time = Column(BigInteger, nullable=False)
    stop_time = Column(BigInteger, nullable=False)
    max_memory = Column(Float, nullable=True)
    avg_cpu_load = Column(Float, nullable=True)

    @hybrid_property
    def elapsed(self):
        """Time elapsed for this task."""
        return self.stop_time - self.start_time

    @classmethod
    def create(
        cls, obsid, task_name, start_time, stop_time, max_memory=None, avg_cpu_load=None
    ):
        """
        Create a new RTPTaskResourceRecord object.

        Parameters
        ----------
        obsid : long
            Observation obsid (Foreign key into Observation).
        task_name : str
            Name of the task in the pipeline (e.g., OMNICAL).
        start_time : astropy Time object
            Start time of the task.
        stop_time : astropy Time object
            Stop time of the task.
        max_memory : float
            Max amount of memory used, in MB.
        avg_cpu_load : float
            Average cpu load, in number of cores.

        Returns
        -------
        RTPTaskResourceRecord object

        """
        if not isinstance(start_time, Time):
            raise ValueError("start_time must be an astropy Time object")
        if not isinstance(stop_time, Time):
            raise ValueError("stop_time must be an astropy Time object")
        start_time = floor(start_time.gps)
        stop_time = floor(stop_time.gps)

        return cls(
            obsid=obsid,
            task_name=task_name,
            start_time=start_time,
            stop_time=stop_time,
            max_memory=max_memory,
            avg_cpu_load=avg_cpu_load,
        )


class RTPLaunchRecord(MCDeclarativeBase):
    """
    Define the rtp_launch_record table.

    Attributes
    ----------
    obsid : BigInteger Column
        Observation obsid. Part of primary_key. Foreign key into Observation
        table.
    submitted_time : BigInteger Column
        GPS time of the most recent job launch, floored.
    rtp_attempts : BigInteger Column
        Number of times the file has been attempted to run as part of RTP.
    jd : BigInteger Column
        The integer Julian Date of the observation. Used for grouping jobs
        together.
    obs_tag : String Column
        The observation tag of the data.
    filename : String Column
        The filename of the observation.
    prefix : String Column
        The full path to the directory where the data file is stored.

    """

    __tablename__ = "rtp_launch_record"
    obsid = Column(BigInteger, ForeignKey("hera_obs.obsid"), primary_key=True)
    submitted_time = Column(BigInteger)
    rtp_attempts = Column(BigInteger, nullable=False)
    jd = Column(BigInteger, nullable=False)
    obs_tag = Column(String(128), nullable=False)
    filename = Column(String(128), nullable=False)
    prefix = Column(String(128), nullable=False)

    @classmethod
    def create(
        cls,
        obsid,
        jd,
        obs_tag,
        filename,
        prefix,
        submitted_time=None,
        rtp_attempts=0,
    ):
        """
        Create a new rtp_launch_record object.

        Parameters
        ----------
        obsid : long
            Observation obsid (Foreign key into Observation).
        jd : int
            Integer Julian Date of the observation.
        obs_tag : str
            Observation tag of the data.
        filename : str
            The name of the corresponding raw data file.
        prefix : str
            The path to the directory where the data file is stored.
        submitted_time : astropy Time, optional
            Time of the most recent job submission.
        rtp_attempts : int, optional
            The number of times this obsid has been run through RTP.

        Returns
        -------
        RTPLaunchRecord object

        """
        if not isinstance(obsid, int):
            raise ValueError("obsid must be an integer.")
        if not isinstance(jd, int):
            raise ValueError("jd must be an integer.")
        if not isinstance(obs_tag, str):
            raise ValueError("obs_tag must be a string.")
        if not isinstance(filename, str):
            raise ValueError("filename must be a string.")
        if not isinstance(prefix, str):
            raise ValueError("prefix must be a string.")
        if submitted_time is not None:
            if not isinstance(submitted_time, Time):
                raise ValueError("submitted_time must be an astropy Time object.")
            submitted_time = int(floor(submitted_time.gps))
        if not isinstance(rtp_attempts, int):
            raise ValueError("rtp_attempts must be an integer.")

        return cls(
            obsid=obsid,
            jd=jd,
            obs_tag=obs_tag,
            filename=filename,
            prefix=prefix,
            submitted_time=submitted_time,
            rtp_attempts=rtp_attempts,
        )


class RTPTaskMultipleTrack(MCDeclarativeBase):
    """
    Definition of rtp_task_multiple_track table.

    Tracks which obsids are included in an rtp task that includes multiple obsids. This
    is a many-to-one mapping table with a row per obsid that is included in the task.

    Attributes
    ----------
    obsid_start : BigInteger Column
        Starting obsid for the set of obsids included in the task. Used along with the
        task_name as the unique identifier in the `rtp_task_resource_record_multiple` table.
        Part of primary_key. Foreign key into Observation table.
    task_name : String Column
        Name of task in pipeline (e.g., OMNICAL). Part of primary_key.
    obsid : BigInteger Column
        Start time of the job in floor(gps_seconds). Part of primary_key. Foreign key into
        Observation table.

    """

    __tablename__ = "rtp_task_multiple_track"
    obsid_start = Column(BigInteger, ForeignKey("hera_obs.obsid"), primary_key=True)
    task_name = Column(Text, primary_key=True)
    obsid = Column(BigInteger, ForeignKey("hera_obs.obsid"), primary_key=True)

    @classmethod
    def create(cls, obsid_start, task_name, obsid):
        """
        Create a new RTPTaskMultipleTrack object.

        Parameters
        ----------
        obsid_start : long
            Starting obsid for the set of obsids included in the task. Used along with
            the task_name as the unique identifier in the `rtp_task_resource_record_multiple`
            table (Foreign key into Observation).
        task_name : str
            Name of the task in the pipeline (e.g., OMNICAL).
        obsid : long
            Observation obsid included in this task (Foreign key into Observation).

        Returns
        -------
        RTPTaskMultipleTrack object

        """
        return cls(obsid_start=obsid_start, task_name=task_name, obsid=obsid)


class RTPTaskMultipleJobID(MCDeclarativeBase):
    """
    Definition of rtp_task_multiple_jobid table.

    Holds the SLURM job id associated with each obsid_start/task for tasks that use
    multiple obsids so statistics can be associated with that obsid_start/task after
    the run completes (to fill out the rtp_task_multiple_resource_record table).

    Attributes
    ----------
    obsid_start : BigInteger Column
        Starting obsid for the set of obsids included in the task. Part of primary_key.
        Foreign key into Observation table.
    task_name : String Column
        Name of task in pipeline (e.g., OMNICAL). Part of primary_key.
    start_time : BigInteger Column
        Start time of the job in floor(gps_seconds). Part of primary_key.
    job_id : BigInteger Column
        Job ID of the task.

    """

    __tablename__ = "rtp_task_multiple_jobid"
    obsid_start = Column(BigInteger, ForeignKey("hera_obs.obsid"), primary_key=True)
    task_name = Column(Text, primary_key=True)
    start_time = Column(BigInteger, nullable=False, primary_key=True)
    job_id = Column(BigInteger, nullable=False)

    @classmethod
    def create(cls, obsid_start, task_name, start_time, job_id):
        """
        Create a new RTPTaskMultipleJobID object.

        Parameters
        ----------
        obsid_start : long
            Starting obsid for the set of obsids included in the task.
            (Foreign key into Observation).
        task_name : str
            Name of the task in the pipeline (e.g., OMNICAL).
        start_time : astropy Time object
            Start time of the task.
        job_id : int
            Job ID of the task

        Returns
        -------
        RTPTaskMultipleJobID object

        """
        if not isinstance(start_time, Time):
            raise ValueError("start_time must be an astropy Time object")
        start_time = floor(start_time.gps)

        return cls(
            obsid_start=obsid_start,
            task_name=task_name,
            start_time=start_time,
            job_id=job_id,
        )


class RTPTaskMultipleResourceRecord(MCDeclarativeBase):
    """
    Definition of rtp_task_multiple_resource_record table.

    Attributes
    ----------
    obsid_start : BigInteger Column
        Starting obsid for the set of obsids included in the task. Part of primary_key.
        Foreign key into Observation table.
    task_name : String Column
        Name of task in pipeline (e.g., OMNICAL). Part of primary_key
    start_time : BigInteger Column
        Start time of the task in floor(gps_seconds).
    stop_time : BigInteger Column
        Stop time of the task in floor(gps_seconds).
    max_memory : Float Column
        The maximum amount of memory consumed by a task, in MB.
    avg_cpu_load : Float Column
        The average amount of CPU used by the task, as number of cores
        (e.g., 2.00 means 2 CPUs used).

    """

    __tablename__ = "rtp_task_multiple_resource_record"
    obsid_start = Column(BigInteger, ForeignKey("hera_obs.obsid"), primary_key=True)
    task_name = Column(Text, primary_key=True)
    start_time = Column(BigInteger, nullable=False)
    stop_time = Column(BigInteger, nullable=False)
    max_memory = Column(Float, nullable=True)
    avg_cpu_load = Column(Float, nullable=True)

    @hybrid_property
    def elapsed(self):
        """Time elapsed for this task."""
        return self.stop_time - self.start_time

    @classmethod
    def create(
        cls,
        obsid_start,
        task_name,
        start_time,
        stop_time,
        max_memory=None,
        avg_cpu_load=None,
    ):
        """
        Create a new RTPTaskMultipleResourceRecord object.

        Parameters
        ----------
        obsid_start : long
            Starting obsid for the set of obsids included in the task
            (Foreign key into Observation).
        task_name : str
            Name of the task in the pipeline (e.g., OMNICAL).
        start_time : astropy Time object
            Start time of the task.
        stop_time : astropy Time object
            Stop time of the task.
        max_memory : float
            Max amount of memory used, in MB.
        avg_cpu_load : float
            Average cpu load, in number of cores.

        Returns
        -------
        RTPTaskMultipleResourceRecord object

        """
        if not isinstance(start_time, Time):
            raise ValueError("start_time must be an astropy Time object")
        if not isinstance(stop_time, Time):
            raise ValueError("stop_time must be an astropy Time object")
        start_time = floor(start_time.gps)
        stop_time = floor(stop_time.gps)

        return cls(
            obsid_start=obsid_start,
            task_name=task_name,
            start_time=start_time,
            stop_time=stop_time,
            max_memory=max_memory,
            avg_cpu_load=avg_cpu_load,
        )
