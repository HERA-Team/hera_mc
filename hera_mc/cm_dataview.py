#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Allows some different data views of cm database.
Currently this is only to look at the full connections of parts looped over time,
either via db calls or pre-written files.
"""

from __future__ import absolute_import, division, print_function
from hera_mc import mc, geo_handling, cm_utils, cm_revisions, part_connect
from astropy.time import Time, TimeDelta
import numpy as np
import matplotlib.pyplot as plt


def write_file(filename, parts_list, fc_map):
    p0 = parts_list[0]
    ndate = len(fc_map[p0][0])
    print("Writing {}".format(filename))
    fp = open(filename, 'w')
    fp.write('Date            \t')
    for p in parts_list:
        fp.write('{}\t'.format(p))
    fp.write('\n')
    for i in range(ndate):
        fp.write('{:%Y-%m-%d %H:%M}\t'.format(fc_map[p0][0][i]))
        for p in parts_list:
            fp.write('{:d}\t'.format(fc_map[p][1][i]))
        fp.write('\n')
    fp.close()


def read_files(filenames):
    fc_map = {}
    parts = []
    for fn in filenames:
        try:
            fp = open(fn, 'r')
        except IOError:
            print('{} not found.'.format(fn))
            continue
        print("Reading {}".format(fn))
        part_fn = fp.readline().split()
        del(part_fn[0])
        for p in part_fn:
            if p not in fc_map.keys():
                fc_map[p] = {'datetime': [], 'flag': [], 'fc': []}
                parts.append(p)
        for line in fp:
            data = line.split()
            date = cm_utils._get_astropytime(data[0], data[1])
            del(data[0:2])
            for i in range(len(data)):
                fc_map[part_fn[i]]['datetime'].append(date.datetime)
                fc_map[part_fn[i]]['flag'].append(int(data[i]))
    return parts, fc_map


def read_db(parts, start_date, stop_date, dt, full_req, session):
    fc_map = {}
    for p in parts:
        print("Finding ", p)
        fc_map[p] = {'datetime': [], 'flag': [], 'fc': []}
        at_date = start_date
        while at_date < stop_date:
            fc = cm_revisions.get_full_revision(p, at_date, full_req, session)
            fc_map[p]['datetime'].append(at_date.datetime)
            fc_map[p]['flag'].append(len(fc))
            fc_map[p]['fc'].append(fc)
            at_date += TimeDelta(dt * 24 * 3600, format='sec')
    return fc_map


def plot_data(parts, fc_map, separate=True):
    dy = 1.0 / len(parts)
    for i, p in enumerate(parts):
        y = np.array(fc_map[p]['flag'])
        if separate:
            y = y * (2.0 - i * dy)
        plt.plot(fc_map[p]['datetime'], y, 'o', label=p)
    plt.legend(bbox_to_anchor=(1.04, 1), loc='upper left')
    plt.grid()
