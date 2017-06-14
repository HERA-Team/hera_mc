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
FUTURE_DATE = '2025-12-31'

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


def add_date_time_args(parser):
    """Add standardized "--date" and "--time" arguments to an ArgParser object.
    Their values should then be converted into a Python DateTime object using
    the function `_get_datetime`.

    """
    parser.add_argument(
        '--date', help="UTC YYYY/MM/DD or '<' or '>' or 'n/a' or 'now' [now]", default='now')
    parser.add_argument(
        '--time', help="UTC hh:mm or '<' or '>' or 'n/a' or 'now' [now]", default='now')


def _get_datetime(_date, _time=0):
    add_time = 0.
    return_date = None
    if isinstance(_date,Time):
        return_date = _date
    elif _date is None:
        return_date = None
    else:
        if _date == '<':
            return_date = Time(PAST_DATE,scale='utc')
        elif _date == '>':
            return_date = Time(FUTURE_DATE,scale='ut1')
        elif _date.lower().replace('/','') == 'na' or _date.lower()=='none':
            return_date = None
        elif _date.lower() == 'now':
            return_date = Time.now()
        elif _date is not None:
            _date = _date.replace('/','-')
            try:
                return_date = Time(_date,scale='utc')
            except ValueError:
                raise ValueError('Invalid format:  date should be YYYY/M/D or YYYY-M-D')
            if ':' in str(_time):
                data = _time.split(':')
                add_time = float(data[0])*3600.0 + float(data[1])*60.0
                if len(data) == 3:
                    add_time+=float(data[2])
            else:
                try:
                    add_time = float(_time)*3600.0
                except ValueError:
                    raise ValueError('Invalid format:  time should be H[:M[:S]] (HMS can be float or int)')
        if return_date is not None:
            return_date += TimeDelta(add_time,format='sec')
    return return_date

def _get_datekeystring(_datetime):
    return "{:%Y%m%d-%H%M}".format(_datetime.datetime)

def _get_displayTime(display):
    if type(display)==str:
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
    if isinstance(_stop_date,Time):
        return _stop_date
    else:
        return Time(FUTURE_DATE, scale='ut1')

def _is_active(current, _start_date, _stop_date):
    _stop_date = _get_stopdate(_stop_date)
    return current >= _start_date and current <= _stop_date

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
