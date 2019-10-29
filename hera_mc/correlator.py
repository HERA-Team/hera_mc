# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Correlator M&C interface.

Anything tracked in the correlator redis database and accessed via hera_corr_cm.
Includes many SNAP-related things.
"""
from __future__ import absolute_import, division, print_function

import six
from math import floor
import numpy as np
from astropy.time import Time
from sqlalchemy import (Column, BigInteger, Integer, Float, Boolean, String,
                        ForeignKey, ForeignKeyConstraint)

from . import MCDeclarativeBase

# default acclen -- corresponds to a bit under 10 seconds (~9.66 seconds)
DEFAULT_ACCLEN_SPECTRA = 147456

DEFAULT_REDIS_ADDRESS = "redishost"

# key is state type, value is method name in hera_corr_cm
state_dict = {'taking_data': 'is_recording',
              'phase_switching': 'phase_switch_is_on',
              'noise_diode': 'noise_diode_is_on'}

tag_list = ['science', 'engineering']

# key is command, value is method name in hera_corr_cm
command_dict = {'take_data': 'take_data',
                'stop_taking_data': 'stop_taking_data',
                'phase_switching_on': 'phase_switch_enable',
                'phase_switching_off': 'phase_switch_disable',
                'noise_diode_on': 'noise_diode_enable',
                'noise_diode_off': 'noise_diode_disable',
                'update_config': 'update_config', 'restart': 'restart'}

command_state_map = {'take_data': {'allowed_when_recording': False},
                     'stop_taking_data': {'state_type': 'taking_data',
                                          'state': False,
                                          'allowed_when_recording': True},
                     'phase_switching_on': {'state_type': 'phase_switching',
                                            'state': True,
                                            'allowed_when_recording': False},
                     'phase_switching_off': {'state_type': 'phase_switching',
                                             'state': False,
                                             'allowed_when_recording': False},
                     'noise_diode_on': {'state_type': 'noise_diode',
                                        'state': True,
                                        'allowed_when_recording': False},
                     'noise_diode_off': {'state_type': 'noise_diode',
                                         'state': False,
                                         'allowed_when_recording': False},
                     'update_config': {'allowed_when_recording': True},
                     'restart': {'allowed_when_recording': False}}


class CorrelatorControlState(MCDeclarativeBase):
    """
    Definition of correlator control state table.

    Attributes
    ----------
    time : BigInteger Column
        GPS time of the control state, floored. Part of the primary key.
    state_type : String Column
        Type of control state, one of the keys in state_dict. Part of the
        primary key.
    state : Boolean Column
        Boolean indicating whether the state_type is true or false.

    """

    __tablename__ = 'correlator_control_state'
    time = Column(BigInteger, primary_key=True)
    state_type = Column(String, primary_key=True)
    state = Column(Boolean, nullable=False)

    @classmethod
    def create(cls, time, state_type, state):
        """
        Create a new correlator control state object.

        Parameters
        ------------
        time : astropy Time object
            Astropy time object based on a timestamp reported by the correlator.
        state_type : str
            Must be a key in state_dict (e.g. 'taking_data', 'phase_switching',
            'noise_diode').
        state : bool
            Is the state_type true or false.

        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        corr_time = floor(time.gps)

        if state_type not in list(state_dict.keys()):
            raise ValueError('state_type must be one of: '
                             + ', '.join(list(state_dict.keys()))
                             + '. state_type is actually {}'.format(state_type))

        return cls(time=corr_time, state_type=state_type, state=state)


def _get_control_state(corr_cm=None,
                       correlator_redis_address=DEFAULT_REDIS_ADDRESS):
    """
    Get the latest states and associated timestamp from the correlator.

    Parameters
    ---------
    corr_cm : hera_corr_cm.HeraCorrCM object
        HeraCorrCM object to use. If None, this function will make a new one.
    correlator_redis_address : str
        Address of redis database (only used if corr_cm is None).

    Returns
    -------
    dict
        a 2-level dict, top level key is a key from the state_dict,
        second level keys are 'timestamp' and 'state' (a boolean)

    """
    import hera_corr_cm

    if corr_cm is None:
        corr_cm = hera_corr_cm.HeraCorrCM(redishost=correlator_redis_address)

    corr_state_dict = {}
    for key, value in six.iteritems(state_dict):
        # call each state query method and add to corr_state_dict
        state, timestamp = getattr(corr_cm, value)()
        corr_state_dict[key] = {'timestamp': timestamp, 'state': state}

    return corr_state_dict


