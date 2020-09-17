#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2020 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""System watch-dogs."""


def read_forward_list():
    fwd = []
    with open('~/.forward', 'r') as fp:
        for line in fp:
            fwd.append(line.strip())


def node_temperature(at_date=None, temp_threshold=45.0, time_threshold=1.0,
                     To=None, session=None):
    """
    Check node for over-temperature.

    This checks all of the temperature sensors in active nodes, and sends an email
    if any sensor exceeds that provided threshold.

    Parameters
    ----------
    at_date : anything understandable by get_astropytime
        If None, use values at latest time.  If valid Time, use nearest value before.
    temp_threshold : float
        Threshold temperature in Celsius
    time_threshold : float
        Time in days for "current" values.
    To : list or None
        List of e-mail addresses.  If None, uses the addresses in ~/.forward
    session : session object or None
        If None, it will start a new session on the database
    """
    from . import node, cm_utils, cm_active

    if session is None:  # pragma: no cover
        from . import mc
        db = mc.connect_to_mc_db(None)
        session = db.sessionmaker()

    if at_date is None:
        use_last = True
        at_date = cm_utils.get_astropytime('now')
    else:
        use_last = False
        at_date = cm_utils.get_astropytime(at_date)
    gps_time = at_date.gps
    active_parts = cm_active.ActiveData()
    active_parts.load_parts(at_date)
    active_nodes = [int(cm_utils.split_part_key(key)[0][1:])
                    for key in active_parts.get_hptype('node')]

    active_temps = {}
    msg_header = 'Over-temperature (>{} C)'.format(temp_threshold)
    msg = '{}'.format(msg_header)
    for node_num in active_nodes:
        if use_last:
            nds = (session.query(node.NodeSensor)
                   .filter(node.NodeSensor.node == node_num)
                   .order_by(node.NodeSensor.time.desc()).first())
        else:
            nds = (session.query(node.NodeSensor)
                   .filter(node.NodeSensor.time < gps_time & node.NodeSensor.node == node_num)
                   .order_by(node.NodeSensor.time.desc()).first())
        if nds is None or (gps_time - nds.time) / 86400.0 > time_threshold:
            continue
        active_temps[node_num] = []
        for _t in [nds.top_sensor_temp, nds.middle_sensor_temp,
                   nds.bottom_sensor_temp, nds.humidity_sensor_temp]:
            if _t is None:
                active_temps[node_num].append(-99.)
            else:
                active_temps[node_num].append(_t)
        highest_temp = max(active_temps[node_num])
        if highest_temp > temp_threshold:
            msg += "\t{:02d}:  {}\n".format(node_num, ', '.join(active_temps[node_num]))
    if msg != msg_header:
        import smtplib
        From = 'hera@lists.berkeley.edu'
        Subject = msg_header
        if To is None:
            To = read_forward_list()
        server = smtplib.SMTP('localhost')
        msg_sent = "From: {}\nTo: {}\nSubject: {}\n{}".format(From, ', '.join(To), Subject, msg)
        server.sendmail(From, To, msg_sent)
