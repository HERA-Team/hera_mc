#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Allows various views on the antenna hookup, as well as handle the hookup cache file.

"""

from hera_mc import mc, cm_hookup, cm_utils

if __name__ == "__main__":
    parser = mc.get_mc_argument_parser()
    parser.add_argument(
        "-p",
        "--hpn",
        help="Part number, csv-list, default/cache or method. (default)",
        default="default",
    )
    parser.add_argument(
        "-e",
        "--exact-match",
        help="Force exact matches on part numbers, not beginning N char.",
        dest="exact_match",
        action="store_true",
    )
    parser.add_argument(
        "--pol", help="Define desired pol(s) for hookup. (e, n, all)", default="all"
    )
    parser.add_argument(
        "--all",
        help="Toggle to show 'all' hookups as opposed to 'full'",
        action="store_true",
    )
    parser.add_argument(
        "--notes", help="If set, this will also show hookup notes.", action="store_true"
    )
    parser.add_argument(
        "--hookup-cols",
        help="Specify a subset of parts to show in hookup, "
        "comma-delimited no-space list. (all])",
        dest="hookup_cols",
        default="all",
    )
    parser.add_argument(
        "--hookup-type",
        dest="hookup_type",
        help="Force use of specified hookup type.",
        default=None,
    )
    parser.add_argument(
        "--hide-ports", dest="ports", help="Hide ports on hookup.", action="store_false"
    )
    parser.add_argument(
        "--show-revs", dest="revs", help="Show revs on hookup.", action="store_true"
    )
    parser.add_argument(
        "--file",
        help="output filename, if desired.  Tags are '.txt', "
        "'.html', '.csv' to set type.",
        default=None,
    )
    parser.add_argument(
        "--sortby",
        help="Part-type column order to sort display.  (csv-list)",
        default=None,
    )
    # Cache options
    parser.add_argument(
        "--use-cache",
        dest="use_cache",
        help="Force cache use (but doesn't rewrite cache)",
        action="store_true",
    )
    parser.add_argument(
        "--delete-cache-file",
        dest="delete_cache_file",
        help="Deletes the local cache file",
        action="store_true",
    )
    parser.add_argument(
        "--write-cache-file",
        dest="write_cache_file",
        help="Flag to write hookup data to cache file",
        action="store_true",
    )
    parser.add_argument(
        "--cache-info",
        help="Shows information about the hookup cache file.",
        dest="cache_info",
        action="store_true",
    )
    parser.add_argument(
        "--cache-log",
        dest="cache_log",
        help="Optional log message for write-cache-file",
        default="Called from hookup script.",
    )
    cm_utils.add_date_time_args(parser)

    args = parser.parse_args()
    # Pre-process the args
    at_date = cm_utils.get_astropytime(args.date, args.time, args.format)
    args.hookup_cols = cm_utils.listify(args.hookup_cols)
    state = "all" if args.all else "full"
    if args.file is None:
        output_format = "display"
    else:
        print("Writing data to {}".format(args.file))
        output_format = args.file.split(".")[-1]

    # Start session
    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()
    hookup = cm_hookup.Hookup(session)
    if args.cache_info:
        print(hookup.hookup_cache_file_info())
    elif args.delete_cache_file:
        hookup.delete_cache_file()
    else:
        hookup_dict = hookup.get_hookup(
            hpn=args.hpn,
            pol=args.pol,
            at_date=at_date,
            exact_match=args.exact_match,
            use_cache=args.use_cache,
            hookup_type=args.hookup_type,
        )
        show = hookup.show_hookup(
            hookup_dict=hookup_dict,
            cols_to_show=args.hookup_cols,
            ports=args.ports,
            revs=args.revs,
            sortby=args.sortby,
            state=state,
            filename=args.file,
            output_format=output_format,
        )
        if output_format == "display":
            print(show)
        if args.notes:
            print(
                "\nNotes:\n---------------------------------------------------------------"
            )
            print(hookup.show_notes(hookup_dict=hookup_dict, state=state))
            print(
                "-------------------------------------------------------------------------"
            )
        if args.write_cache_file:
            hookup.write_cache_file(args.cache_log)