class CorrelatorConfigFile(MCDeclarativeBase):
    """
    Definition of correlator_config_file table.

    Attributes
    ----------
    hash : String Column
        Unique hash for the config. The primary key.
    filename : String Column
        Name of the config file in the Librarian.

    """

    __tablename__ = 'correlator_config_file'
    config_hash = Column(String, primary_key=True)
    filename = Column(String, nullable=False)

    @classmethod
    def create(cls, config_hash, filename):
        """
        Create a new correlator config file object.

        Parameters
        ------------
        config_hash : str
            unique hash of the config
        filename : str
            name of the config file in the Librarian

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
        Unique hash for the config. Foreign key into correlator_config_file.

    """

    __tablename__ = 'correlator_config_status'
    time = Column(BigInteger, primary_key=True)
    config_hash = Column(String,
                         ForeignKey("correlator_config_file.config_hash"),
                         nullable=False)

    @classmethod
    def create(cls, time, config_hash):
        """
        Create a new correlator config status object.

        Parameters
        ------------
        time : astropy Time object
            Astropy time object based on a timestamp reported by the correlator.
        config_hash : str
            Unique hash for the config. Foreign key into correlator_config_file.

        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        corr_time = floor(time.gps)

        return cls(time=corr_time, config_hash=config_hash)


def _get_config(corr_cm=None, correlator_redis_address=DEFAULT_REDIS_ADDRESS):
    """
    Get the latest config, hash and associated timestamp from the correlator.

    Parameters
    ---------
    corr_cm : hera_corr_cm.HeraCorrCM object
        HeraCorrCM object to use. If None, this function will make a new one.
    correlator_redis_address : str
        Address of redis database (only used if corr_cm is None)

    Returns
    -------
    dict
        Keys are 'timestamp', 'hash' and 'config' (a yaml processed string)

    """
    import hera_corr_cm

    if corr_cm is None:
        corr_cm = hera_corr_cm.HeraCorrCM(redishost=correlator_redis_address)

    timestamp, config, hash = corr_cm.get_config()
    time = Time(timestamp, format='unix')

    return {'time': time, 'hash': hash, 'config': config}


class CorrelatorControlCommand(MCDeclarativeBase):
    """
    Definition of correlator control command table.

    Attributes
    ----------
    time : BigInteger Column
        GPS time of the command, floored. Part of primary_key.
    command : String Column
        Control command, one of the keys in command_dict. Part of primary_key.

    """

    __tablename__ = 'correlator_control_command'
    time = Column(BigInteger, primary_key=True)
    command = Column(String, primary_key=True)

    @classmethod
    def create(cls, time, command):
        """
        Create a new correlator control command object.

        Parameters
        ------------
        time : astropy Time object
            Astropy time object for time command was sent.
        command : str
            One of the keys in command_dict (e.g. 'take_data',
            'phase_switching_on', 'phase_switching_off', 'restart')

        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        corr_time = floor(time.gps)

        if command not in list(command_dict.keys()):
            raise ValueError('command must be one of: '
                             + ', '.join(list(command_dict.keys()))
                             + '. command is actually {}'.format(command))

        return cls(time=corr_time, command=command)


def _get_integration_time(acclen_spectra, corr_cm=None,
                          correlator_redis_address=DEFAULT_REDIS_ADDRESS):
    """
    Get the integration time in seconds for a given acclen in spectra.

    Parameters
    ---------
    acclen_spectra : int
        Accumulation length in number of spectra.
    corr_cm : hera_corr_cm.HeraCorrCM object
        HeraCorrCM object to use. If None, this function will make a new one.
    correlator_redis_address : str
        Address of redis database (only used if corr_cm is None)

    Returns
    -------
    float
        integration time in seconds

    """
    import hera_corr_cm

    if corr_cm is None:
        corr_cm = hera_corr_cm.HeraCorrCM(redishost=correlator_redis_address)

    return corr_cm.n_spectra_to_secs(acclen_spectra)


