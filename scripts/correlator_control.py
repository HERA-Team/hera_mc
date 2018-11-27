#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""script to control correlator (taking data, noise diode, phase switching)

"""
from __future__ import absolute_import, division, print_function

import sys
from astropy.time import Time

from hera_mc import mc
from hera_mc import correlator as corr

valid_commands = list(corr.command_dict.keys())

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.description = """Send correlator control commands"""
    parser.add_argument('command', help="correlator control command. One of: "
                        + valid_commands)
    parser.add_argument('--address', help="address for correlator redis", default=None)
    parser.add_argument('--starttime', help="required if command is 'take_data', "
                        "ignored otherwise. Time to start taking data. "
                        "Format readable by astropy Time object, can specify "
                        "format and scale separately.", default=None)
    parser.add_argument('--starttime_format', help="astropy Time object format "
                        "string for interpreting starttime.", default=None)
    parser.add_argument('--starttime_scale', help="astropy Time object scale "
                        "string for interpreting starttime.", default=None)
    parser.add_argument('--duration', help="required if command is 'take_data', "
                        "ignored otherwise. Length of time to take data for, in seconds. "
                        "Float", default=None)
    parser.add_argument('--tag', help="required if command is 'take_data', "
                        "ignored otherwise. Tag which will end up in data files "
                        "as a header entry, must be from correlator.tag_list "
                        "(e.g. 'science', 'engineering').", default=None)
    parser.add_argument('--acclen_spectra', help="only used if command is 'take_data', "
                        "ignored otherwise. Accumulation length in spectra. "
                        "Defaults to a value that produces ~10s integration time."
                        "Integer", default=None)
    parser.add_argument('--overwrite_take_data', help="only used if command is 'take_data', "
                        "ignored otherwise.  If there is already a take data starttime "
                        "in the future, overwrite it with this command."
                        "Boolean", default=False)
    parser.add_argument('--config_file', help="only used if command is 'update_config', "
                        "ignored otherwise. config file to command the correlator to use."
                        "String", default=None)
    parser.add_argument('--dryrun', help="just print the list of CorrelatorControlCommand "
                        "objects, do not issue the power commands or log them "
                        "to the database' [False]", action='store_true')
    parser.add_argument('--testing', help="Testing: do not use anything that "
                        "requires a connection to the correlator (implies dryrun)' [False]",
                        action='store_true')

    args = parser.parse_args()
    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()

    if args.starttime is not None:
        starttime_obj = Time(starttime, format=args.starttime_format,
                             scale=args.scale)

    command_list = session.correlator_control_command(args.command,
                                                      starttime=starttime_obj
                                                      duration=args.duration,
                                                      acclen_spectra=args.acclen_spectra,
                                                      tag=args.tag,
                                                      overwrite_take_data=args.overwrite_take_data,
                                                      config_file=args.config_file,
                                                      dryrun=args.dryrun,
                                                      testing=args.testing)
    if args.testing or args.dryrun:
        for cmd in command_list:
            print(cmd)
    session.commit()
