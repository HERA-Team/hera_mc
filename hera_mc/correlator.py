# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Correlator M&C interface

"""
from __future__ import absolute_import, division, print_function

import six
from math import floor
from astropy.time import Time
from sqlalchemy import Column, BigInteger, Integer, Float, Boolean, String, ForeignKeyConstraint

from . import MCDeclarativeBase

DefaultRedisAddress = "redishost"

# key is state type, value is method name in hera_corr_cm
state_dict = {'taking_data': 'is_recording', 'phase_switching': 'phase_switch_is_on',
              'noise_diode': 'noise_diode_is_on'}

tag_list = ['science', 'engineering']

# key is command, value is method name in hera_corr_cm
command_dict = {'take_data': 'take_data', 'stop_taking_data': 'stop_taking_data',
                'phase_switching_on': 'phase_switch_enable',
                'phase_switching_off': 'phase_switch_disable',
                'noise_diode_on': 'noise_diode_enable',
                'noise_diode_off': 'noise_diode_disable',
                'restart': 'restart'}

command_state_map = {'take_data': {'allowed_when_recording': False},
                     'stop_taking_data': {'state_type': 'taking_data', 'state': False,
                                          'allowed_when_recording': True},
                     'phase_switching_on': {'state_type': 'phase_switching',
                                            'state': True,
                                            'allowed_when_recording': False},
                     'phase_switching_off': {'state_type': 'phase_switching',
                                             'state': False,
                                             'allowed_when_recording': False},
                     'noise_diode_on': {'state_type': 'noise_diode', 'state': True,
                                        'allowed_when_recording': False},
                     'noise_diode_off': {'state_type': 'noise_diode', 'state': False,
                                         'allowed_when_recording': False},
                     'restart': {'allowed_when_recording': False}}


class CorrelatorControlState(MCDeclarativeBase):
    """
    Definition of correlator control state table.

    time: gps time of the control state, floored (BigInteger, part of primary_key).
    state_type: type of control state, one of the keys in state_dict (String, part of primary_key)
    state: boolean indicating whether the state_type is true or false
    """
    __tablename__ = 'correlator_control_state'
    time = Column(BigInteger, primary_key=True)
    state_type = Column(String, primary_key=True)
    state = Column(Boolean, nullable=False)

    @classmethod
    def create(cls, time, state_type, state):
        """
        Create a new correlator control state object.

        Parameters:
        ------------
        time: astropy time object
            astropy time object based on a timestamp reported by the correlator
        state_type: string
            must be a key in state_dict (e.g. 'taking_data', 'phase_switching', 'noise_diode')
        state: boolean
            is the state_type true or false
        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        corr_time = floor(time.gps)

        if state_type not in list(state_dict.keys()):
            raise ValueError('state_type must be one of: ' + ', '.join(list(state_dict.keys()))
                             + '. state_type is actually {}'.format(state_type))

        return cls(time=corr_time, state_type=state_type, state=state)


def _get_control_state(correlator_redis_address=DefaultRedisAddress):
    """
    Loops through the state types in state_dict and gets the latest state and associated timestamp for each one.

    Returns a 2-level dict, top level key is a key from the state_dict,
    second level keys are 'timestamp' and 'state' (a boolean)
    """
    import hera_corr_cm

    corr_cm = hera_corr_cm.HeraCorrCM(redishost=correlator_redis_address)

    corr_state_dict = {}
    for key, value in enumerate(state_dict):
        # call each state query method and add to corr_state_dict
        timestamp, state = getattr(corr_cm, value)
        corr_state_dict[key]: {'timestamp': timestamp, 'state': state}

    return corr_state_dict


def create_control_state(correlator_redis_address=DefaultRedisAddress, corr_state_dict=None):
    """
    Return a list of correlator control state objects with data from the correlator.

    Parameters:
    ------------
    correlator_redis_address: Address where the correlator redis database can be accessed.
        Only used if corr_state_dict is None.
    corr_state_dict: A dict containing info as in the return dict from _get_control_state()
        for testing purposes. If None, _get_control_state() is called. Default: None

    Returns:
    -----------
    A list of CorrelatorControlState objects
    """

    if corr_state_dict is None:
        corr_state_dict = _get_control_state(correlator_redis_address=correlator_redis_address)

    corr_state_list = []
    for state_type, dict in six.iteritems(corr_state_dict):
        time = Time(dict['timestamp'], format='datetime', scale='utc')
        state = dict['state']

        corr_state_list.append(CorrelatorControlState.create(time, state_type, state))

    return corr_state_list


