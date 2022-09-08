# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Correlator M&C interface.

Anything tracked in the correlator redis database and accessed via hera_corr_cm.
Includes many SNAP-related things.
"""
import json
import warnings
from math import floor

import numpy as np
import redis
from astropy.time import Time
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
)

from . import MCDeclarativeBase

# default acclen -- corresponds to a bit under 10 seconds (~9.66 seconds)
DEFAULT_ACCLEN_SPECTRA = 147456

DEFAULT_REDIS_ADDRESS = "redishost"

signal_source_list = [
    "antenna",
    "load",
    "noise",
    "digital_same_seed",
    "digital_different_seed",
]
tag_list = ["science", "engineering"]
corr_component_events = {
    "f_engine": ["sync"],
    "x_engine": ["integration_start"],
    "catcher": ["start", "stop", "stop_timeout"],
}


class ArraySignalSource(MCDeclarativeBase):
    """
    Definition of array_signal_source table.

    Attributes
    ----------
    time : BigInteger Column
        GPS time that the when the input source was set, floored. The primary key.
    source : String Column
        One of "antenna", "load", "noise", "digital_noise_same",
        "digital_noise_different" (listed in signal_source_list).

    """

    __tablename__ = "array_signal_source"
    time = Column(BigInteger, primary_key=True)
    source = Column(String, nullable=False)

    @classmethod
    def create(cls, time, source):
        """
        Create a new correlator config status object.

        Parameters
        ----------
        time : astropy Time object
            Astropy time object based on a timestamp reported by the correlator.
        source : str
            One of "antenna", "load", "noise", "digital_noise_same",
            "digital_noise_different" (listed in signal_source_list).

        """
        if not isinstance(time, Time):
            raise ValueError("time must be an astropy Time object")
        corr_time = floor(time.gps)

        if source not in signal_source_list:
            raise ValueError(
                f"invalid signal source value was passed. Passed value was {source}, "
                f"must be one of: {signal_source_list}"
            )

        return cls(time=corr_time, source=source)


def _get_snap_input_from_redis(redishost=DEFAULT_REDIS_ADDRESS):
    """
    Get the SNAP input state from redis ("adc" or "noise").

    Parameters
    ----------
    redishost : str
        Address of redis database

    Returns
    -------
    snap_source : str
        Should be one of "adc" or "noise" (others are errors).
    snap_seed_type : str
        Should be one of "same" or "diff" (others are errors)..
    snap_time : astropy Time object
        Time that source was last set.

    """
    redis_pool = redis.ConnectionPool(host=redishost, decode_responses=True)
    rsession = redis.Redis(connection_pool=redis_pool, charset="utf-8")

    snap_input_dict = rsession.hgetall("corr:status:input")
    # keys are:
    # - source (either "adc" or "noise")
    # - seed (either "same" or "diff")
    # - time (a unix time stamp).

    snap_source = snap_input_dict["source"]
    snap_seed_type = snap_input_dict["seed"]
    snap_time = Time(snap_input_dict["time"], format="unix")

    return snap_source, snap_seed_type, snap_time


def _get_fem_switch_from_redis(redishost=DEFAULT_REDIS_ADDRESS):
    """
    Get the FEM switch state from redis ("antenna" or "load" or "noise").

    Parameters
    ----------
    redishost : str
        Address of redis database

    Returns
    -------
    fem_switch : str
        Should be one of "antenna", "load" or "noise" (others are errors).
    fem_time : astropy Time object
        Time that the fem_switch was last set.

    """
    redis_pool = redis.ConnectionPool(host=redishost, decode_responses=True)
    rsession = redis.Redis(connection_pool=redis_pool, charset="utf-8")

    fem_switch_dict = rsession.hgetall("corr:fem_switch_state")
    # keys are:
    #  - state ("antenna" or "load" or "noise")
    #  - time (a unix time stamp).

    fem_switch = fem_switch_dict["state"]
    fem_time = Time(fem_switch_dict["time"], format="unix")

    return fem_switch, fem_time


def _define_array_signal_source(
    snap_source, snap_seed, snap_time, fem_switch, fem_time
):
    """
    Define the array signal source based on the snap input and fem switch information.

    Parameters
    ----------
    snap_source : str
        One of "adc" or "noise" (meaning digital noise).
    snap_seed : str
        One of "same" or "diff"
    snap_time : astropy Time object
        Time of the snap input status.
    fem_switch : str
        One of "antenna", "load" or "noise"
    fem_time : astropy Time object
        Time of the fem switch status.

    Returns
    -------
    time : astropy Time object
        Time of the array signal source.
    source : str
        One of "antenna", "load", "noise", "digital_noise_same",
        "digital_noise_different" (listed in signal_source_list).

    """
    if snap_source == "adc":
        # Using input from FEM, now we need the fem switch info
        source = fem_switch
        if source not in signal_source_list[0:3]:
            raise ValueError(
                f"On FEM input, FEM switch state is {source}, should be one of "
                f"{signal_source_list[0:3]}."
            )
        # Use the most recent time of when either the snap input or fem input changed
        time = max(snap_time, fem_time)
    elif snap_source == "noise":
        # on digital noise. get the seed and time info
        if snap_seed == "same":
            source = "digital_same_seed"
        elif snap_seed == "diff":
            source = "digital_different_seed"
        else:
            raise ValueError(
                f"On digital noise, seed type is {snap_seed}, should be 'same' or "
                "'diff'."
            )
        time = snap_time
    else:
        raise ValueError(
            f"SNAP input information is {snap_source}, should be 'adc' or 'noise'."
        )

    return time, source


def _get_array_source_from_redis(redishost=DEFAULT_REDIS_ADDRESS):
    """
    Get the current array source info from redis.

    Parameters
    ----------
    redishost : str
        Address of redis database

    Returns
    -------
    time : astropy Time object
        Time of this status
    source : str
        One of "antenna", "load", "noise", "digital_noise_same",
        "digital_noise_different" (listed in signal_source_list).

    Raises
    ------
    ValueError
        If values pulled from redis cannot be interpreted properly.

    """
    snap_source, snap_seed_type, snap_time = _get_snap_input_from_redis(
        redishost=redishost
    )
    fem_switch, fem_time = _get_fem_switch_from_redis(redishost=redishost)

    return _define_array_signal_source(
        snap_source, snap_seed_type, snap_time, fem_switch, fem_time
    )


class CorrelatorComponentEventTime(MCDeclarativeBase):
    """
    Definition of correlator_component_event_time table.

    Specifies when various correlator components had an event related to normal
    observing (expected to be order one entry per component-event per day).

    Attributes
    ----------
    component : String Column
        Correlator component, one of "f_engine", "x_engine",
        "catcher" (key in corr_component_events). Part of the primary key.
    event : String Column
        Correlator component event, one of "sync" (f-engine),
        "integration_start" (x-engine), "start", "stop", "stop_timeout" (catcher).
        Component and event must be paired in corr_component_events.
        Part of the primary key.
    time : Float Column
        GPS time that the component started (note that unlike other tables this is not
        floored, it is a float). Part of the primary key.

    """

    __tablename__ = "correlator_component_event_time"
    component = Column(String, primary_key=True)
    event = Column(String, primary_key=True)
    time = Column(Float, primary_key=True)

    tols = {
        "time": {"atol": 1e-3, "rtol": 0},
    }

    @classmethod
    def create(cls, component, event, time):
        """
        Create a new correlator component time object.

        Parameters
        ----------
        component : str
            Correlator component, one of "f_engine", "x_engine", "catcher"
            (key in corr_component_events).
        event : str
            Correlator component event, one of "sync" (f-engine),
            "integration_start" (x-engine), "start", "stop", "stop_timeout" (catcher).
            Component and event must be paired in corr_component_events.
        time : astropy Time object
            Astropy time object based on a timestamp reported by the correlator.

        """
        if not isinstance(time, Time):
            raise ValueError("time must be an astropy Time object")
        corr_time = time.gps

        if component not in corr_component_events.keys():
            raise ValueError(
                "invalid component value was passed. Passed component was "
                f"{component}, must be one of: {corr_component_events.keys()}"
            )

        if event not in corr_component_events[component]:
            raise ValueError(
                f"invalid event value for {component} was passed. Passed value was "
                f"{event}, must be one of: {corr_component_events[component]}"
            )

        return cls(component=component, event=event, time=corr_time)


def _get_f_engine_sync_time_from_redis(redishost=DEFAULT_REDIS_ADDRESS):
    """
    Get the most recent f-engine sync time from redis.

    Parameters
    ----------
    redishost : str
        Address of redis database

    Returns
    -------
    time : astropy Time object
        Time of the most recent f-engine sync

    """
    redis_pool = redis.ConnectionPool(host=redishost, decode_responses=True)
    rsession = redis.Redis(connection_pool=redis_pool, charset="utf-8")

    # The redis key that is currently being used for this is in unix ms.
    # In the future, this key will change in redis to "feng:sync_time".
    # Unclear if that will be in Unix seconds or ms.
    sync_time_unix_ms = rsession.get("corr:feng_sync_time")

    sync_time_unix = float(sync_time_unix_ms) * 1e-3

    return Time(sync_time_unix, format="unix")


def _get_catcher_start_stop_time_from_redis(
    redishost=DEFAULT_REDIS_ADDRESS,
    taking_data_dict=None,
):
    """
    Get the most recent catcher start time from redis.

    Parameters
    ----------
    redishost : str
        Address of redis database
    taking_data_dict: A dict spoofing the dict returned by the redis call
        `hgetall("corr:is_taking_data")` for testing purposes.
        Example: {b'state': b'True', b'time': b'1654884281'} or empty dict

    Returns
    -------
    event : str or None
        Either "start" if the catcher is currently taking data or "stop"
        if it is not. Returns None if the redis key has timed out.
    time : astropy Time object or None
        Time when the data taking last started or stopped. . Returns None if the redis
        key has timed out.

    """
    if taking_data_dict is None:
        redis_pool = redis.ConnectionPool(host=redishost, decode_responses=True)
        rsession = redis.Redis(connection_pool=redis_pool, charset="utf-8")
        taking_data_dict = rsession.hgetall("corr:is_taking_data")

    if len(taking_data_dict) > 0:
        if taking_data_dict["state"] == "True":
            event = "start"
        else:
            event = "stop"
        time = Time(taking_data_dict["time"], format="unix")

        return event, time
    else:
        return None, None


def _get_correlator_component_event_times_from_redis(
    redishost=DEFAULT_REDIS_ADDRESS,
    taking_data_dict=None,
):
    """
    Get the correlator component event times from redis.

    This currently only gets the f-engine sync time and the catcher start/stop times.
    In the future, when the x-engine integration start time (in Mcounts) is available
    it will be added to this function as well.

    Parameters
    ----------
    redishost : str
        Address of redis database (only used if corr_cm is None)
    taking_data_dict: A dict spoofing the dict returned by the redis call
        `hgetall("corr:is_taking_data")` for testing purposes.
        Example: {b'state': b'True', b'time': b'1654884281'} or empty dict

    Returns
    -------
    dict
        Keys are correlator components, values are sub-dict with "event" (str) and
        "time" (astropy Time objects).

    """
    outdict = {}

    outdict["f_engine"] = {
        "event": "sync",
        "time": _get_f_engine_sync_time_from_redis(redishost=redishost),
    }

    catcher_event, catcher_time = _get_catcher_start_stop_time_from_redis(
        redishost=redishost, taking_data_dict=taking_data_dict
    )

    if catcher_event is not None:
        outdict["catcher"] = {"event": catcher_event, "time": catcher_time}

    return outdict


class CorrelatorCatcherFile(MCDeclarativeBase):
    """
    Definition of correlator_catcher_file table.

    Track the files written by the catcher.

    Attributes
    ----------
    time : BigInteger Column
        GPS time that the file started being written, floored. The primary key.
    filename : String Column
        Name of the current file being written by the catcher.

    """

    __tablename__ = "correlator_catcher_file"
    time = Column(BigInteger, primary_key=True)
    filename = Column(String, nullable=False)

    @classmethod
    def create(cls, time, filename):
        """
        Create a new correlator component time object.

        Parameters
        ----------
        time : astropy Time object
            Astropy time object based on a timestamp reported by the correlator.
        filename : str
            Name of the current file being written by the catcher.

        """
        if not isinstance(time, Time):
            raise ValueError("time must be an astropy Time object")
        corr_time = floor(time.gps)

        return cls(time=corr_time, filename=filename)


def _get_catcher_file_from_redis(redishost=DEFAULT_REDIS_ADDRESS):
    """
    Get the current catcher file from redis.

    Parameters
    ----------
    redishost : str
        Address of redis database

    Returns
    -------
    time : astropy Time object
        Time the current file started being written
    filename : str
        Name of the current file being written by the catcher.

    """
    redis_pool = redis.ConnectionPool(host=redishost, decode_responses=True)
    rsession = redis.Redis(connection_pool=redis_pool, charset="utf-8")

    catcher_file_dict = rsession.hgetall("corr:current_file")
    # keys are:
    #  - filename
    #  - time (a unix time stamp).
    time = Time(catcher_file_dict["time"], format="unix")
    filename = catcher_file_dict["filename"]

    return time, filename


class CorrelatorConfigFile(MCDeclarativeBase):
    """
    Definition of correlator_config_file table.

    Attributes
    ----------
    hash : String Column
        Unique MD5 hash for the config. The primary key.
    filename : String Column
        Name of the config file in the Librarian.

    """

    __tablename__ = "correlator_config_file"
    config_hash = Column(String, primary_key=True)
    filename = Column(String, nullable=False)

    @classmethod
    def create(cls, config_hash, filename):
        """
        Create a new correlator config file object.

        Parameters
        ----------
        config_hash : str
            Unique MD5 hash of the config.
        filename : str
            Name of the config file in the Librarian.

        """
        return cls(config_hash=config_hash, filename=filename)


class CorrelatorConfigStatus(MCDeclarativeBase):
    """
    Definition of correlator config status table.

    Attributes
    ----------
    time : BigInteger Column
        GPS time that the config started, floored. The primary key.
    config_hash : String Column
        Unique MD5 hash for the config. Foreign key into correlator_config_file.

    """

    __tablename__ = "correlator_config_status"
    time = Column(BigInteger, primary_key=True)
    config_hash = Column(
        String, ForeignKey("correlator_config_file.config_hash"), nullable=False
    )

    @classmethod
    def create(cls, time, config_hash):
        """
        Create a new correlator config status object.

        Parameters
        ----------
        time : astropy Time object
            Astropy time object based on a timestamp reported by the correlator.
        config_hash : str
            Unique hash for the config. Foreign key into correlator_config_file.

        """
        if not isinstance(time, Time):
            raise ValueError("time must be an astropy Time object")
        corr_time = floor(time.gps)

        return cls(time=corr_time, config_hash=config_hash)


def _get_config(corr_cm=None, redishost=DEFAULT_REDIS_ADDRESS):
    """
    Get the latest config, hash and associated timestamp from the correlator.

    Parameters
    ----------
    corr_cm : hera_corr_cm.HeraCorrCM object
        HeraCorrCM object to use. If None, this function will make a new one.
    redishost : str
        Address of redis database (only used if corr_cm is None)

    Returns
    -------
    dict
        Keys are 'time', 'hash' and 'config' (a yaml processed string)

    """
    import hera_corr_cm

    if corr_cm is None:
        corr_cm = hera_corr_cm.HeraCorrCM(redishost=redishost)

    timestamp, config, config_hash = corr_cm.get_config()
    time = Time(timestamp, format="unix")

    return {"time": time, "hash": config_hash, "config": config}


class CorrelatorConfigParams(MCDeclarativeBase):
    """
    Definition of correlator_config_params table.

    Attributes
    ----------
    config_hash : String Column
        Unique MD5 hash for the config. Part of the primary key. Foreign key into
        correlator_config_file.
    parameter : String Column
        Name of correlator parameter. Part of the primary key.
    value : String Column
        Value of parameter.
    """

    __tablename__ = "correlator_config_params"
    config_hash = Column(
        String,
        ForeignKey("correlator_config_file.config_hash"),
        primary_key=True,
        nullable=False,
    )
    parameter = Column(String, primary_key=True)
    value = Column(String, nullable=False)

    @classmethod
    def create(cls, config_hash, parameter, value):
        """
        Create a new CorrelatorConfigParams object.

        Parameters
        ----------
        config_hash : str
            MD5 hash of configuration contents
        parameter : str
            Name of correlator parameter
        value : str
            Value of parameter
        """
        return cls(config_hash=config_hash, parameter=parameter, value=value)


class CorrelatorConfigActiveSNAP(MCDeclarativeBase):
    """
    Definition of correlator_config_active_snap table.

    Attributes
    ----------
    config_hash : String Column
        Unique MD5 hash for the config. Part of the primary key. Foreign key into
        correlator_config_file.
    hostname : String Column
        Hostname of SNAP (typically e.g. heraNode1Snap2). Part of the primary key.
    """

    __tablename__ = "correlator_config_active_snap"
    config_hash = Column(
        String,
        ForeignKey("correlator_config_file.config_hash"),
        primary_key=True,
        nullable=False,
    )
    hostname = Column(String, primary_key=True)

    @classmethod
    def create(cls, config_hash, hostname):
        """
        Create a new CorrelatorConfigActiveSNAP object.

        Parameters
        ----------
        config_hash : String Column
            MD5 hash of configuration contents
        hostname : String Column
            Hostname of SNAP (typically e.g. heraNode1Snap2)
        """
        return cls(config_hash=config_hash, hostname=hostname)


class CorrelatorConfigInputIndex(MCDeclarativeBase):
    """
    Definition of correlator_config_input_index table.

    Attributes
    ----------
    config_hash : String Column
        Unique MD5 hash for the config. Part of the primary key. Foreign key into
        correlator_config_file.
    correlator_index : Integer Column
        Correlator index value (0 - 349). Part of the primary key.
    hostname : String Column
        Hostname of SNAP (typically e.g. heraNode1Snap2).
    antenna_index_position : Integer Column
        Antenna index position within SNAP (0 - 2).
    """

    __tablename__ = "correlator_config_input_index"
    config_hash = Column(
        String,
        ForeignKey("correlator_config_file.config_hash"),
        primary_key=True,
        nullable=False,
    )
    correlator_index = Column(Integer, primary_key=True)
    hostname = Column(String, nullable=False)
    antenna_index_position = Column(Integer, nullable=False)

    @classmethod
    def create(cls, config_hash, correlator_index, hostname, antenna_index_position):
        """
        Create a new CorrelatorConfigInputIndex object.

        Parameters
        ----------
        config_hash : String Column
            MD5 hash of configuration contents
        correlator_index : Integer Column
            Correlator index value (0 - 349)
        hostname : String Column
            Hostname of SNAP (typically e.g. heraNode1Snap2)
        antenna_index_position : Integer Column
            Antenna ndex position within SNAP (0 - 2)
        """
        return cls(
            config_hash=config_hash,
            correlator_index=correlator_index,
            hostname=hostname,
            antenna_index_position=antenna_index_position,
        )


class CorrelatorConfigPhaseSwitchIndex(MCDeclarativeBase):
    """
    Definition of correlator_config_phase_switch_index table.

    Attributes
    ----------
    config_hash : String Column
        Unique MD5 hash for the config. Part of the primary key. Foreign key into
        correlator_config_file.
    hostname : String Column
        Hostname of SNAP (typically e.g. heraNode1Snap2). Part of the primary key.
    phase_switch_index : Integer Column
        Phase switch index value (1 - 24). Part of the primary key.
    antpol_index_position : Integer Column
        Antpol index position within SNAP (0 - 5)
    """

    __tablename__ = "correlator_config_phase_switch_index"
    config_hash = Column(
        String,
        ForeignKey("correlator_config_file.config_hash"),
        primary_key=True,
        nullable=False,
    )
    hostname = Column(String, primary_key=True)
    phase_switch_index = Column(Integer, primary_key=True)
    antpol_index_position = Column(Integer, nullable=False)

    @classmethod
    def create(cls, config_hash, hostname, phase_switch_index, antpol_index_position):
        """
        Create a new CorrelatorConfigPhaseSwitchIndex object.

        Parameters
        ----------
        config_hash : String Column
            MD5 hash of configuration contents
        hostname : String Column
            Hostname of SNAP (typically e.g. heraNode1Snap2)
        phase_switch_index : Integer Column
            Phase switch index value (1 - 24)
        antpol_index_position : Integer Column
            Antpol ndex position within SNAP (0 - 5)
        """
        return cls(
            config_hash=config_hash,
            phase_switch_index=phase_switch_index,
            hostname=hostname,
            antpol_index_position=antpol_index_position,
        )


def _parse_config(config, config_hash):
    """
    Parse the config into all the components required for the various config tables.

    Parameters
    ----------
    config : dict
        Dict of config info from redis/hera_corr_cm.
    config_hash : str
        Unique hash of the config.


    Returns
    -------
    list
        List of correlator config related objects including CorrelatorConfigParams,
        CorrelatorConfigActiveSNAP, CorrelatorConfigInputIndex, and
        CorrelatorConfigPhaseSwitchIndex objects.

    """
    obj_list = []
    keys_to_save = [
        "fft_shift",
        "fpgfile",
        "dest_port",
        "log_walsh_step_size",
        "walsh_order",
        "walsh_delay",
    ]
    for key in keys_to_save:
        value = config[key]
        obj_list.append(
            CorrelatorConfigParams.create(
                config_hash=config_hash, parameter=key, value=value
            )
        )

    fengines = sorted(config["fengines"].keys())
    obj_list.append(
        CorrelatorConfigParams.create(
            config_hash=config_hash, parameter="fengines", value=",".join(fengines)
        )
    )
    xengines = [str(x) for x in sorted(config["xengines"].keys())]
    obj_list.append(
        CorrelatorConfigParams.create(
            config_hash=config_hash, parameter="xengines", value=",".join(xengines)
        )
    )
    for xengind, xeng in config["xengines"].items():
        parameter = f"x{xengind}:chan_range"
        value = ",".join([str(_x) for _x in xeng["chan_range"]])
        obj_list.append(
            CorrelatorConfigParams.create(
                config_hash=config_hash, parameter=parameter, value=value
            )
        )
        for evod in ["even", "odd"]:
            for ipma in ["ip", "mac"]:
                parameter = f"x{xengind}:{evod}:{ipma}"
                value = xeng[evod][ipma]
                obj_list.append(
                    CorrelatorConfigParams.create(
                        config_hash=config_hash, parameter=parameter, value=value
                    )
                )
    for hostname, entry in config["fengines"].items():
        obj_list.append(
            CorrelatorConfigActiveSNAP.create(
                config_hash=config_hash,
                hostname=hostname,
            )
        )
        for antind in range(len(entry["ants"])):
            cind = entry["ants"][antind]
            obj_list.append(
                CorrelatorConfigInputIndex.create(
                    config_hash=config_hash,
                    correlator_index=cind,
                    hostname=hostname,
                    antenna_index_position=antind,
                )
            )
        for psind in range(len(entry["phase_switch_index"])):
            pind = entry["phase_switch_index"][psind]
            obj_list.append(
                CorrelatorConfigPhaseSwitchIndex.create(
                    config_hash=config_hash,
                    hostname=hostname,
                    phase_switch_index=pind,
                    antpol_index_position=psind,
                )
            )

    return obj_list


class CorrelatorSoftwareVersions(MCDeclarativeBase):
    """
    Definition of correlator software versions table.

    Attributes
    ----------
    time : BigInteger Column
        GPS time of the version report, floored. Part of primary_key.
    package : String Column
        Name of the correlator software module or <package>:<script> for
        daemonized processes e.g. 'hera_corr_cm',
        'udpSender:hera_node_keep_alive.py'. Part of primary_key.
    version : String Column
        Version string for this package or script.

    """

    __tablename__ = "correlator_software_versions"
    time = Column(BigInteger, primary_key=True)
    package = Column(String, primary_key=True)
    version = Column(String, nullable=False)

    @classmethod
    def create(cls, time, package, version):
        """
        Create a new correlator software versions object.

        Parameters
        ----------
        time : astropy time object
            Astropy time object based on the version report timestamp.
        package : str
            Name of the correlator software module or <package>:<script> for
            daemonized processes(e.g. 'hera_corr_cm',
            'udpSender:hera_node_keep_alive.py')
        version : str
            Version string for this package or script.

        """
        if not isinstance(time, Time):
            raise ValueError("time must be an astropy Time object")
        corr_time = floor(time.gps)

        return cls(time=corr_time, package=package, version=version)


class SNAPConfigVersion(MCDeclarativeBase):
    """
    Definition of SNAP configuration and version table.

    Attributes
    ----------
    init_time : BigInteger Column
        GPS time when the SNAPs were last initialized with the
        `hera_snap_feng_init.py` script, floored. Part of primary_key.
    init_time: gps time when the SNAPs were last initialized with the
        `hera_snap_feng_init.py` script, floored. Part of primary_key.
    version : String Column
        Version string for the hera_corr_f package.
    init_args : String Column
        Arguments passed to the initialization script at runtime.
    config_hash : String Columnn
        Unique hash for the config. Foreign key into correlator_config_file.

    """

    __tablename__ = "snap_config_version"
    init_time = Column(BigInteger, primary_key=True)
    version = Column(String, nullable=False)
    init_args = Column(String, nullable=False)
    config_hash = Column(
        String, ForeignKey("correlator_config_file.config_hash"), nullable=False
    )

    @classmethod
    def create(cls, init_time, version, init_args, config_hash):
        """
        Create a new SNAP configuration and version object.

        Parameters
        ----------
        init_time : astropy time object
            Astropy time object for when the SNAPs were last initialized with
            the `hera_snap_feng_init.py` script.
        version : str
            Version string for the hera_corr_f package.
        init_args : str
            Arguments passed to the initialization script at runtime.
        config_hash : str
            Unique hash of the config. Foreign key into correlator_config_file
            table.

        """
        if not isinstance(init_time, Time):
            raise ValueError("init_time must be an astropy Time object")
        init_time_gps = floor(init_time.gps)

        return cls(
            init_time=init_time_gps,
            version=version,
            init_args=init_args,
            config_hash=config_hash,
        )


def _get_corr_versions(corr_cm=None, redishost=DEFAULT_REDIS_ADDRESS):
    """
    Get the versions dict from the correlator.

    Parameters
    ----------
    corr_cm : hera_corr_cm.HeraCorrCM object
        HeraCorrCM object to use. If None, this function will make a new one.
    redishost : str
        Address of redis database (only used if corr_cm is None)

    Returns
    -------
    dict
        from hera_corr_cm docstring:
            Returns the version of various software modules in dictionary form.
            Keys of this dictionary are software packages, e.g. "hera_corr_cm",
            or of the form <package>:<script> for daemonized processes,
            e.g. "udpSender:hera_node_receiver.py".
            The values of this dictionary are themselves dicts, with keys:
                "version": A version string for this package
                "timestamp": A datetime object indicating when this version
                             was last reported to redis

            There is one special key, "snap", in the top-level of the returned
            dictionary. This stores software and configuration states at the
            time the SNAPs were last initialized with the
            `hera_snap_feng_init.py` script. For the "snap" dictionary keys are:
                "version" : version string for the hera_corr_f package.
                "init_args" : arguments passed to the inialization script at
                              runtime
                "config" : Configuration structure used at initialization time
                "config_timestamp" : datetime instance indicating when this
                                     file was updated in redis
                "config_md5" : MD5 hash of this config file
                "timestamp" : datetime object indicating when the
                              initialization script was called.

    """
    import hera_corr_cm

    if corr_cm is None:
        corr_cm = hera_corr_cm.HeraCorrCM(redishost=redishost)

    return corr_cm.get_version()


class SNAPStatus(MCDeclarativeBase):
    """
    Definition of SNAP status table.

    Attributes
    ----------
    time : BigInteger Column
        GPS time of the snap status data, floored. Part of primary_key.
    hostname : String Column
        SNAP hostname. Part of primary_key.
    node : Integer Column
        Node number.
    snap_loc_num : Integer Column
        SNAP location number.
    serial_number : String Column
        Serial number of the SNAP board.
    psu_alert : Boolean Column
        True if SNAP PSU (aka PMB) controllers have issued an alert.
        False otherwise.
    pps_count : BigInteger Column
        Number of PPS pulses received since last programming cycle.
    fpga_temp : Float Column
        Reported FPGA temperature in degrees Celsius.
    uptime_cycles : BigInteger Column
        Multiples of 500e6 ADC clocks since last programming cycle.
    last_programmed_time :  BigInteger Column
        Last time this FPGA was programmed in floored gps seconds.
    is_programmed : Boolean Column
        True if the host is programmed.
    adc_is_configured : Boolean Column
        True if the host adc is configured
    is_initialized : Boolean Column
        True if host is initialized
    dest_is_configured : Boolean Column
        True if the ethernet destination is configured.
    version : String Column
        Version of firmware installed
    sample_rate : Float Column
        Sample rate in MHz

    """

    __tablename__ = "snap_status"
    time = Column(BigInteger, primary_key=True)
    hostname = Column(String, primary_key=True)
    node = Column(Integer)
    snap_loc_num = Column(Integer)
    serial_number = Column(String)
    psu_alert = Column(Boolean)
    pps_count = Column(BigInteger)
    fpga_temp = Column(Float)
    uptime_cycles = Column(BigInteger)
    last_programmed_time = Column(BigInteger)
    is_programmed = Column(Boolean)
    adc_is_configured = Column(Boolean)
    is_initialized = Column(Boolean)
    dest_is_configured = Column(Boolean)
    version = Column(String)
    sample_rate = Column(Float)

    @classmethod
    def create(
        cls,
        time,
        hostname,
        node,
        snap_loc_num,
        serial_number,
        psu_alert,
        pps_count,
        fpga_temp,
        uptime_cycles,
        last_programmed_time,
        is_programmed,
        adc_is_configured,
        is_initialized,
        dest_is_configured,
        version,
        sample_rate,
    ):
        """
        Create a new SNAP status object.

        Parameters
        ----------
        time : astropy Time object
            Astropy time object based on a timestamp reported by node.
        hostname : str
            SNAP hostname.
        node : int
            Node number.
        snap_loc_num : int
            SNAP location number.
        serial_number : str
            Serial number of the SNAP board.
        psu_alert : bool
            True if SNAP PSU (aka PMB) controllers have issued an alert.
            False otherwise.
        pps_count : int
            Number of PPS pulses received since last programming cycle.
        fpga_temp : float
            Reported FPGA temperature in degrees Celsius.
        uptime_cycles : int
            Multiples of 500e6 ADC clocks since last programming cycle.
        last_programmed_time : astropy Time object
            Astropy time object based on the last time this FPGA was programmed.
        is_programmed : bool
            True if the host is programmed.
        adc_is_configured : bool
            True if the host adc is configured
        is_initialized : bool
            True if host is initialized
        dest_is_configured : bool
            True if the ethernet destination is configured.
        version : str
            Version of firmware installed
        sample_rate : float
            Sample rate in MHz

        """
        if not isinstance(time, Time):
            raise ValueError("time must be an astropy Time object")
        snap_time = floor(time.gps)

        if last_programmed_time is not None:
            if not isinstance(last_programmed_time, Time):
                raise ValueError("last_programmed_time must be an astropy Time object")
            last_programmed_time_gps = floor(last_programmed_time.gps)
        else:
            last_programmed_time_gps = None

        return cls(
            time=snap_time,
            hostname=hostname,
            node=node,
            snap_loc_num=snap_loc_num,
            serial_number=serial_number,
            psu_alert=psu_alert,
            pps_count=pps_count,
            fpga_temp=fpga_temp,
            uptime_cycles=uptime_cycles,
            last_programmed_time=last_programmed_time_gps,
            is_programmed=is_programmed,
            adc_is_configured=adc_is_configured,
            is_initialized=is_initialized,
            dest_is_configured=dest_is_configured,
            version=version,
            sample_rate=sample_rate,
        )


class SNAPInput(MCDeclarativeBase):
    """
    Definition of SNAP input table.

    Attributes
    ----------
    time : BigInteger Column
        GPS time of the snap input data, floored. Part of primary_key, Foreign key into
        snap_status.
    hostname : String Column
        SNAP hostname. Part of primary_key, Foreign key into snap_status.
    snap_channel_number : Integer Column
        The SNAP ADC channel number (0-5), Part of primary_key.
    antenna_number : Integer Column
         Antenna number that is connected to this snap channel number.
    antenna_feed_pol : String Column
        Feed polarization, either 'e' or 'n', that is connected to this snap
        channel number.
    snap_input : String Column
        Either "adc" or "noise-%d" where %d is the noise seed.

    """

    __tablename__ = "snap_input"
    time = Column(BigInteger, primary_key=True)
    hostname = Column(String, primary_key=True)
    snap_channel_number = Column(Integer, primary_key=True)
    antenna_number = Column(Integer)
    antenna_feed_pol = Column(String)
    snap_input = Column(String)

    __table_args__ = (
        ForeignKeyConstraint(
            ["time", "hostname"],
            ["snap_status.time", "snap_status.hostname"],
        ),
        {},
    )

    @classmethod
    def create(
        cls,
        time,
        hostname,
        snap_channel_number,
        antenna_number,
        antenna_feed_pol,
        snap_input,
    ):
        """
        Create a new SNAP input object.

        Parameters
        ----------
        time : astropy Time object
            Astropy time object based on a timestamp reported by node.
        hostname : str
            SNAP hostname.
        snap_channel_number : int
            The SNAP ADC channel number (0-5).
        antenna_number : int
            Antenna number that is connected to this snap channel number.
        antenna_feed_pol : String Column
            Feed polarization, either 'e' or 'n', that is connected to this snap
            channel number.
        snap_input : str
            Either "adc" or "noise-%d" where %d is the noise seed.

        """
        if not isinstance(time, Time):
            raise ValueError("time must be an astropy Time object")
        snap_time = floor(time.gps)

        if antenna_feed_pol is not None and antenna_feed_pol not in ["e", "n"]:
            raise ValueError("antenna_feed_pol must be 'e' or 'n'.")

        return cls(
            time=snap_time,
            hostname=hostname,
            snap_channel_number=snap_channel_number,
            antenna_number=antenna_number,
            antenna_feed_pol=antenna_feed_pol,
            snap_input=snap_input,
        )


def _get_snap_status(corr_cm=None, redishost=DEFAULT_REDIS_ADDRESS):
    """
    Get the snap status dict from the correlator.

    Parameters
    ----------
    corr_cm : hera_corr_cm.HeraCorrCM object
        HeraCorrCM object to use. If None, this function will make a new one.
    redishost : str
        Address of redis database (only used if corr_cm is None)

    Returns
    -------
    dict
        from hera_corr_cm docstring:
            Returns a dictionary of snap status flags. Keys of returned
            dictionaries are snap hostnames. Values of this dictionary are
            status key/val pairs.

            These keys are:
                is_programmed (bool): True if the host is programmed
                adc_is_configured (bool): True if the host adc is configured
                is_initialized (bool): True if host is initialized
                dest_is_configured (bool): True if dest_is_configured
                version (str)      : Version of firmware installed
                sample_rate (float): Sample rate in MHz
                input (str)        : comma-delimited list of 6 stream inputs either:
                    adc = adc,adc,adc,adc,adc,adc
                    digital noise = noise-%d,noise-%d,noise-%d,noise-%d,noise-%d,noise-%d
                    where %d is the noise seed.
                pmb_alert (bool) : True if SNAP PSU controllers have issued an
                                   alert. False otherwise.
                pps_count (int)  : Number of PPS pulses received since last
                                   programming cycle
                serial (str)     : Serial number of this SNAP board
                temp (float)     : Reported FPGA temperature (degrees C)
                uptime (int)     : Multiples of 500e6 ADC clocks since last
                                   programming cycle
                last_programmed (datetime) : Last time this FPGA was programmed
                timestamp (datetime) : Asynchronous timestamp that these status
                                       entries were gathered

                Unknown values return the string "None"

    """
    import hera_corr_cm

    if corr_cm is None:
        corr_cm = hera_corr_cm.HeraCorrCM(redishost=redishost)

    return corr_cm.get_f_status()


class SNAPFengInitStatus(MCDeclarativeBase):
    """
    Definition of snap_feng_init_status table.

    Attributes
    ----------
    time : BigInteger Column
        GPS time that the when the snap state was logged, floored. Part of the primary
        key.
    hostname : String Column
        SNAP hostname. Part of primary_key.
    status : String Column
        Feng init status of the SNAP. Should be one of "working" (hera_corr_f thinks it
        works), "unconfig" (snap made it to arming, but weren't configured, so don't
        work), "maxout" (snap made it all the way through arming and configuring but
        was ignored because there were too many snaps).

    """

    __tablename__ = "snap_feng_init_status"
    time = Column(BigInteger, primary_key=True)
    hostname = Column(String, primary_key=True)
    status = Column(String, nullable=False)

    @classmethod
    def create(cls, time, hostname, status):
        """
        Create a new correlator config status object.

        Parameters
        ----------
        time : astropy Time object
            Astropy time object based on a timestamp reported by the correlator.
        hostname : str
            SNAP hostname.
        status : str
            Feng init status of the SNAP. Should be one of "working" (hera_corr_f
            thinks it works), "unconfig" (snap made it to arming, but weren't
            configured, so don't work), "maxout" (snap made it all the way through
            arming and configuring but was ignored because there were too many snaps).

        """
        if not isinstance(time, Time):
            raise ValueError("time must be an astropy Time object")
        log_time = floor(time.gps)

        return cls(time=log_time, hostname=hostname, status=status)


def _get_snap_feng_init_status_from_redis(
    redishost=DEFAULT_REDIS_ADDRESS, snap_config_dict=None
):
    """
    Get the SNAP feng init status from redis.

    Parameters
    ----------
    redishost : str
        Address of redis database
    snap_config_dict : dict
        Dict matching what comes out of redis for testing.

    Returns
    -------
    log_time : astropy Time object
        Time of log (log_time_stop).
    snap_feng_status : dict
        keys are snap hostnames, values are status. Status should be one of "working"
        (hera_corr_f thinks it works), "unconfig" (snap made it to arming, but weren't
        configured, so don't work), "maxout" (snap made it all the way through
        arming and configuring but was ignored because there were too many snaps).

    """
    if snap_config_dict is None:
        redis_pool = redis.ConnectionPool(host=redishost, decode_responses=True)
        rsession = redis.Redis(connection_pool=redis_pool, charset="utf-8")

        snap_config_dict = rsession.hgetall("snap_log")
        # These keys are:
        #  - log_time_start (timestamp) time of log start
        #  - log_time_stop (timestamp) time of log stop
        #  - timestamp (timestamp) time when this info was written to redis
        #  - working (str) csv list of the snap hostnames that hera_corr_f thinks work
        #  - unconfig (str) csv list of the snap hostnames that made it to arming,
        #      but weren't configured (so don't work)
        #  - maxout (str)  csv list of the snap hostnames that made it all the way, but
        #      were ignored because we had too many snaps
        # other statuses may be added, will similarly have csv lists of snap hostnames

    log_time_str = snap_config_dict["log_time_stop"]
    if log_time_str == "Not found":
        return None, {}
    try:
        log_time = Time(log_time_str, scale="utc")
    except ValueError:
        return None, {}

    snap_feng_status = {}
    for key in snap_config_dict:
        key_str = key
        if "time" in key_str:
            continue
        if snap_config_dict[key] == "":
            continue
        if "heraNode" not in snap_config_dict[key]:
            warnings.warn(
                f"Unexpected key in redis `snap_log` key: {key}, some info may be lost"
            )
            continue
        for hostname in snap_config_dict[key].split(","):
            snap_feng_status[hostname] = key_str

    return log_time, snap_feng_status


class AntennaStatus(MCDeclarativeBase):
    """
    Definition of antenna status table (based on SNAP info).

    Attributes
    ----------
    time : BigInteger Column
        GPS time of the antenna status data, floored. Part of primary_key.
    antenna_number : Integer Column
        Antenna number. Part of primary_key.
    antenna_feed_pol : String Column
        Feed polarization, either 'e' or 'n'. Part of primary_key.
    snap_hostname : String Column
        SNAP hostname.
    snap_channel_number : Integer Column
        The SNAP ADC channel number (0-5) to which this antenna is connected.
    adc_mean : Float Column
        Mean ADC value, in ADC units.
    adc_rms : Float Column
        RMS ADC value, in ADC units.
    adc_power : Float Column
        Mean ADC power, in ADC units squared.
    pam_atten : Integer Column
        PAM attenuation setting for this antenna, in dB. (Integer)
    pam_power : Float Column
        PAM power sensor reading for this antenna, in dBm.
    pam_voltage : Float Column
        PAM voltage sensor reading for this antenna, in Volts.
    pam_current : Float Column
        PAM current sensor reading for this antenna, in Amps.
    pam_id : String Column
        Serial number of this PAM.
    fem_voltage : Float Column
        FEM voltage sensor reading for this antenna, in Volts.
    fem_current : Float Column
        FEM current sensor reading for this antenna, in Amps.
    fem_id : String Column
        Serial number of this FEM.
    fem_switch : String Column
        Switch state for this FEM. Options are: {'antenna', 'load', 'noise'}
    fem_lna_power : Boolean Column
        Power state of this FEM (True if powered).
    fem_imu_theta : Float Column
        IMU-reported theta, in degrees.
    fem_imu_phi : Float Column
        IMU-reported phi, in degrees.
    fem_temp : Float Column
        EM temperature sensor reading for this antenna in degrees Celsius.
    fft_overflow : Boolean Column
        Indicator of an FFT overflow, True if there was an FFT overflow.
    eq_coeffs : String Column
        Digital EQ coefficients for this antenna, list of floats stored as a
        string.
    histogram : String Column
        ADC histogram counts, list of ints stored as a string.

    """

    __tablename__ = "antenna_status"
    time = Column(BigInteger, primary_key=True)
    antenna_number = Column(Integer, primary_key=True)
    antenna_feed_pol = Column(String, primary_key=True)
    snap_hostname = Column(String)
    snap_channel_number = Column(Integer)
    adc_mean = Column(Float)
    adc_rms = Column(Float)
    adc_power = Column(Float)
    pam_atten = Column(Integer)
    pam_power = Column(Float)
    pam_voltage = Column(Float)
    pam_current = Column(Float)
    pam_id = Column(String)
    fem_voltage = Column(Float)
    fem_current = Column(Float)
    fem_id = Column(String)
    fem_switch = Column(String)
    fem_lna_power = Column(Boolean)
    fem_imu_theta = Column(Float)
    fem_imu_phi = Column(Float)
    fem_temp = Column(Float)
    fft_overflow = Column(Boolean)
    eq_coeffs = Column(String)
    histogram = Column(String)

    @classmethod
    def create(
        cls,
        time,
        antenna_number,
        antenna_feed_pol,
        snap_hostname,
        snap_channel_number,
        adc_mean,
        adc_rms,
        adc_power,
        pam_atten,
        pam_power,
        pam_voltage,
        pam_current,
        pam_id,
        fem_voltage,
        fem_current,
        fem_id,
        fem_switch,
        fem_lna_power,
        fem_imu_theta,
        fem_imu_phi,
        fem_temp,
        fft_overflow,
        eq_coeffs,
        histogram,
    ):
        """
        Create a new antenna status object.

        Parameters
        ----------
        time : astropy time object
            Astropy time object based on a timestamp reported by node.
        antenna_number : int
            Antenna number.
        antenna_feed_pol : str
            Feed polarization, either 'e' or 'n'.
        snap_hostname : str
            Hostname of snap the antenna is connected to.
        snap_channel_number : int
            The SNAP ADC channel number (0-5) that this antenna is connected
            to.
        adc_mean : float
            Mean ADC value, in ADC units, meaning raw ADC values interpreted as
            signed integers between -128 and +127. Typically ~ -0.5.
        adc_rms : float
            RMS ADC value, in ADC units, meaning raw ADC values interpreted as
            signed integers between -128 and +127.  Should be ~ 10-20.
        adc_power : float
            Mean ADC power, in ADC units squared, meaning raw ADC values
            interpreted as signed integers between -128 and +127 and then
            squared. Since mean should be close to zero, this should just be
            adc_rms^2.
        pam_atten : int
            PAM attenuation setting for this antenna, in dB.
        pam_power : float
            PAM power sensor reading for this antenna, in dBm.
        pam_voltage : float
            PAM voltage sensor reading for this antenna, in Volts.
        pam_current : float
            PAM current sensor reading for this antenna, in Amps.
        pam_id : str
            Serial number of this PAM.
        fem_voltage : float
            FEM voltage sensor reading for this antenna, in Volts.
        fem_current : float
            FEM current sensor reading for this antenna, in Amps.
        fem_id : str
            Serial number of this FEM.
        fem_switch : {'antenna', 'load', 'noise'}
            Switch state for this FEM.
        fem_lna_power : bool
            Power state of this FEM (True if powered).
        fem_imu_theta : float
            IMU-reported theta, in degrees.
        fem_imu_phi : float
            IMU-reported phi, in degrees.
        fem_temp : float
            EM temperature sensor reading for this antenna in degrees Celsius.
        fft_overflow : bool
            Indicator of an FFT overflow, True if there was an FFT overflow.
        eq_coeffs : list of float
            Digital EQ coefficients, used for keeping the bit occupancy in the
            correct range, for this antenna, list of floats. Note this these
            are not divided out anywhere in the DSP chain (!).
        histogram : list of int
            ADC histogram counts.

        """
        if not isinstance(time, Time):
            raise ValueError("time must be an astropy Time object")
        snap_time = floor(time.gps)

        if antenna_feed_pol not in ["e", "n"]:
            raise ValueError('antenna_feed_pol must be "e" or "n".')

        if fem_switch is not None and fem_switch not in ["antenna", "load", "noise"]:
            raise ValueError('fem_switch must be "antenna", "load", "noise"')

        if eq_coeffs is not None:
            eq_coeffs_str = [str(val) for val in eq_coeffs]
            eq_coeffs_string = "[" + ",".join(eq_coeffs_str) + "]"
        else:
            eq_coeffs_string = None

        if histogram is not None:
            histogram_string = [str(val) for val in histogram]
            histogram_string = "[" + ",".join(histogram_string) + "]"
        else:
            histogram_string = None

        return cls(
            time=snap_time,
            antenna_number=antenna_number,
            antenna_feed_pol=antenna_feed_pol,
            snap_hostname=snap_hostname,
            snap_channel_number=snap_channel_number,
            adc_mean=adc_mean,
            adc_rms=adc_rms,
            adc_power=adc_power,
            pam_atten=pam_atten,
            pam_power=pam_power,
            pam_voltage=pam_voltage,
            pam_current=pam_current,
            pam_id=pam_id,
            fem_voltage=fem_voltage,
            fem_current=fem_current,
            fem_id=fem_id,
            fem_switch=fem_switch,
            fem_lna_power=fem_lna_power,
            fem_imu_theta=fem_imu_theta,
            fem_imu_phi=fem_imu_phi,
            fem_temp=fem_temp,
            fft_overflow=fft_overflow,
            eq_coeffs=eq_coeffs_string,
            histogram=histogram_string,
        )


def _get_ant_status(corr_cm=None, redishost=DEFAULT_REDIS_ADDRESS):
    """
    Get the antenna status dict from the correlator.

    Parameters
    ----------
    corr_cm : hera_corr_cm.HeraCorrCM object
        HeraCorrCM object to use. If None, this function will make a new one.
    correlator_redis_address : str
        Address of redis database (only used if corr_cm is None)

    Returns
    -------
    dict
        from hera_corr_cm docstring:
        Returns a dictionary of antenna status flags. Keys of returned
        dictionaries are of the form "<antenna number>:"<e|n>". Values of
        this dictionary are status key/val pairs.

        These keys are:
            adc_mean (float)  : Mean ADC value (in ADC units)
            adc_rms (float)   : RMS ADC value (in ADC units)
            adc_power (float) : Mean ADC power (in ADC units squared)
            f_host (str)      : The hostname of the SNAP board to which
                                this antenna is connected
            host_ant_id (int) : The SNAP ADC channel number (0-5) to which
                                this antenna is connected
            pam_atten (int)   : PAM attenuation setting for this antenna (dB)
            pam_power (float) : PAM power sensor reading for this antenna (dBm)
            pam_voltage (float)   : PAM voltage sensor reading for this
                                    antenna (V)
            pam_current (float)   : PAM current sensor reading for this
                                    antenna (A)
            pam_id (list of ints) : Bytewise serial number of this PAM
            fem_voltage (float)   : FEM voltage sensor reading for this
                                    antenna (V)
            fem_current (float)   : FEM current sensor reading for this
                                    antenna (A)
            fem_id (list)         : Bytewise serial number of this FEM
            fem_switch(str)       : Switch state for this FEM ('antenna',
                                    'load', or 'noise')
            fem_lna_power(bool)   : True if LNA is powered
            fem_imu_theta (float) : IMU-reported theta (degrees)
            fem_imu_phi (float)   : IMU-reported phi (degrees)
            fem_temp (float)      : FEM temperature sensor reading for this
                                    antenna (C)
            fft_of (bool)         : True if there was an FFT overflow
            eq_coeffs (list of floats) : Digital EQ coefficients for this
                                         antenna
            histogram (list of ints) : Two-dimensional list:
                                       [[bin_centers][counts]] representing ADC
                                       histogram
            timestamp (datetime) : Asynchronous timestamp that these status
            entries were gathered

            Unknown values return the string "None"

    """
    import hera_corr_cm

    if corr_cm is None:
        corr_cm = hera_corr_cm.HeraCorrCM(redishost=redishost)

    return corr_cm.get_ant_status()


def _pam_fem_id_to_string(idno):
    """
    Convert the id number to a string.

    Parameters
    ----------
    idno : str
        value from hera_corr_f id function via redis

    Returns
    -------
    str
        decoded id number

    """
    if isinstance(idno, list):
        return ":".join([str(x) for x in idno])
    try:
        val = json.loads(idno)
        if isinstance(val, list):
            return ":".join([str(x) for x in val])
        else:
            retval = str(idno)
    except (TypeError, json.JSONDecodeError):
        retval = str(idno)

    if not len(retval) or retval.lower() == "none" or retval.lower() == "null":
        return None
    return retval


def create_antenna_status(
    corr_cm=None, redishost=DEFAULT_REDIS_ADDRESS, ant_status_dict=None
):
    """
    Return a list of antenna status objects with data from the correlator.

    Parameters
    ----------
    correlator_redis_address: Address of server where the correlator redis
        database can be accessed.
    ant_status_dict: A dict spoofing the return dict from _get_ant_status for
        testing purposes.

    Returns
    -------
    list of AntennaStatus objects

    """
    if ant_status_dict is None:
        ant_status_dict = _get_ant_status(corr_cm=corr_cm, redishost=redishost)

    ant_status_list = []
    for antkey, ant_dict in ant_status_dict.items():
        antenna_number, antenna_feed_pol = tuple(antkey.split(":"))
        antenna_number = int(antenna_number)

        time = Time(ant_dict["timestamp"], format="datetime")

        # any entry other than timestamp can be the string 'None'
        # need to convert those to a None type
        for key, val in ant_dict.items():
            if (isinstance(val, str) and val == "None") or (
                isinstance(val, float) and np.isnan(val)
            ):
                ant_dict[key] = None

        snap_hostname = ant_dict["f_host"]
        snap_channel_number = ant_dict["host_ant_id"]
        adc_mean = ant_dict["adc_mean"]
        adc_rms = ant_dict["adc_rms"]
        if ant_dict["adc_power"] is not None:
            adc_power = float(ant_dict["adc_power"])
        else:
            adc_power = None
        pam_atten = ant_dict["pam_atten"]
        pam_power = ant_dict["pam_power"]
        pam_voltage = ant_dict["pam_voltage"]
        pam_current = ant_dict["pam_current"]
        pam_id = _pam_fem_id_to_string(ant_dict["pam_id"])
        fem_voltage = ant_dict["fem_voltage"]
        fem_current = ant_dict["fem_current"]
        fem_id = _pam_fem_id_to_string(ant_dict["fem_id"])
        fem_switch = ant_dict["fem_switch"]
        if fem_switch is not None and fem_switch not in ["antenna", "load", "noise"]:
            warnings.warn(
                "fem_switch value is {}, should be one of: "
                '"antenna", "load", "noise" or "None". '
                "Setting to None.".format(fem_switch)
            )
            fem_switch = None

        fem_lna_power = ant_dict["fem_lna_power"]
        fem_imu_theta = ant_dict["fem_imu_theta"]
        fem_imu_phi = ant_dict["fem_imu_phi"]
        fem_temp = ant_dict["fem_temp"]
        fft_overflow = ant_dict["fft_of"]
        eq_coeffs = ant_dict["eq_coeffs"]
        histogram = ant_dict["histogram"]

        ant_status_list.append(
            AntennaStatus.create(
                time,
                antenna_number,
                antenna_feed_pol,
                snap_hostname,
                snap_channel_number,
                adc_mean,
                adc_rms,
                adc_power,
                pam_atten,
                pam_power,
                pam_voltage,
                pam_current,
                pam_id,
                fem_voltage,
                fem_current,
                fem_id,
                fem_switch,
                fem_lna_power,
                fem_imu_theta,
                fem_imu_phi,
                fem_temp,
                fft_overflow,
                eq_coeffs,
                histogram,
            )
        )

    return ant_status_list
