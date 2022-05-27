#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2020 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""System watch-dogs."""


def read_forward_list():  # pragma: no cover
    """Read in emails from .forward file."""
    fwd = []
    with open("~/.forward", "r") as fp:
        for line in fp:
            fwd.append(line.strip())


def send_email(
    subject, msg, to_addr=None, from_addr="hera@lists.berkeley.edu", skip_send=False
):
    """
    Send an email message, unless skip_send is True (for testing).

    Parameters
    ----------
    subject : str
        Subject of email.
    msg : str
        Message to send.
    to_addr : list or None
        If None, it will read the list in the .forward file.
    from_addr : str
        From address to use
    skip_send : bool
        If True, it will just return the composed message and not send it.

    Returns
    -------
    EmailMessage

    """
    import smtplib
    from email.message import EmailMessage

    if to_addr is None:  # pragma: no cover
        to_addr = read_forward_list()
    email = EmailMessage()
    email.set_content(msg)
    email["From"] = from_addr
    email["To"] = to_addr
    email["Subject"] = subject
    if not skip_send:  # pragma: no cover
        server = smtplib.SMTP("localhost")
        server.send_message(email)
        server.quit()
    return email


def node_temperature(
    at_date=None,
    at_time=None,
    float_format=None,
    temp_threshold=45.0,
    time_threshold=1.0,
    To=None,
    testing=False,
    session=None,
):
    """
    Check node for over-temperature.

    This checks all of the temperature sensors in active nodes, and sends an email
    if any sensor exceeds that provided threshold.

    Parameters
    ----------
    at_date : anything understandable by get_astropytime
        If None, use values at latest time.  If valid Time, use nearest value before.
    at_time : anything understandable by get_astropytime
        Used for appropriate forms of 'at_date' for get_astropytime, ignored if at_date
        is a float or contains time information.
    float_format : str or None
        If at_date is unix or gps or jd day.
    temp_threshold : float
        Threshold temperature in Celsius
    time_threshold : float
        Time in days for "current" values.
    To : list or None
        List of e-mail addresses.  If None, uses the addresses in ~/.forward
    testing : bool
        Boolean to skip sending the actual e-mail and return a string (for testing)
    session : session object or None
        If None, it will start a new session on the database

    """
    from . import mc, node, cm_utils, cm_active

    if at_date is None:
        use_last = True
        at_date = cm_utils.get_astropytime("now")
    else:
        use_last = False
        at_date = cm_utils.get_astropytime(at_date, at_time, float_format)
    gps_time = at_date.gps
    with mc.MCSessionWrapper(session=session) as session:
        active_parts = cm_active.ActiveData(session=session)
        active_parts.load_parts(at_date)
        active_nodes = sorted(
            [
                int(cm_utils.split_part_key(key)[0][1:])
                for key in active_parts.get_hptype("node")
            ]
        )
        active_temps = {}
        msg_header = (
            "WARNING: Over-temperature (>{:.1f} C, <{:.2f} days)\n"
            "\n\tNode   Top     Mid     Bot     Hum"
            "\n\t----   ----    ----    ----    ----".format(
                float(temp_threshold), float(time_threshold)
            )
        )
        msg = "{}".format(msg_header)
        for node_num in active_nodes:
            if use_last:
                nds = (
                    session.query(node.NodeSensor)
                    .filter(node.NodeSensor.node == node_num)
                    .order_by(node.NodeSensor.time.desc())
                    .first()
                )
            else:
                nds = (
                    session.query(node.NodeSensor)
                    .filter(
                        (node.NodeSensor.node == node_num)
                        & (node.NodeSensor.time < gps_time)
                    )
                    .order_by(node.NodeSensor.time.desc())
                    .first()
                )
            if nds is None or (gps_time - nds.time) / 86400.0 > time_threshold:
                continue
            active_temps[node_num] = []
            for sensor_temp in [
                nds.top_sensor_temp,
                nds.middle_sensor_temp,
                nds.bottom_sensor_temp,
                nds.humidity_sensor_temp,
            ]:
                if sensor_temp is None:
                    active_temps[node_num].append(-99.9)
                else:
                    active_temps[node_num].append(sensor_temp)
            highest_temp = max(active_temps[node_num])
            if highest_temp > temp_threshold:
                htlist = []
                for this_temp in active_temps[node_num]:
                    if this_temp > temp_threshold:
                        ht = "[{:4.1f}]".format(this_temp)
                    elif this_temp < -99.0:
                        ht = "  -   "
                    else:
                        ht = " {:4.1f} ".format(this_temp)
                    htlist.append(ht)
                msg += "\n\t {:02d}   {}".format(node_num, "  ".join(htlist))

    if msg != msg_header:
        subject = msg_header.splitlines()[0]
        return send_email(subject, msg, To, skip_send=testing)