class CorrelatorControlCommand(MCDeclarativeBase):
    """
    Definition of correlator control command table.

    time: gps time of the command, floored (BigInteger, part of primary_key).
    command: control command, one of the keys in command_dict (String, part of primary_key)
    """
    __tablename__ = 'correlator_control_command'
    time = Column(BigInteger, primary_key=True)
    command = Column(String, primary_key=True)

    @classmethod
    def create(cls, time, command):
        """
        Create a new correlator control command object.

        Parameters:
        ------------
        time: astropy time object
            astropy time object for time command was sent.
        command: string
            one of the keys in command_dict (e.g. 'take_data',
            'phase_switching_on', 'phase_switching_off', 'restart')
        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        corr_time = floor(time.gps)

        if command not in list(command_dict.keys()):
            raise ValueError('command must be one of: ' + ', '.join(list(command_dict.keys()))
                             + '. command is actually {}'.format(command))

        return cls(time=corr_time, command=command)


def _get_integration_time(acclen_spectra, correlator_redis_address=DefaultRedisAddress):
    """
    gets the integration time in seconds for a given acclen in spectra

    """
    import hera_corr_cm

    corr_cm = hera_corr_cm.HeraCorrCM(redishost=correlator_redis_address)

    return corr_cm.n_spectra_to_secs(acclen_spectra)


def _get_next_start_time(correlator_redis_address=DefaultRedisAddress):
    """
    gets the next start time from the correlator, in gps seconds

    """
    import hera_corr_cm

    corr_cm = hera_corr_cm.HeraCorrCM(redishost=correlator_redis_address)

    starttime_unix_timestamp = corr_cm.next_start_time()
    if starttime_unix_timestamp == 0.0:
        return None

    return Time(starttime_unix_timestamp, format=unix).gps


class CorrelatorTakeDataArguments(MCDeclarativeBase):
    """
    Definition of correlator take_data arguments table.

    Records the arguments passed to the correlator `take_data` command.

    time: gps time of the take_data command, floored (BigInteger, part of primary_key).
    starttime_sec: gps time to start taking data, floored (BigInteger)
    starttime_ms: milliseconds to add to starttime_sec to set correlator start time.
    duration: Duration to take data for in seconds. After this time, the
        correlator will stop recording.
    acclen_spectra: Accumulation length in spectra.
    integration_time: Accumulation length in seconds, converted from acclen_spectra.
        The conversion is non-trivial and depends on the correlator settings.
    tag: Tag which will end up in data files as a header entry
    """
    __tablename__ = 'correlator_take_data_arguments'
    time = Column(BigInteger, primary_key=True)
    command = Column(String, primary_key=True)
    starttime_sec = Column(BigInteger)
    starttime_ms = Column(Integer)
    duration = Column(Float)
    acclen_spectra = Column(Integer)
    integration_time = Column(Float)
    tag = Column(String)

    # TODO: this Foreign key arrangement requires an unneccesary column on this
    # object (command) because this table only has rows when command='take_data'
    # Is there a way to specify the constraint without this dummy column?
    __table_args__ = (ForeignKeyConstraint(['time', 'command'],
                                           ['correlator_control_command.time',
                                            'correlator_control_command.command']), {})

    @classmethod
    def create(cls, time, starttime, duration, acclen_spectra, integration_time, tag):
        """
        Create a new correlator take data arguments object.

        Parameters:
        ------------
        time: astropy time object
            astropy time object for time the take_data command was sent.
        starttime: astropy time object
            astropy time object for time to start taking data
        duration: float
            Duration to take data for in seconds. After this time, the
            correlator will stop recording.
        acclen_spectra: integer
            Accumulation length in spectra.
        integration_time: float
            Integration time in seconds, converted from acclen_spectra
        tag: string
            Tag which will end up in data files as a header entry.
            Must be one of the values in tag_list
        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        corr_time = floor(time.gps)

        if not isinstance(starttime, Time):
            raise ValueError('starttime must be an astropy Time object')
        starttime_gps = starttime.gps
        starttime_sec = floor(starttime_gps)

        # TODO: check on what the resolution should be here
        # 1ms or more?
        starttime_ms = floor((starttime_gps - starttime_sec) * 1000.)

        if tag not in tag_list:
            raise ValueError('tag must be one of: ', tag_list)

        return cls(time=corr_time, command='take_data', starttime_sec=starttime_sec,
                   starttime_ms=starttime_ms, duration=duration,
                   acclen_spectra=acclen_spectra, integration_time=integration_time,
                   tag=tag)
