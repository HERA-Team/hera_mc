#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Check in on the status of this machine's MegaRAID array and log information
to the M&C system.

We assume that there is one controller with one big old RAID array.

This script must be run as root since that's what the storcli64 command line
client requires.

"""
import datetime
import dateutil.tz
import errno
import json
import socket
from subprocess import Popen, PIPE
import sys

from astropy.time import Time, TimeDelta

from hera_mc import mc


# Preliminaries
#
# This script runs as root on netboot machines where the majority of the
# filesystem is readonly. So `event_ticker` is hardcoded to point to somewhere
# where we can reliably save state.
#
# If `num_recent_events` gets too big, the relevant storcli call can start taking
# incredibly long to complete.

storcli = "/opt/MegaRAID/storcli/storcli64"
event_ticker = "/home/obs/.hera_mc/megaraid_last_event_id_%s.txt" % (
    socket.gethostname(),
)
controller = 0
num_recent_events = (
    32  # if more than this many events occur between runs, some won't get logged
)
hostname = socket.gethostname()

show_all_items = [
    "Controller Status",
    "Memory Correctable Errors",
    "Memory Uncorrectable Errors",
    "BBU Status",
    "Physical Drives",
]

event_header_keep_keys = frozenset(["Code", "Class", "Locale", "Event Description"])


_months = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


def parse_storcli_datetime(text):
    """Example input text: "Sat May 20 00:16:57 2017". Returns an Astropy Time
    object. The time reported by storcli is in the system local time (and not,
    say, UTC).

    """
    _, month, day, hhmmss, year = text.split()
    month = _months[month]
    day = int(day)
    year = int(year)
    hour, minute, second = [int(s) for s in hhmmss.split(":")]
    local_tz = dateutil.tz.tzlocal()
    t = datetime.datetime(year, month, day, hour, minute, second, tzinfo=local_tz)
    return Time(t)  # auto-converts to UTC timescale


# Before running anything, make sure we can connect to the DB.

parser = mc.get_mc_argument_parser()
args = parser.parse_args()
db = mc.connect_to_mc_db(args)


# Get the seqNum of the last event that we've noticed

try:
    ticker_file = open(event_ticker, "r")
except IOError as e:
    if e.errno != errno.ENOENT:
        raise
    last_seen_seqnum = 0
else:
    last_seen_seqnum = int(ticker_file.readline())
    ticker_file.close()


# Parse '/c0 show all'

show_all = Popen(
    [storcli, "/c%d" % controller, "show", "all"], shell=False, stdout=PIPE
)
item_values = {}

for line in show_all.stdout:
    line = line.decode("utf-8")
    for item in show_all_items:
        if line.startswith(item):
            item_values[item] = line.split("=", 1)[1].strip()
            break

    # This is not at all scalable, but ... meh. We're looking for:
    #
    # ----------------------------------------------------------------
    # DG/VD TYPE   State Access Consist Cache Cac sCC       Size Name
    # ----------------------------------------------------------------
    # 0/0   RAID60 Optl  RW     Yes     RWBD  -   ON  196.475 TB
    # ----------------------------------------------------------------

    if line.startswith("0/0"):
        item_values["VD 0/0 State"] = line.split()[2]

if show_all.wait() != 0:
    print("error: storcli exited with an error code", file=sys.stderr)
    print(
        "unfortunately this script may have swallowed its error message",
        file=sys.stderr,
    )
    sys.exit(1)

num_disks = int(item_values.pop("Physical Drives", 0))
status_info = json.dumps(item_values, sort_keys=True)

# Parse the recent events

event_log = Popen(
    [
        storcli,
        "/c%d" % controller,
        "show",
        "events",
        "type=latest=%d" % num_recent_events,
        "filter=warning,critical,fatal",
    ],
    shell=False,
    stdout=PIPE,
)
events = []

NOT_IN_EVENT, IN_EVENT = 0, 1
state = NOT_IN_EVENT
seq_num = None
cur_event_data = {}

for line in event_log.stdout:
    line = line.decode("utf-8")
    if state == NOT_IN_EVENT:
        if line.startswith("seqNum:"):
            # The extra 0 arg here means to guess the numeric base;
            # seqnum is in hex with a 0x prefix.
            seq_num = int(line.split(":", 1)[1].strip(), 0)
            state = IN_EVENT
    elif state == IN_EVENT:
        line = line.strip()
        if not len(line):
            continue

        if line.startswith("======="):
            continue

        if line.startswith("Event Data:"):  # just a separator
            continue

        if line == "None":  # appears for events with no data after the ====== divider
            continue

        if line.startswith("seqNum:"):  # new event, finishing old one
            if seq_num is not None:
                events.append((seq_num, cur_event_data))
                seq_num = None
                cur_event_data = {}

            seq_num = int(line.split(":", 1)[1].strip(), 0)
            state = IN_EVENT
            continue

        if line.startswith("Controller ="):  # we've reached the footer
            if seq_num is not None:
                events.append((seq_num, cur_event_data))
                seq_num = None
                cur_event_data = {}

            state = NOT_IN_EVENT
            continue

        try:
            key, value = line.split(":", 1)
        except ValueError:
            print("severe: unexpected event data line: %r" % (line,))
        else:
            cur_event_data[key] = value.strip()

if event_log.wait() != 0:
    print("error: storcli exited with an error code", file=sys.stderr)
    print(
        "unfortunately this script may have swallowed its error message",
        file=sys.stderr,
    )
    sys.exit(1)

if seq_num is not None:
    events.append((seq_num, cur_event_data))


# Now actually check in with the database

now = Time.now()
biggest_seqnum = last_seen_seqnum

with db.sessionmaker() as session:
    session.add_lib_raid_status(now, hostname, num_disks, status_info)

    for seqnum, data in events:
        if seqnum <= last_seen_seqnum:
            continue

        biggest_seqnum = max(biggest_seqnum, seqnum)

        # Once the controller makes contact with the OS,
        # it reports event times in the local time using the 'Time'
        # key. But on boot, it doesn't know the time and can
        # only report a delta against boot.

        abs_time_str = data.pop("Time", None)
        if abs_time_str is not None:
            time = parse_storcli_datetime(abs_time_str)
        else:
            boot_rel_time = int(data.pop("Seconds since last reboot"))
            import psutil

            boot = datetime.datetime.fromtimestamp(psutil.boot_time())
            delta = TimeDelta(boot_rel_time, format="sec")
            time = Time(boot) + delta

        disk = data.pop("Device ID", "?")
        data["seqNum"] = seqnum
        info = json.dumps(data)
        session.add_lib_raid_error(time, hostname, disk, info)

    session.commit()


# Remember the biggest seqnum that we've seen.

with open(event_ticker, "w") as f:
    print(biggest_seqnum, file=f)
