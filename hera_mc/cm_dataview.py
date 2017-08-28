#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Allows some different data views of cm database.
Currently this is only to look at the full connections of parts looped over time,
either via db calls or pre-written files.
"""

from __future__ import absolute_import, print_function
from hera_mc import mc, cm_utils, cm_revisions
from astropy.time import Time, TimeDelta
import numpy as np
import matplotlib.pyplot as plt


class Dataview:
    def __init__(self, session=None):
        """
        session: session on current database. If session is None, a new session
                 on the default database is created and used.
        """
        if session is None:
            db = mc.connect_to_mc_db(None)
            self.session = db.sessionmaker()
        else:
            self.session = session
        self.parts_list = None
        self.fc_map = None

    def print_fully_connected(self, fully_connected):
        """
        Prints out correlator information from 'standard' fully_connected list

        Parameters:
        ------------
        fully_connected:  list of fully connected stations provided by the correlator
        methods in geo_handling
        """
        print("Part number    x/E input    y/N input")
        print("-----------    ---------    ---------")
        for fv in fully_connected:
            print("{:11}    {:9}    {:9}".format(fv['station_name'],
                  fv['correlator_input_x'], fv['correlator_input_y']))

    def read_db(self, parts, start_date, stop_date, dt, full_req):
        """
        Reads the database to produce a "map" of fully connected antennas,
        returned in a dictionary (fc_map)

        Parameters:
        ------------
        parts:  list of parts (stations) to search for
        start_date:  astropy.time to start map
        stop_date:  astropytime to stop map
        dt:  time-step for dictionary
        full_req:  parts needed for full Hookup
        """

        fc_map = {}
        for p in parts:
            print("Finding ", p)
            fc_map[p] = {'datetime': [], 'flag': [], 'fc': []}
            at_date = start_date
            while at_date < stop_date:
                fc = cm_revisions.get_full_revision(p, at_date, full_req, self.session)
                fc_map[p]['datetime'].append(at_date.datetime)
                fc_map[p]['flag'].append(len(fc))
                fc_map[p]['fc'].append(fc)
                at_date += TimeDelta(dt * 24 * 3600, format='sec')
        self.parts_list = parts
        self.fc_map = fc_map
        return fc_map

    def write_fc_map_file(self, filename, output='flag'):
        """
        Writes the fc_map to the named filename.  Either a 'flag' file can be written
        (i.e. 0 or 1) for the plotter, or the 'corr'elator hookups

        Parameters:
        ------------
        filename:  name of output file
        output:  type of file 'flag' or 'corr'
        """

        if self.fc_map is None or self.parts_list is None:
            print("You first need to generate fc_map and parts_list")
            return None
        from hera_mc import cm_hookup
        hu = cm_hookup.Hookup(self.session)
        p0 = self.parts_list[0]
        ndate = len(self.fc_map[p0]['datetime'])
        print("Writing {}".format(filename))
        fp = open(filename, 'w')
        fp.write('{:18}'.format('Date'))
        for p in self.parts_list:
            if output == 'corr':
                fp.write('{:^19}'.format(p))
            else:
                fp.write('{:^8}'.format(p))
        fp.write('\n')
        for i in range(ndate):
            fp.write('{:%Y-%m-%d %H:%M}  '.format(self.fc_map[p0]['datetime'][i]))
            for p in self.parts_list:
                if output == 'flag':
                    fp.write('{:^8d}'.format(self.fc_map[p]['flag'][i]))
                elif output == 'corr':
                    if self.fc_map[p]['fc'][i]:
                        this_hu = self.fc_map[p]['fc'][i][0].hookup
                        c = hu.get_correlator_input_from_hookup(this_hu)
                        s = 'e:{} n:{}'.format(c['e'], c['n'])
                    else:
                        s = '---'
                    fp.write('{:^19}'.format(s))
            fp.write('\n')
        fp.close()

    def read_fc_map_files(self, filenames):
        """
        Reads in fc_map from the supplied filenames list.

        Parameters:
        ------------
        filenames:  list of filenames to read in .
        """

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
        self.parts_list = parts
        self.fc_map = fc_map
        return parts, fc_map

    def plot_fc_map(self):
        """
        Plots the fc_map flgs.

        Parameters:
        ------------
        separate:  T/F to plot the rows separated.
        """

        dy = 1.0 / len(self.parts_list)
        for i, p in enumerate(self.parts_list):
            y = np.array(self.fc_map[p]['flag'])
            # Separate out the lines a bit
            y = y * (2.0 - i * dy)
            plt.plot(self.fc_map[p]['datetime'], y, 'o', label=p)
        plt.legend(bbox_to_anchor=(1.04, 1), loc='upper left')
        plt.grid()
        plt.show()
