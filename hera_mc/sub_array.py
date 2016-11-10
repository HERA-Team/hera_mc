# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""M&C logging of the parts and the connections between them.

"""

from __future__ import absolute_import, division, print_function

import datetime
import os
import socket

from sqlalchemy import Column, Float, Integer, String, func

from . import MCDeclarativeBase, NotNull
import hera_mc.mc as mc


class SubArray(MCDeclarativeBase):
    """
    A table to track sub_array things in various ways
    """
    __tablename__ = 'sub_array'

    subarray_prefix = Column(String(64), primary_key=True)
    "String prefix to sub-array type, elements of which are typically characterized by <prefix><int>."

    description = Column(String(64))
    "Short description of sub-array type."

    plot_marker = Column(String(64))
    "matplotlib marker type to use"

    def __repr__(self):
        return '<subarray_name={self.subarray_name} description={self.description} marker={self.plot_marker}>'.format(self=self)



