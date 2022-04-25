#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Steadily report the status of this machine to the M&C database.

Some M&C information needs to be averaged over long-ish time scales, and it's
easiest to provide it by having a long-lived standalone program that's in
charge of reporting.

"""
import os
import socket
import sys
import time
from builtins import int
from astropy.time import Time
import numpy as np
import psutil

from hera_mc import mc


# Preliminaries. We have a small validity check since the M&C design specifies
# the memory, network, and system load are to be 5-minute averages.

MONITORING_INTERVAL = 60  # seconds
REPORTING_CADENCE = 5  # number of MONITORING_INTERVALS between reports to M&C

if REPORTING_CADENCE * MONITORING_INTERVAL != 300:
    print(
        "warning: averaging time should be 300s but it will be %ds"
        % (REPORTING_CADENCE * MONITORING_INTERVAL),
        file=sys.stderr,
    )


def get_ip_address():
    """Return an IP address for this machine as a string.

    https://stackoverflow.com/questions/24196932/how-can-i-get-the-ip-address-of-eth0-in-python

    This is actually not well defined -- machines have multiple interfaces,
    each with its own IP address. We use eth0 if it exists, otherwise the
    first one that isn't `lo`.

    """
    import netifaces

    try:
        addrs = netifaces.ifaddresses("eth0")
    except ValueError:
        for ifname in sorted(netifaces.interfaces()):
            if ifname != "lo":
                addrs = netifaces.ifaddresses(ifname)
                break
        else:  # triggered if we never did the 'break'
            return "?.?.?.?"

    return addrs[netifaces.AF_INET][0]["addr"]


# Connect up to the database

parser = mc.get_mc_argument_parser()
parser.add_argument(
    "subsystem", help="The name of the subsystem that this machine is part of."
)
args = parser.parse_args()
db = mc.connect_to_mc_db(args)


# Let's go. We initialize last_report to the current time so that we have time
# to accumulate stats data before sending anything to M&C.

last_report = time.time()

mem_buf = np.zeros(REPORTING_CADENCE, dtype=np.uint64)
rx_buf = np.zeros(REPORTING_CADENCE, dtype=np.uint64)
tx_buf = np.zeros(REPORTING_CADENCE, dtype=np.uint64)
index = 0
prev_index = REPORTING_CADENCE - 1

# Network byte counters can wrap around if they're stored as 32 bits.
# When we detect a wraparound we bump these up to maintain continuity.
# We use Python 'long's so we'll be fine.

net_rx_offset = int(0)
net_tx_offset = int(0)

# OK, let's go.

with db.sessionmaker() as session:
    try:
        while True:
            now = time.time()

            # Update the higher-cadence monitoring data

            vmem = psutil.virtual_memory()
            mem_buf[index] = vmem.used  # bytes

            net = psutil.net_io_counters()

            if net.bytes_sent < tx_buf[prev_index]:  # have we wrapped?
                net_tx_offset += int(1) << 32  # assuming wraparound only affects 32-bit
            tx_buf[index] = net.bytes_sent + net_tx_offset

            if net.bytes_recv < rx_buf[prev_index]:
                net_rx_offset += int(1) << 32
            rx_buf[index] = net.bytes_recv + net_rx_offset

            prev_index = index
            index = (index + 1) % REPORTING_CADENCE

            # It's time to file a status update? If so, first, gather bits of
            # information that don't need to be averaged over time. Some of these
            # shouldn't change between boots, but the whole point of M&C is to be
            # sure ...

            if index == 0:
                hostname = socket.gethostname()
                ip_address = get_ip_address()
                system_time = Time.now()
                num_cores = os.sysconf("SC_NPROCESSORS_ONLN")
                cpu_load_pct = os.getloadavg()[1] / num_cores * 100.0
                uptime_days = (time.time() - psutil.boot_time()) / 86400.0

                memory_size_gb = vmem.total / 1024**3  # bytes => GiB

                # We only track disk usage on the root filesystem partition. We could
                # potentially use `psutil.disk_partitions(all=False)` to try to track
                # all physical disks. But the most important non-root disks to monitor
                # are the pots, and the Librarian reports their status to M&C through
                # specialized channels.

                disk = psutil.disk_usage("/")
                disk_size_gb = disk.total / 1024**3  # bytes => GiB
                disk_space_pct = (
                    disk.percent
                )  # note, this is misnamed a bit - it's the % used

                # Compute the longer averages. We have advanced `index` and
                # `prev_index` so that the differences below give the total number
                # of bytes transferred since the last report.

                memory_used_pct = (mem_buf.mean() / 1024**3) * 100.0 / memory_size_gb

                tx_bytes = tx_buf[prev_index] - tx_buf[index]
                rx_bytes = rx_buf[prev_index] - rx_buf[index]
                network_bandwidth_mbs = (
                    (tx_bytes + rx_bytes) / 1024**2 / (now - last_report)
                )

                # Submit

                session.add_server_status(
                    args.subsystem,
                    hostname,
                    ip_address,
                    system_time,
                    num_cores,
                    cpu_load_pct,
                    uptime_days,
                    memory_used_pct,
                    memory_size_gb,
                    disk_space_pct,
                    disk_size_gb,
                    network_bandwidth_mbs,
                )
                session.commit()
                session.add_daemon_status(
                    "mc_server_status_daemon", hostname, Time.now(), "good"
                )
                session.commit()

                last_report = now

            time.sleep(MONITORING_INTERVAL)
    except KeyboardInterrupt:
        pass
    except Exception:
        session.add_daemon_status(
            "mc_server_status_daemon", hostname, Time.now(), "errored"
        )
        session.commit()
        raise
