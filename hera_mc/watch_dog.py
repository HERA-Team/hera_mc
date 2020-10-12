#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2020 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""System watch-dogs."""
import os.path


def send_message(subject, msg, to_addr=None, from_addr='hera@lists.berkeley.edu', skip_send=False):
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
    str or None
        If skip_send, will return the composed message.
    """
    import smtplib
    if to_addr is None:  # pragma: no cover
        to_addr = read_forward_list()
    msg_to_send = ("From: {}\nTo: {}\nSubject: {}\n{}"
                   .format(from_addr, ', '.join(to_addr), subject, msg))
    if skip_send:
        return msg_to_send
    else:  # pragma: no cover
        server = smtplib.SMTP('localhost')
        server.sendmail(from_addr, to_addr, msg_to_send)


def read_forward_list():  # pragma: no cover
    """Read in emails from .forward file."""
    fwd = []
    with open('~/.forward', 'r') as fp:
        for line in fp:
            fwd.append(line.strip())


def read_hosts_ethers_file(ftype, host, path='/etc', testing=False):
    """
    Read in the hosts or ethers file and send an e-mail on error.

    This returns tw dictionies keyed on either the mac (ethers) or ip (hosts) and the hostnames.
    The valueis a list of corresponding hostnames (or vice versa).  If an error, the first return
    dictionary contains the error messaging.

    Parameters
    ----------
    ftype : str
        File-type: either 'hosts' or 'ethers'
    host : str
        Hostname of server (included in warning message.)
    path : str
        Path to file.
    testing : bool (False) or dict
        If dict, will process testing[ftype]

    Returns
    -------
    dict
        Contains the hosts or ethers information.  If error, contains message.
    """
    if testing:
        file_contents = testing[ftype]
    else:  # pragma: no cover
        with open(os.path.join(path, ftype), 'r') as fp:
            file_contents = fp.read()

    hoeth = {}
    macip = {}
    for line in file_contents.splitlines():
        if line[0] == '#' or len(line) < 12:
            continue
        data = line.split()
        if data[0] in macip.keys():
            return {'Error': True, 'Subject': 'ERROR: Duplicate entry in {}'.format(ftype),
                    'Message': '{} is duplicated in {} file on {}'.format(data[0], ftype, host)}, {}
        macip[data[0]] = []
        for he in data[1:]:
            if '#' in he:  # Stop if you hit #
                break
            if he in hoeth.keys():
                return {'Error': True, 'Subject': 'ERROR: Duplicate entry in {}'.format(ftype),
                        'Message': '{} is duplicated in {} file on {}'.format(he, ftype, host)}, {}
            hoeth[he] = data[0]
            macip[data[0]].append(he)
    return macip, hoeth


def hosts_ethers(path='/etc', To=None, testing=False):
    import socket

    hostname = socket.gethostname()
    if hostname == 'hera-node-head':
        print("Get arduinos/wr in hera_mc rosetta and part_info")
    elif hostname == 'hera-snap-head':
        print("Get snaps in hera_mc rosetta and part_info")
    elif not testing:
        raise ValueError("{} not in [hera-node-head, hera-snap-head]".format(hostname))
    iho, nho = read_hosts_ethers_file('hosts', host=hostname, path=path, testing=testing)
    if 'Error' in iho.keys():
        return send_message(iho['Subject'], iho['Message'], to_addr=To, skip_send=testing)
    meth, neth = read_hosts_ethers_file('ethers', host=hostname, path=path, testing=testing)
    if 'Error' in meth.keys():
        return send_message(meth['Subject'], meth['Message'], to_addr=To, skip_send=testing)
    print("Now need to do the actual checking.")


def node_temperature(at_date=None, at_time=0.0,
                     temp_threshold=45.0, time_threshold=1.0,
                     To=None, testing=False, session=None):
    """
    Check node for over-temperature.

    This checks all of the temperature sensors in active nodes, and sends an email
    if any sensor exceeds that provided threshold.

    Parameters
    ----------
    at_date : anything understandable by get_astropytime
        If None, use values at latest time.  If valid Time, use nearest value before.
    at_time : anything understandable by get_astropytime
        Used for appropriate forms of 'at_date' for get_astropytime
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
        at_date = cm_utils.get_astropytime('now')
    else:
        use_last = False
        at_date = cm_utils.get_astropytime(at_date, at_time)
    gps_time = at_date.gps
    active_parts = cm_active.ActiveData(session=session)
    active_parts.load_parts(at_date)
    active_nodes = sorted([int(cm_utils.split_part_key(key)[0][1:])
                          for key in active_parts.get_hptype('node')])
    active_temps = {}
    msg_header = ('WARNING: Over-temperature (>{:.1f} C, <{:.2f} days)\n'
                  '\n\tNode   Top     Mid     Bot     Hum'
                  '\n\t----   ----    ----    ----    ----'
                  .format(float(temp_threshold), float(time_threshold)))
    msg = '{}'.format(msg_header)
    for node_num in active_nodes:
        if use_last:
            nds = (session.query(node.NodeSensor)
                   .filter(node.NodeSensor.node == node_num)
                   .order_by(node.NodeSensor.time.desc()).first())
        else:
            nds = (session.query(node.NodeSensor)
                   .filter((node.NodeSensor.node == node_num) & (node.NodeSensor.time < gps_time))
                   .order_by(node.NodeSensor.time.desc()).first())
        if nds is None or (gps_time - nds.time) / 86400.0 > time_threshold:
            continue
        active_temps[node_num] = []
        for sensor_temp in [nds.top_sensor_temp, nds.middle_sensor_temp,
                            nds.bottom_sensor_temp, nds.humidity_sensor_temp]:
            if sensor_temp is None:
                active_temps[node_num].append(-99.9)
            else:
                active_temps[node_num].append(sensor_temp)
        highest_temp = max(active_temps[node_num])
        if highest_temp > temp_threshold:
            htlist = []
            for this_temp in active_temps[node_num]:
                if this_temp > temp_threshold:
                    ht = '[{:4.1f}]'.format(this_temp)
                elif this_temp < -99.0:
                    ht = '  -   '
                else:
                    ht = ' {:4.1f} '.format(this_temp)
                htlist.append(ht)
            msg += "\n\t {:02d}   {}".format(node_num, '  '.join(htlist))
    if msg != msg_header:
        return send_message(msg_header.splitlines()[0], msg, To, skip_send=testing)