def _get_next_start_time(corr_cm=None,
                         correlator_redis_address=DEFAULT_REDIS_ADDRESS):
    """
    Get the next start time from the correlator, in gps seconds.

    Parameters
    ---------
    corr_cm : hera_corr_cm.HeraCorrCM object
        HeraCorrCM object to use. If None, this function will make a new one.
    correlator_redis_address : str
        Address of redis database (only used if corr_cm is None).

    Returns
    -------
    astropy Time object
        Time of the next start time

    """
    import hera_corr_cm

    if corr_cm is None:
        corr_cm = hera_corr_cm.HeraCorrCM(redishost=correlator_redis_address)

    starttime_unix_timestamp = corr_cm.next_start_time()
    if starttime_unix_timestamp == 0.0:
        return None

    return Time(starttime_unix_timestamp, format='unix').gps


class CorrelatorTakeDataArguments(MCDeclarativeBase):
    """
    Definition of correlator take_data arguments table.

    Records the arguments passed to the correlator `take_data` command.

    Attributes
    ----------
    time : BigInteger Column
        GPS time of the take_datacommand, floored. Part of primary_key.
    command : String Column
        Always equal to 'take_data'. Part of primary_key.
    starttime_sec : BigInteger Column
        GPS time to start taking data, floored.
    starttime_ms : Integer Column
        Milliseconds to add to starttime_sec to set correlator start time.
    duration : Float Column
        Duration to take data for in seconds. After this time, the
        correlator will stop recording.
    acclen_spectra : Integer Column
        Accumulation length in spectra.
    integration_time :  Float Column
        Accumulation length in seconds, converted from acclen_spectra.
        The conversion is non-trivial and depends on the correlator settings.
    tag : String Column
        Tag which will end up in data files as a header entry. Must be one of
        the values in tag_list.

    """

    __tablename__ = 'correlator_take_data_arguments'
    time = Column(BigInteger, primary_key=True)
    command = Column(String, primary_key=True)
    starttime_sec = Column(BigInteger, nullable=False)
    starttime_ms = Column(Integer, nullable=False)
    duration = Column(Float, nullable=False)
    acclen_spectra = Column(Integer, nullable=False)
    integration_time = Column(Float, nullable=False)
    tag = Column(String, nullable=False)

    # the command column isn't really needed to define the table (it's always
    # 'take_data'), but it's required for the Foreign key to work properly
    __table_args__ = (ForeignKeyConstraint(
        ['time', 'command'], ['correlator_control_command.time',
                              'correlator_control_command.command']), {})

    @classmethod
    def create(cls, time, starttime, duration, acclen_spectra, integration_time,
               tag):
        """
        Create a new correlator take data arguments object.

        Parameters
        ------------
        time : astropy Time object
            Astropy time object for time the take_data command was sent.
        starttime : astropy Time object
            Astropy time object for time to start taking data.
        duration : float
            Duration to take data for in seconds. After this time, the
            correlator will stop recording.
        acclen_spectra : int
            Accumulation length in spectra.
        integration_time : float
            Integration time in seconds, converted from acclen_spectra.
        tag : str
            Tag which will end up in data files as a header entry.
            Must be one of the values in tag_list.

        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        corr_time = floor(time.gps)

        if not isinstance(starttime, Time):
            raise ValueError('starttime must be an astropy Time object')
        starttime_gps = starttime.gps
        starttime_sec = floor(starttime_gps)

        starttime_ms = floor((starttime_gps - starttime_sec) * 1000.)

        if tag not in tag_list:
            raise ValueError('tag must be one of: ', tag_list)

        return cls(time=corr_time, command='take_data',
                   starttime_sec=starttime_sec,
                   starttime_ms=starttime_ms, duration=duration,
                   acclen_spectra=acclen_spectra,
                   integration_time=integration_time,
                   tag=tag)


class CorrelatorConfigCommand(MCDeclarativeBase):
    """
    Definition of correlator_config_command, for correlator config changes.

    Attributes
    ----------
    time : BigInteger Column
        GPS time that the config command was sent, floored. Part of primary_key.
    command : String Column
        Always equal to 'update_config'. Part of primary_key.
    config_hash : String Column
        Unique hash for the config. Foreign key into correlator_config_file.

    """

    __tablename__ = 'correlator_config_command'
    time = Column(BigInteger, primary_key=True)
    command = Column(String, primary_key=True)
    config_hash = Column(String,
                         ForeignKey("correlator_config_file.config_hash"),
                         nullable=False)

    # the command column isn't really needed to define the table (it's always
    # 'update_config'), but it's required for the Foreign key to work properly
    __table_args__ = (ForeignKeyConstraint(
        ['time', 'command'], ['correlator_control_command.time',
                              'correlator_control_command.command']), {})

    @classmethod
    def create(cls, time, config_hash):
        """
        Create a new correlator config command object.

        Parameters
        ------------
        time : astropy time object
            Astropy time object based on a timestamp reported by the correlator
        config_hash : str
            Unique hash of the config. Foreign key into correlator_config_file
            table.

        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        command_time = floor(time.gps)

        return cls(time=command_time, command='update_config',
                   config_hash=config_hash)


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

    __tablename__ = 'correlator_software_versions'
    time = Column(BigInteger, primary_key=True)
    package = Column(String, primary_key=True)
    version = Column(String, nullable=False)

    @classmethod
    def create(cls, time, package, version):
        """
        Create a new correlator software versions object.

        Parameters
        ------------
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
            raise ValueError('time must be an astropy Time object')
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

    __tablename__ = 'snap_config_version'
    init_time = Column(BigInteger, primary_key=True)
    version = Column(String, nullable=False)
    init_args = Column(String, nullable=False)
    config_hash = Column(String,
                         ForeignKey("correlator_config_file.config_hash"),
                         nullable=False)

    @classmethod
    def create(cls, init_time, version, init_args, config_hash):
        """
        Create a new SNAP configuration and version object.

        Parameters
        ------------
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
            raise ValueError('init_time must be an astropy Time object')
        init_time_gps = floor(init_time.gps)

        return cls(init_time=init_time_gps, version=version,
                   init_args=init_args, config_hash=config_hash)


