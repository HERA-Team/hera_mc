# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Monitoring temperatures of various parts of the telescope.

"""
from __future__ import absolute_import, division, print_function

import numpy as np
from astropy.time import Time
from sqlalchemy import Column, Float
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION

from . import MCDeclarativeBase


class PaperTemperatures(MCDeclarativeBase):
    """
    Definition of paper_temperatures table.

    gps_time: GPS second of observation (double)
    jd_time: JD time of observation (to 5 decimals, <0.05 sec accuracy) (double)
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

    gps_time = Column(DOUBLE_PRECISION, nullable=False, primary_key=True)
    jd_time = Column(DOUBLE_PRECISION, nullable=False)
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

    def __repr__(self):
        return ("<PaperTemperatures('{self.gps_time}', '{self.jd_time}', "
                "'{self.balun_east}', '{self.cable_east}', "
                "'{self.balun_west}', '{self.cable_west}', "
                "'{self.rcvr_1a}', '{self.rcvr_1b}', "
                "'{self.rcvr_2a}', '{self.rcvr_2b}', "
                "'{self.rcvr_3a}', '{self.rcvr_3b}', "
                "'{self.rcvr_4a}', '{self.rcvr_4b}', "
                "'{self.rcvr_5a}', '{self.rcvr_5b}', "
                "'{self.rcvr_6a}', '{self.rcvr_6b}', "
                "'{self.rcvr_7a}', '{self.rcvr_7b}', "
                "'{self.rcvr_8a}', '{self.rcvr_8b}')>".format(self=self))

    def __eq__(self, other):
        if isinstance(other, PaperTemperatures):
            attribute_list = [a for a in dir(self) if not a.startswith('__') and
                              not callable(getattr(self, a))]
            isequal = True
            for a in attribute_list:
                if isinstance(a, Column):
                    self_col = getattr(self, a)
                    other_col = getattr(other, a)
                    if self_col != other_col:
                        print('column {col} does not match. Left is {lval} '
                              'and right is {rval}'.
                              format(col=a, lval=str(self_col),
                                     rval=str(other_col)))
                        isequal = False
            return isequal
        else:
            return False


    @classmethod
    def new_from_text_row (cls, read_time, temp_list):
        """
        Create a new PaperTemperatures item from items parsed from the text file
        that's written out on tmon.

        Parameters:
        ------------
        read_time: float or astropy time object
            if float: jd time of temperature read

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
        if isinstance(read_time, Time):
            t_read = read_time.utc
        elif isinstance(read_time, float):
            t_read = Time(read_time, format='jd', scale='utc')
        else:
            raise ValueError ('unrecognized "read_time" argument: %r' % (read_time,))

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
        return cls(gps_time=t_read.gps, jd_time=t_read.jd, **temp_dict)
