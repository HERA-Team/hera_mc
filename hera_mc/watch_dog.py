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


def node_verdict(
    age_out=3800, To=None, return_as="node_info", testing=False, redishost="redishost"
):
    """
    Check redis for latest node power command results.

    This will check redis for the results from the latest node power command
    (see hera_node_mc repo) and send an email if update is less than age_out
    seconds.

    Parameters
    ----------
    age_out : int
        Number of seconds under which to send an update email
    To : str
        csv-list of email accounts to use.  None uses .forward
    return_as : str
        Either 'node_info' or 'email' to specify which value to return
    testing : bool
        Flag for testing, so won't send email.
    redishost :  str
        Name of redis server to connect to

    Return
    ------
    The return dictionary contains the results keyed on node.
    """
    if return_as not in ["node_info", "email"]:
        raise ValueError("Must be returned as 'node_info' or 'email'")
    import redis
    import time

    connection_pool = redis.ConnectionPool(host=redishost, decode_responses=True)
    r = redis.StrictRedis(connection_pool=connection_pool, charset="utf-8")
    node_info = {}
    for key in r.keys():
        if "valid:node" in key:
            node = int(key.split(":")[2])
            node_info.setdefault(node, {})
            node_info[node]["valid"] = True if int(r.get(key)) else False
        elif "verdict:node" in key:
            node = int(key.split(":")[2])
            node_info.setdefault(node, {})
            hw = key.split(":")[3]
            node_info[node][hw] = r.hgetall(key)
    node_list = sorted(node_info.keys())
    node_info["param"] = r.hgetall("verdict")
    this_email = None
    if node_info["param"]:
        this_time = float(node_info["param"]["time"])
        subject = "Node verdict:  mode '{}', timeout {}, time {}".format(
            node_info["param"]["mode"], node_info["param"]["timeout"], int(this_time)
        )
        msg = ""
        if int(time.time() - this_time) < age_out:
            for node in node_list:
                s = "Node {} is{}valid\n".format(
                    node, " " if node_info[node]["valid"] else " not "
                )
                for hw, val in node_info[node].items():
                    if hw != "valid":
                        s += "\t{}: {}\n".format(hw, val)
                s += "\n"
                msg += s
        if len(msg):
            msg = subject + "\n\n" + msg
            this_email = send_email(subject, msg, To, skip_send=testing)
    if return_as == "node_info":
        return node_info
    elif return_as == "email":
        return this_email


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
    from . import node, cm_utils, cm_active

    if session is None:  # pragma: no cover
        from . import mc

        db = mc.connect_to_mc_db(None)
        session = db.sessionmaker()

    if at_date is None:
        use_last = True
        at_date = cm_utils.get_astropytime("now")
    else:
        use_last = False
        at_date = cm_utils.get_astropytime(at_date, at_time, float_format)
    gps_time = at_date.gps
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