def _get_corr_versions(corr_cm=None,
                       correlator_redis_address=DEFAULT_REDIS_ADDRESS):
    """
    Get the versions dict from the correlator.

    Parameters
    ---------
    corr_cm : hera_corr_cm.HeraCorrCM object
        HeraCorrCM object to use. If None, this function will make a new one.
    correlator_redis_address : str
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
        corr_cm = hera_corr_cm.HeraCorrCM(redishost=correlator_redis_address)

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

    """

    __tablename__ = 'snap_status'
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

    @classmethod
    def create(cls, time, hostname, node, snap_loc_num, serial_number,
               psu_alert, pps_count, fpga_temp, uptime_cycles,
               last_programmed_time):
        """
        Create a new SNAP status object.

        Parameters
        ------------
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

        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        snap_time = floor(time.gps)

        if last_programmed_time is not None:
            if not isinstance(last_programmed_time, Time):
                raise ValueError('last_programmed_time must be an astropy '
                                 'Time object')
            last_programmed_time_gps = floor(last_programmed_time.gps)
        else:
            last_programmed_time_gps = None

        return cls(time=snap_time, hostname=hostname, node=node,
                   snap_loc_num=snap_loc_num,
                   serial_number=serial_number, psu_alert=psu_alert,
                   pps_count=pps_count, fpga_temp=fpga_temp,
                   uptime_cycles=uptime_cycles,
                   last_programmed_time=last_programmed_time_gps)


def _get_snap_status(corr_cm=None,
                     correlator_redis_address=DEFAULT_REDIS_ADDRESS):
    """
    Get the snap status dict from the correlator.

    Parameters
    ---------
    corr_cm : hera_corr_cm.HeraCorrCM object
        HeraCorrCM object to use. If None, this function will make a new one.
    correlator_redis_address : str
        Address of redis database (only used if corr_cm is None)

    Returns
    -------
    dict
        from hera_corr_cm docstring:
            Returns a dictionary of snap status flags. Keys of returned
            dictionaries are snap hostnames. Values of this dictionary are
            status key/val pairs.

            These keys are:
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
        corr_cm = hera_corr_cm.HeraCorrCM(redishost=correlator_redis_address)

    return corr_cm.get_f_status()


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
        The SNAP ADC channel number (0-7) to which this antenna is connected.
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
    fem_temp : Float Column
        EM temperature sensor reading for this antenna in degrees Celsius.
    eq_coeffs : String Column
        Digital EQ coefficients for this antenna, list of floats stored as a
        string.
    histogram_bin_centers : String Column
        ADC histogram bin centers, list of ints stored as a string.
    histogram : String Column
        ADC histogram counts, list of ints stored as a string.

    """

    __tablename__ = 'antenna_status'
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
    fem_temp = Column(Float)
    eq_coeffs = Column(String)
    histogram_bin_centers = Column(String)
    histogram = Column(String)

    @classmethod
    def create(cls, time, antenna_number, antenna_feed_pol, snap_hostname,
               snap_channel_number, adc_mean, adc_rms, adc_power, pam_atten,
               pam_power, pam_voltage, pam_current, pam_id, fem_voltage,
               fem_current, fem_id, fem_temp, eq_coeffs, histogram_bin_centers,
               histogram):
        """
        Create a new antenna status object.

        Parameters
        ------------
        time : astropy time object
            Astropy time object based on a timestamp reported by node.
        antenna_number : int
            Antenna number.
        antenna_feed_pol : str
            Feed polarization, either 'e' or 'n'.
        snap_hostname : str
            Hostname of snap the antenna is connected to.
        snap_channel_number : int
            The SNAP ADC channel number (0-7) that this antenna is connected to.
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
            Serial number of this FEM
        fem_temp : float
            EM temperature sensor reading for this antenna in degrees Celsius.
        eq_coeffs : list of float
            Digital EQ coefficients, used for keeping the bit occupancy in the
            correct range, for this antenna, list of floats. Note this these are
            not divided out anywhere in the DSP chain (!).
        histogram_bin_centers : list of int
            ADC histogram bin centers.
        histogram : list of int
            ADC histogram counts.

        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        snap_time = floor(time.gps)

        if antenna_feed_pol not in ['e', 'n']:
            raise ValueError('antenna_feed_pol must be "e" or "n".')

        if eq_coeffs is not None:
            eq_coeffs_str = [str(val) for val in eq_coeffs]
            eq_coeffs_string = '[' + ','.join(eq_coeffs_str) + ']'
        else:
            eq_coeffs_string = None

        if histogram_bin_centers is not None:
            histogram_bin_string = [str(val) for val in histogram_bin_centers]
            histogram_bin_string = '[' + ','.join(histogram_bin_string) + ']'
        else:
            histogram_bin_string = None

        if histogram is not None:
            histogram_string = [str(val) for val in histogram]
            histogram_string = '[' + ','.join(histogram_string) + ']'
        else:
            histogram_string = None

        return cls(time=snap_time, antenna_number=antenna_number,
                   antenna_feed_pol=antenna_feed_pol,
                   snap_hostname=snap_hostname,
                   snap_channel_number=snap_channel_number, adc_mean=adc_mean,
                   adc_rms=adc_rms, adc_power=adc_power, pam_atten=pam_atten,
                   pam_power=pam_power, pam_voltage=pam_voltage,
                   pam_current=pam_current, pam_id=pam_id,
                   fem_voltage=fem_voltage, fem_current=fem_current,
                   fem_id=fem_id, fem_temp=fem_temp,
                   eq_coeffs=eq_coeffs_string,
                   histogram_bin_centers=histogram_bin_string,
                   histogram=histogram_string)


