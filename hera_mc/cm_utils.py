# -*- mode: python; coding: utf-8 -*-
# Copyright 2016-2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Some low-level configuration management utility functions.

"""

from __future__ import print_function

from hera_mc import mc
from astropy.time import Time
from astropy.time import TimeDelta
import os.path

PAST_DATE = '2000-01-01'


def _future_date():
    """
    Future is defined here, since defining a far FUTURE_DATE typically gives a warning about
    UTC vs UT1 etc
    """
    return Time.now() + TimeDelta(100, format='jd')


def _log(msg, **kwargs):
    fp = open(mc.cm_log_file, 'a')
    dt = Time.now()
    fp.write('-------------------' + str(dt.datetime) + '  ' + msg + '-------------------\n\n')
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


def _make_part_key(hpn, rev):
    return ":".join([hpn, rev]).strip()
def _split_part_key(key):
    return key.split(':')[0], key.split(':')[1]

def _make_connection_key(hpn, rev, port, start_gps):
    return ":".join([hpn, rev, port, str(start_gps)]).strip()
def _split_connection_key(key):
    ks = key.split(':')
    return ks[0], ks[1], ks[2], ks[3]

def add_verbosity_args(parser):
    """Add a standardized "--verbosity" argument to an ArgParser object. Supported
    values are "l", "m", and "h", which presumably stand for "low", "medium",
    and "high".

    The function name is plural because it's conceivable that in the future we might
    want to provide multiple arguments related to this general topic.

    """
    parser.add_argument('-v', '--verbosity', help="Verbosity level: 'l', 'm', or 'h'. [h].",
                        choices=['l', 'm', 'h'], default="h")


def add_date_time_args(parser):
    """Add standardized "--date" and "--time" arguments to an ArgParser object.
    Their values should then be converted into a Python DateTime object using
    the function `_get_datetime`.

    """
    parser.add_argument(
        '--date', help="UTC YYYY/MM/DD or '<' or '>' or 'n/a' or 'now' [now]", default='now')
    parser.add_argument(
        '--time', help="UTC hh:mm or float (hours)", default=0.0)


def _get_datetime(_date, _time=0):
    """
    Take in various incarnations of _date/_time and return an astropy.Time object
    """

    add_time = 0.
    return_date = None
    if isinstance(_date, Time):
        return_date = _date
    elif _date is None or _date is False:
        return_date = _date
    else:
        if _date == '<':
            return_date = Time(PAST_DATE, scale='utc')
        elif _date == '>':
            return_date = _future_date()
        elif _date.lower().replace('/', '') == 'na' or _date.lower() == 'none':
            return_date = None
        elif _date.lower() == 'now':
            return_date = Time.now()
        elif _date is not None:
            _date = _date.replace('/', '-')
            try:
                return_date = Time(_date, scale='utc')
            except ValueError:
                raise ValueError('Invalid format:  date should be YYYY/M/D or YYYY-M-D')
            s_time = str(_time)
            if ':' in str(_time):
                data = _time.split(':')
                add_time = float(data[0]) * 3600.0 + float(data[1]) * 60.0
                if len(data) == 3:
                    add_time += float(data[2])
            else:
                try:
                    add_time = float(_time) * 3600.0
                except ValueError:
                    raise ValueError('Invalid format:  time should be H[:M[:S]] (HMS can be float or int)')
        if return_date is not None:
            return_date += TimeDelta(add_time, format='sec')
    return return_date


def _get_datekeystring(_datetime):
    return "{:%Y%m%d-%H%M}".format(_datetime.datetime)


def _get_displayTime(display):
    if type(display) == str:
        d = display
    elif display is None:
        d = 'None'
    elif not isinstance(display, Time):
        print('Non astropy time not supported')
        d = 'N/A'
    else:
        d = "{:%Y-%m-%d %H:%M:%S}".format(display.datetime)
    return d


def _get_stopdate(_stop_date):
    if isinstance(_stop_date, Time):
        return _stop_date
    else:
        return _future_date()


def _is_active(current, _start_date, _stop_date):
    _stop_date = _get_stopdate(_stop_date)
    return current >= _start_date and current <= _stop_date


def _return_TF(x):
    """
    This returns a boolean based on strings from input args
    For y/n queries, use _query_yn below.
    """
    if x or x[0].upper == 'T' or x[0].upper == 'Y':
        TF = True
    else:
        TF = False
    return TF


def _query_default(a, args):
    vargs = vars(args)
    default = vargs[a]
    s = '%s [%s]:  ' % (a, str(default))
    v = raw_input(s).strip()
    if len(v) == 0:
        v = default
    return v


def _query_yn(s, default='y'):
    if default:
        s += ' [' + default + ']'
    s += ':  '
    ans = raw_input(s)
    if len(ans) == 0 and default:
        ans = default.lower()
    elif len(ans) > 0:
        ans = ans.lower()
    else:
        print('No answer provided.')
        ans = _query_yn(s)
    return ans[0] == 'y'
