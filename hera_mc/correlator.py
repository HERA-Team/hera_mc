# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Correlator M&C interface

"""
from __future__ import absolute_import, division, print_function

from astropy.time import Time
from math import floor
from sqlalchemy import Column, BigInteger, Integer, Float, Boolean, String

from . import MCDeclarativeBase


# key is state type, value is method name in hera_corr_cm
state_dict = {'taking_data': 'is_recording', 'phase_switching': 'phase_switch_is_on',
              'noise_diode': 'noise_diode_is_on'}

tag_list = ['science', 'engineering']

# key is command, value is method name in hera_corr_cm
correlator_command_dict = {'take_data': 'take_data',
                           'phase_switching_on': 'phase_switch_enable',
                           'phase_switching_off': 'phase_switch_disable',
                           'noise_diode_on': 'noise_diode_enable',
                           'noise_diode_off': 'noise_diode_disable',
                           'restart': 'restart'}


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


def _get_control_state(correlator_redis_address=default_redis_address):
    """
    Loops through the state types in state_dict and gets the latest state and associated timestamp for each one.

    Returns a 2-level dict, top level key is a key from the state_dict,
    second level keys are 'timestamp' and 'state' (a boolean)
    """
    import hera_corr_cm

    corr_cm = hera_corr_cm.HeraCorrCM(node, serverAddress=nodeServerAddress)

    corr_state_dict = {}
    for key, value in enumerate(state_dict):
        # call each state query method and add to corr_state_dict
        timestamp, state = getattr(corr_cm, value)
        corr_state_dict[key]: {'timestamp': timestamp, 'state': state}

    return corr_state_dict


def create_control_state(correlator_redis_address=default_redis_address, corr_state_dict=None):
    """
    Return a list of correlator control state objects with data from the correlator.

    Parameters:
    ------------
    correlator_redis_address: Address where the correlator redis database can be accessed
    corr_state_dict: A dict containing info as in the return dict from _get_control_state()
        for testing purposes. If None, _get_control_state() is called. Default: None

    Returns:
    -----------
    A list of CorrelatorControlState objects
    """

    if corr_state_dict is None:
        corr_state_dict = _get_power_dict(node, nodeServerAddress=nodeServerAddress)

    corr_state_list = []
    for state_type, dict in corr_state_dict:
        time = Time(dict['timestamp'], format='datetime', scale='utc')
        state = dict['state']

        corr_state_list.append(CorrelatorControlState.create(time, state_type, state))

    return corr_state_list


class CorrelatorControlCommand(MCDeclarativeBase):
    """
    Definition of correlator control command table.

    time: gps time of the command, floored (BigInteger, part of primary_key).
    command: control command, one of the keys in correlator_command_dict (String, part of primary_key)
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
            one of the keys in correlator_command_dict (e.g. 'take_data',
            'phase_switching_on', 'phase_switching_off', 'restart')
        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        corr_time = floor(time.gps)

        if command not in list(correlator_command_dict.keys()):
            raise ValueError('command must be one of: ' + ', '.join(list(correlator_command_dict.keys()))
                             + '. command is actually {}'.format(command))

        return cls(time=corr_time, command=command)


class CorrelatorTakeDataArguments(MCDeclarativeBase):
    """
    Definition of correlator take_data arguments table.

    Records the arguments passed to the correlator `take_data` command.

    time: gps time of the take_data command, floored (BigInteger, part of primary_key).
    starttime: gps time to start taking data
    duration: Duration to take data for in seconds. After this time, the
        correlator will stop recording. float or int?
    acclen: "Accumulation length in spectra." Not sure what this means...
    tag: Tag which will end up in data files as a header entry
    """
    __tablename__ = 'correlator_take_data_arguments'
    time = Column(BigInteger, primary_key=True)
    starttime = Column(Float)
    duration = Column(Float)
    acclen = Column(Float)
    tag = Column(String, nullable=True)

    __table_args__ = (ForeignKeyConstraint(['time', 'take_data'],
                                           ['correlator_control_command.time',
                                            'correlator_control_command.command']))

    @classmethod
    def create(cls, time, starttime, duration, acclen, tag):
        """
        Create a new correlator take data arguments object.

        Parameters:
        ------------
        time: astropy time object
            astropy time object for time the take_data command was sent.
        starttime: float
            astropy time object for time to start taking data
        duration: float or int?
            Duration to take data for in seconds. After this time, the
            correlator will stop recording.
        acclen: float or int?
            "Accumulation length in spectra." Not sure what this means...
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

        if tag not in tag_list:
            raise ValueError('tag must be one of: ', tag_list)

        return cls(time=corr_time, starttime=starttime_gps, duration=duration,
                   acclen=acclen, tag=tag)