def _get_ant_status(corr_cm=None,
                    correlator_redis_address=DEFAULT_REDIS_ADDRESS):
    """
    Get the antenna status dict from the correlator.

    Parameters
    ---------
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
            host_ant_id (int) : The SNAP ADC channel number (0-7) to which
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
            fem_temp (float)      : FEM temperature sensor reading for this
                                    antenna (C)
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
        corr_cm = hera_corr_cm.HeraCorrCM(redishost=correlator_redis_address)

    return corr_cm.get_ant_status()


def _pam_fem_serial_list_to_string(serial_number_list):
    """
    Convert the native FEM/PAM Bytewise serial number to a string.

    Parameters
    ----------
    serial_number_list : list of ints
        Bytewise serial number of a FEM or PAM

    Returns
    -------
    str
        decoded string serial number

    """
    try:
        serial_str = ''
        for int_val in serial_number_list:
            hex_val = hex(int_val)[2:]
            # str_val = bytes.fromhex(hex_val).decode('ascii')
            str_val = hex_val
            serial_str += str_val

        return serial_str
    except Exception:
        return None


def create_antenna_status(corr_cm=None,
                          correlator_redis_address=DEFAULT_REDIS_ADDRESS,
                          ant_status_dict=None):
    """
    Return a list of antenna status objects with data from the correlator.

    Parameters
    ------------
    correlator_redis_address: Address of server where the correlator redis
        database can be accessed.
    ant_status_dict: A dict spoofing the return dict from _get_ant_status for
        testing purposes.

    Returns
    -----------
    list of AntennaStatus objects

    """
    if ant_status_dict is None:
        ant_status_dict = _get_ant_status(
            corr_cm=corr_cm, correlator_redis_address=correlator_redis_address)

    ant_status_list = []
    for antkey, ant_dict in six.iteritems(ant_status_dict):
        antenna_number, antenna_feed_pol = tuple(antkey.split(':'))
        antenna_number = int(antenna_number)

        time = Time(ant_dict['timestamp'], format='datetime')

        # any entry other than timestamp can be the string 'None'
        # need to convert those to a None type
        for key, val in six.iteritems(ant_dict):
            if val == 'None' or (isinstance(val, float) and np.isnan(val)):
                ant_dict[key] = None

        snap_hostname = ant_dict['f_host']
        snap_channel_number = ant_dict['host_ant_id']
        adc_mean = ant_dict['adc_mean']
        adc_rms = ant_dict['adc_rms']
        adc_power = ant_dict['adc_power']
        pam_atten = ant_dict['pam_atten']
        pam_power = ant_dict['pam_power']
        pam_voltage = ant_dict['pam_voltage']
        pam_current = ant_dict['pam_current']
        if ant_dict['pam_id'] is not None and ant_dict['pam_id'] != -1:
            pam_id = _pam_fem_serial_list_to_string(ant_dict['pam_id'])
        else:
            pam_id = None
        fem_voltage = ant_dict['fem_voltage']
        fem_current = ant_dict['fem_current']
        if ant_dict['fem_id'] is not None and ant_dict['fem_id'] != -1:
            fem_id = _pam_fem_serial_list_to_string(ant_dict['fem_id'])
        else:
            fem_id = None
        fem_temp = ant_dict['fem_temp']
        eq_coeffs = ant_dict['eq_coeffs']
        if ant_dict['histogram'] is not None:
            histogram_bin_centers = ant_dict['histogram'][0]
            histogram = ant_dict['histogram'][1]
        else:
            histogram_bin_centers = None
            histogram = None

        ant_status_list.append(
            AntennaStatus.create(time, antenna_number, antenna_feed_pol,
                                 snap_hostname, snap_channel_number, adc_mean,
                                 adc_rms, adc_power, pam_atten, pam_power,
                                 pam_voltage, pam_current, pam_id, fem_voltage,
                                 fem_current, fem_id, fem_temp, eq_coeffs,
                                 histogram_bin_centers, histogram))

    return ant_status_list
