#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""script to control correlator (taking data, noise diode, phase switching)

"""

from astropy.time import Time, TimeDelta
from astropy.units import Quantity
from hera_mc.utils import LSTScheduler
from hera_mc import mc, geo_handling
from hera_mc import correlator as corr

valid_commands = sorted(corr.command_dict.keys())

if __name__ == "__main__":
    parser = mc.get_mc_argument_parser()
    parser.description = """Send correlator control commands"""
    parser.add_argument(
        "command",
        help="Correlator control command. One of: " + ", ".join(valid_commands) + ".",
    )
    parser.add_argument(
        "-f",
        "--force",
        help="Option to force a command that might interfere "
        "with observing even if the correlator is currently taking data. This "
        "will only have an effect for commands that are not usually allowed "
        "while data is being taken (e.g restart, hard_stop, phase "
        "switching/load/noise diode state changes). [False]",
        action="store_true",
    )
    parser.add_argument(
        "--address",
        help="Address for correlator redis. The " "default is used if unspecified.",
        default=None,
    )
    parser.add_argument(
        "--starttime",
        help="Required if command is 'take_data', "
        "ignored otherwise. Time to start taking data. "
        "Format readable by astropy Time object, can specify "
        "format and scale separately (string).",
        default=None,
    )
    parser.add_argument(
        "--starttime_format",
        help="Astropy Time object format "
        "string for interpreting starttime (string).",
        default=None,
    )
    parser.add_argument(
        "--starttime_scale",
        help="Astropy Time object scale " "string for interpreting starttime (string).",
        default=None,
    )
    parser.add_argument(
        "--duration",
        help="Required if command is 'take_data', "
        "ignored otherwise. Length of time to take data for, "
        "in seconds (float). ",
        type=float,
        default=None,
    )
    parser.add_argument(
        "--tag",
        help="Required if command is 'take_data', "
        "ignored otherwise. Tag which will end up in data files "
        "as a header entry, must be one of: " + ", ".join(corr.tag_list) + ".",
        default=None,
    )
    parser.add_argument(
        "--acclen_spectra",
        help="Only used if command is 'take_data', "
        "ignored otherwise. Accumulation length in spectra, "
        "must be an integer and a multiple of 2048. "
        "Defaults to a value that produces ~10s integration time. ",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--overwrite_take_data",
        help="Only used if command is "
        "'take_data', ignored otherwise. Option to force an "
        "overwrite of the next take data command if there is "
        "already one scheduled in the future (boolean).",
        default=False,
    )
    parser.add_argument(
        "--config_file",
        help="Only used if command is "
        "'update_config', ignored otherwise. Config file to "
        "command the correlator to use (string).",
        default=None,
    )
    parser.add_argument(
        "--dryrun",
        help="Just print the list of "
        "CorrelatorControlCommand (and possibly other) objects, "
        "that would be added to the database, do not issue the "
        "commands or log them to the database [False]",
        action="store_true",
    )
    parser.add_argument(
        "--testing",
        help="Testing mode: do not use anything that "
        "requires a connection to the correlator "
        "(implies dryrun) [False]",
        action="store_true",
    )
    parser.add_argument(
        "--lstlock",
        help="Lock observation start to a 16s LST grid " "[True]",
        action="store_true",
    )
    parser.add_argument(
        "--now",
        help="Take data in 60s."
        "overrides: starttime, starttime_format and starttime_scale",
        action="store_true",
    )

    args = parser.parse_args()
    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()

    if args.starttime is not None:
        starttime_obj = Time(
            args.starttime, format=args.starttime_format, scale=args.starttime_scale
        )
    elif args.now:
        # now + 60s buffer for correlator to collect itself
        starttime_obj = Time.now() + TimeDelta(Quantity(60, "second"))
    else:
        starttime_obj = None
    if args.lstlock and starttime_obj is not None:
        LSTbin_size = 16  # seconds
        geo = geo_handling.Handling(session)  # get the geo part of CM
        cofa = geo.cofa()  # center of array (COFA yo)
        longitude = cofa[0].lon  # the longitude in _degrees_
        starttime_obj, LSTbin = LSTScheduler(
            starttime_obj, LSTbin_size, longitude=longitude
        )
        print(
            "locking to {s}s LST grid. Next bin at".format(s=LSTbin_size),
            starttime_obj.iso,
        )
    command_list = session.correlator_control_command(
        args.command,
        starttime=starttime_obj,
        duration=args.duration,
        acclen_spectra=args.acclen_spectra,
        tag=args.tag,
        overwrite_take_data=args.overwrite_take_data,
        config_file=args.config_file,
        force=args.force,
        dryrun=args.dryrun,
        testing=args.testing,
    )
    if args.testing or args.dryrun:
        for cmd in command_list:
            print(cmd)
    session.commit()
