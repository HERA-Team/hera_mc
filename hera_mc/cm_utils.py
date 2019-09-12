# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Some low-level configuration management utility functions.

"""

from __future__ import absolute_import, division, print_function

import os.path
import subprocess
import six
from astropy.time import Time
from astropy.time import TimeDelta
import datetime

from . import mc

PAST_DATE = '2000-01-01'
all_hera_zone_prefixes = ['HH', 'HA', 'HB']  # This is for hookup_cache to get all
default_station_prefixes = ['HH', 'HA', 'HB']  # This is for defaults for sys etc.


def get_cm_repo_git_hash(mc_config_path=None, cm_csv_path=None, testing=False):
    """
    Get the current cm_version for recording with antenna locations.

    Parameters
    ----------
    mc_config_path : str or None
        Path to configuration file.  If None, uses default.
    cm_csv_path : str or None
        Path to the cm csv file updates.  If None, uses default.
    testing : bool
        Flag to allow for testing.

    Returns
    -------
    str
        git hash of cm repository
    """
    if cm_csv_path is None or testing:
        cm_csv_path = mc.get_cm_csv_path(mc_config_file=mc_config_path)
        if cm_csv_path is None:
            raise ValueError('No cm_csv_path defined in mc_config file.')

    git_hash = subprocess.check_output(['git', '-C', cm_csv_path, 'rev-parse', 'HEAD'],
                                       stderr=subprocess.STDOUT).strip()
    return git_hash


def log(msg, **kwargs):
    """
    Writes to the standard cm log file.

    Parameters
    ----------
    msg : str
        log message to write.
    **kwargs : dict
        keywords and arguments to log.
    """
    fp = open(mc.cm_log_file, 'a')
    dt = Time.now()
    fp.write('-------------------' + str(dt.datetime) + '  ' + msg
             + '-------------------\n\n')
    for key, value in kwargs.items():
        if key == 'args':
            fp.write('--args\n\t')
            vargs = vars(value)
            for k, v in vargs.items():
                fp.write(str(k) + ':  ' + str(v) + ';  ')
            fp.write('\n\n')
        elif key == 'data_dict':
            fp.write('--data\n\t')
            for k, v in value.items():
                fp.write('    ' + k + '  ')
                for d in v:
                    fp.write(str(d) + ';  ')
                fp.write('\n\n')
        else:
            fp.write('--other\n\t')
            fp.write(str(key) + ':  ' + str(value) + '\n\n')
    fp.close()


# #######################################Key stuff
system_wide_key = '__Sys__'


def make_part_key(hpn, rev, port=None):
    """
    Returns the standard part key of hpn:rev[:port].  Port is only
    included if not None

    Parameters
    ----------
    hpn : str
        HERA part number.  If None, it returns the system_wide_key
    rev : str
        HERA part revision
    port : str
        HERA port name

    Returns
    -------
    str
        key
    """
    if hpn is None:
        return system_wide_key

    if port is None:
        return ":".join([hpn.upper(), rev.upper()])

    return ":".join([hpn.upper(), rev.upper(), port.upper()])


def split_part_key(key):
    """
    Splits the standard part key.  Only returns port if present in key.

    Parameters
    ----------
    key : str
        Standard part key as hpn:rev

    Returns
    -------
    tuple
        hpn, rev, [,port]
    """

    split_key = key.split(":")

    if len(split_key) == 2:
        return split_key[0], split_key[1]

    return split_key[0], split_key[1], split_key[2]


def make_connection_key(hpn, rev, port, start_gps):
    """
    Returns the standard connection key of hpn:rev:port:gps_second

    Parameters
    ----------
    hpn : str
        HERA part number.  If None, it returns the system_wide_key
    rev : str
        HERA part revision
    port : str
        HERA port
    start_gps : str or int
        Start time as gps second

    Returns
    -------
    str
        key
    """
    return ":".join([hpn, rev, port, str(start_gps)]).strip()


def split_connection_key(key):
    """
    Splits the standard connection key.

    Parameters
    ----------
    key : str
        Standard part key as hpn:rev:port:gps

    Returns
    -------
    tuple
        hpn, rev, port, gps
    """
    ks = key.split(':')
    return ks[0], ks[1], ks[2], ks[3]


def stringify(X):
    """
    "Stringify" the input, hopefully sensibly.

    Parameters
    ----------
    X
        Thing to be stringified.

    Returns
    -------
    str
    """
    if X is None:
        return None
    if isinstance(X, six.string_types):
        return X
    if isinstance(X, list):
        return ','.join(X)
    return str(X)


def listify(X):
    """
    "Listify" the input, hopefully sensibly.

    Parameters
    ----------
    X
        Thing to be listified.

    Returns
    -------
    str or None
    """
    if X is None:
        return None
    if isinstance(X, six.string_types):
        return X.split(',')
    if isinstance(X, list):
        return X
    return [X]


def match_listify(req1, req2):
    """
    Makes sure that the two requests are both lists and that they are
    equal in length.  Raises an Error if can't match.

    Parameters
    ----------
    req1, req1 : lists
        Two lists to be matched.

    Returns
    -------
    tuple of lists
        Matched lists
    """
    list1 = listify(req1)
    if isinstance(req2, list):
        list2 = req2
    else:
        list2 = len(list1) * [req2]
    if len(list1) != len(list2):
        raise ValueError("Unmatched list requests.")
    return list1, list2


def add_verbosity_args(parser):
    """Add a standardized "--verbosity" argument to an ArgParser object.
    Returns the number of 'v's (-v=1 [low], -vv=2 [medium], -vvv=3 [high]) or the supplied integer.
    Defaults to 1
    Parsed by 'parse_verbosity' function

    Parameters
    ----------
    parser : object
        Parser object
    """
    parser.add_argument('-v', '--verbosity', help="Verbosity level -v -vv -vvv. [-v].",
                        nargs='?', default=1)


def parse_verbosity(vargs):
    """
    Parse the verbosity argument to produce a standardized integer for verbosity.

    Parameters
    ----------
    vargs
        Parser argument

    Returns
    -------
    int
        Integer characterizing verbosity level
    """
    try:
        return int(vargs)
    except (ValueError, TypeError):
        pass
    if vargs is None:
        return 1
    if vargs.count('v'):
        return vargs.count('v') + 1
    raise ValueError("Invalid argument to verbosity.")


# ##############################################DATE STUFF
def add_date_time_args(parser):
    """Add standardized "--date" and "--time" arguments to an ArgParser object.
    Their values should then be converted into a Python DateTime object using
    the function `get_astropytime`.

    Parameters
    ----------
    parser : object
        Parser object
    """
    parser.add_argument(
        '--date', help="UTC YYYY/MM/DD or '<' or '>' or 'n/a' or 'now' [now]",
        default='now')
    parser.add_argument(
        '--time', help="UTC hh:mm or float (hours), must include --date if use --time", default=0.0)


def is_active(at_date, start_date, stop_date):
    """
    Checks to see if at_date is within start/stop.

    Parameters
    ----------
    at_date : str, int, Time, None
        Date to check - anything intelligible by cm_utils.get_astropytime
    start_date : str, int, Time
        Start date to use - anything intelligible by cm_utils.get_astropytime
    stop_date : str, int, Time
        Stop date to use - anything intelligible by cm_utils.get_astropytime
    """
    if at_date is None:
        return True
    at_date = get_astropytime(at_date).gps
    start_date = get_astropytime(start_date).gps
    stop_date = get_stopdate(stop_date).gps
    return at_date >= start_date and at_date <= stop_date


def future_date():
    """
    Future is defined here, since defining a far FUTURE_DATE typically gives a
    warning about UTC vs UT1 etc

    Returns
    -------
    Time
        Time 300 days in the future.
    """
    return Time.now() + TimeDelta(300, format='jd')


def get_stopdate(stop_date):
    """
    Provide an appropriate stop date.  If None, provides future_date

    Parameters
    ----------
    stop_date : str, int, None, Time

    Returns
    -------
    Time
    """
    if stop_date is None:
        return future_date()
    return get_astropytime(stop_date)


def get_time_for_display(display):
    """
    Provide a reader-friendly time string for any time parse-able by get_astropytime -
    if that results in None, then the string None is displayed.

    Parameters
    ----------
    display : str, int, None, Time

    Returns
    -------
    str
        Readable string of time in display
    """
    d = get_astropytime(display)

    if d is None:
        d = 'None'
    elif isinstance(d, Time):
        d = "{:%Y-%m-%d %H:%M:%S}".format(d.datetime)
    return d


def get_astropytime(adate, atime=0):
    """
    Take in various incarnations of adate/atime and return an astropy.Time object or None.
    No time zone is allowed.

    Returns:  either astropy Time or None

    Parameters
    ----------
    adate :  a date in various formats:
                return astropy Time
                    astropy Time:  just gets returned
                    datetime: just gets converted
                    int, long, float:  interpreted as gps_second or julian date
                                       depending on appropriate range
                    string:  '<' - PAST_DATE
                             '>' - future_date()
                             'now' or 'current'
                             'YYYY/M/D' or 'YYYY-M-D'
                return None:
                    string:  'none' return None
                    None/False:  return None
    atime : a time in various formats, ignored if time information is provided in adate
                float, int:  hours in decimal time
                string:  HH[:MM[:SS]] or hours in decimal time

    Returns
    -------
    astropy.Time or None
    """

    if isinstance(adate, Time):
        return adate
    if isinstance(adate, datetime.datetime):
        return Time(adate, format='datetime')
    if adate is None or adate is False:
        return None
    try:
        adate = float(adate)
    except ValueError:
        pass
    if isinstance(adate, float):
        if adate > 1000000000.0:
            return Time(adate, format='gps')
        if adate > 2400000.0 and adate < 2500000.0:
            return Time(adate, format='jd')
        raise ValueError('Invalid format:  date as a number should be gps time or julian date, not {}.'.format(adate))
    if isinstance(adate, str):
        if adate == '<':
            return Time(PAST_DATE, scale='utc')
        if adate == '>':
            return future_date()
        if adate.lower() == 'now' or adate.lower() == 'current':
            return Time.now()
        if adate.lower() == 'none':
            return None
        adate = adate.replace('/', '-')
        try:
            return_date = Time(adate, scale='utc')
        except ValueError:
            raise ValueError('Invalid format:  date should be YYYY/M/D or YYYY-M-D, not {}'.format(adate))
        try:
            atime = float(atime)
        except ValueError:
            pass
        if isinstance(atime, float):
            return return_date + TimeDelta(atime * 3600.0, format='sec')
        if isinstance(atime, str):
            if ':' not in atime:
                raise ValueError('Invalid format:  time should be H[:M[:S]] (ints or floats)')
            add_time = 0.0
            for i, d in enumerate(atime.split(':')):
                if i > 2:
                    raise ValueError('Time can only be hours[:minutes[:seconds]], not {}.'.format(atime))
                add_time += (float(d)) * 3600.0 / (60.0**i)
            return return_date + TimeDelta(add_time, format='sec')


def put_keys_in_numerical_order(keys):
    """
    Takes a list of hookup keys in the format of prefix[+number]:revision and puts them in number order.
    If no number supplied, it uses 0. If no revision supplied, it uses 'A'.
    Returns the ordered list of keys

    Parameters
    ----------
    keys : list
        List of hookup keys

    Returns
    -------
    list
        Ordered list of keys
    """
    keylib = {}
    for k in keys:
        c = k
        if ':' not in k:
            c = k + ':A'
        colon = c.find(':')
        for i in range(len(c)):
            try:
                n = int(c[i:colon])
                break
            except ValueError:
                n = 0
                continue
        prefix = c[:i]
        rev = c[colon + 1:]
        dkey = (n, prefix, rev)
        keylib[dkey] = k

    keyordered = []
    for k in sorted(keylib.keys()):
        keyordered.append(keylib[k])
    return keyordered


def html_table(headers, table):
    """
    This formats a table into an html table.  Returns a string containing the full html table.

    Parameters
    ----------
    headers : list
        List of header titles
    table : list
        List of rows with data formatted
            [ [row1_entry1, row1_entry2, ..., row1_entry<len(headers)>],
              [row2_...],
              [rowN_...] ]

    Returns
    -------
    str
        String containing the html table
    """
    s_table = '<table border="1">\n<tr>'
    for h in headers:
        s_table += '<th>{}</th>'.format(h)
    s_table += '</tr>\n'
    for tr in table:
        s_table += '<tr>'
        for d in tr:
            f = str(d).replace('<', '&lt ')
            f = f.replace('>', '&gt ')
            s_table += '<td>{}</td>'.format(f)
        s_table += '</tr>\n'
    s_table += '</table>'
    return s_table


def csv_table(headers, table):
    """
    This formats a table into an csv string.  Returns a string containing the full csv table.

    Parameters
    ----------
    headers : list
        List of header titles
    table : list
        List of rows with data formatted
            [ [row1_entry1, row1_entry2, ..., row1_entry<len(headers)>],
              [row2_...],
              [rowN_...] ]

    Returns
    -------
    str
        String containing the csv table
    """
    s_table = ''
    for h in headers:
        s_table += '"{}",'.format(h)
    s_table = s_table.strip(',') + '\n'
    for tr in table:
        for d in tr:
            s_table += '"{}",'.format(d)
        s_table = s_table.strip(',') + '\n'
    return s_table


def query_default(param, args):
    """
    Allows for a parameter to be queried, and return defaults for those not provided.

    Parameters
    ----------
    param : str
        The parameter being queried
    args : object
        Namespace object

    Returns
    -------
    Queried value or default
    """
    vargs = vars(args)
    default = vargs[param]
    if 'unittesting' in vargs.keys():
        v = vargs['unittesting']
    else:  # pragma: no cover
        s = '{} [{}]:  '.format(param, str(default))
        v = six.moves.input(s)
    if len(v) == 0:
        return default
    if v.lower() == 'none':
        return None
    if v.lower() == 'false':
        return False
    if v.lower() == 'true':
        return True
    return v
