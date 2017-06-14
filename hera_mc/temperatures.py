# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Monitoring temperatures of various parts of the telescope.

"""
from __future__ import absolute_import, division, print_function

from math import floor
import numpy as np
from astropy.time import Time
from sqlalchemy import Column, Float, BigInteger

from . import MCDeclarativeBase


class PaperTemperatures(MCDeclarativeBase):
    """
    Definition of paper_temperatures table.

    time: time of this measurement in floor(gps seconds) (BigInteger)
    balun_east: temperature at a balun east of the hut (float)
    cable_east: temperature of the underside of a feed cable east of the hut (float)
    balun_west: temperature at a balun west of the hut (float)
    cable_west: temperature of the underside of a feed cable west of the hut (float)
    rcvr_1a: 1st temperature in receiverator 1
    rcvr_1b: 2nd temperature in receiverator 1
    .
    .
    .
    rcvr_8a: 1st temperature in receiverator 8
    rcvr_8b: 2nd temperature in receiverator 8
    """
    __tablename__ = 'paper_temperatures'

    time = Column(BigInteger, nullable=False, primary_key=True)
    balun_east = Column(Float)
    cable_east = Column(Float)
    balun_west = Column(Float)
    cable_west = Column(Float)
    rcvr_1a = Column(Float)
    rcvr_1b = Column(Float)
    rcvr_2a = Column(Float)
    rcvr_2b = Column(Float)
    rcvr_3a = Column(Float)
    rcvr_3b = Column(Float)
    rcvr_4a = Column(Float)
    rcvr_4b = Column(Float)
    rcvr_5a = Column(Float)
    rcvr_5b = Column(Float)
    rcvr_6a = Column(Float)
    rcvr_6b = Column(Float)
    rcvr_7a = Column(Float)
    rcvr_7b = Column(Float)
    rcvr_8a = Column(Float)
    rcvr_8b = Column(Float)

    @classmethod
    def new_from_text_row(cls, time, temp_list):
        """
        Create a new PaperTemperatures item from items parsed from the text file
        that's written out on tmon.

        Parameters:
        ------------
        time: astropy time object
            time of measurement

        temp_list: List of temperatures as written to text file (see below,
            contains extra columns we don't save

        From the wiki: description of columns in text file: (temp list is cols 1-28)
        Col 0:   Julian date to 5 decimal places
        Col 1:   Balun East
        Col 2:   Cable East
        Col 3:   Balun West
        Col 4:   Cable West
        Col 5:   junk
        Col 6:   junk
        Col 7:   junk
        Col 8:   Rcvr 1-A
        Col 9:   Rcvr 1-B
        Col 10:  Rcvr 2-A
        Col 11:  Rcvr 2-B
        Col 12:  Rcvr 3-A
        Col 13:  Rcvr 3-B
        Col 14:  junk
        Col 15:  Rcvr 4-A
        Col 16:  Rcvr 4-B
        Col 17:  Rcvr 5-A
        Col 18:  Rcvr 5-B
        Col 19:  Rcvr 6-A
        Col 20:  Rcvr 6-B
        Col 21:  junk
        Col 22:  Rcvr 7-A
        Col 23:  Rcvr 7-B
        Col 24:  Rcvr 8-A
        Col 25:  Rcvr 8-B
        Col 26:  junk
        Col 27:  junk
        Col 28:  junk
        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        time = floor(time.gps)

        temp_colnames = ['balun_east', 'cable_east',
                         'balun_west', 'cable_west',
                         'rcvr_1a', 'rcvr_1b', 'rcvr_2a', 'rcvr_2b',
                         'rcvr_3a', 'rcvr_3b', 'rcvr_4a', 'rcvr_4b',
                         'rcvr_5a', 'rcvr_5b', 'rcvr_6a', 'rcvr_6b',
                         'rcvr_7a', 'rcvr_7b', 'rcvr_8a', 'rcvr_8b']
        temp_indices = (np.array([1, 2, 3, 4, 8, 9, 10, 11, 12, 13, 15, 16, 17, 18,
                                  19, 20, 22, 23, 24, 25]) - 1).tolist()
        temp_values = [temp_list[i] for i in temp_indices]
        temp_dict = dict(zip(temp_colnames, temp_values))
        return cls(time=time, **temp_dict)
