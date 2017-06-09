# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
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
    dt = datetime.datetime.now()
    fp.write('-------------------' + str(dt) + '  ' + msg + '-------------------\n\n')
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


def _get_datetime(_date, _time=0):
    if _date == '<' or _time == '<':
        return_date = Time(PAST_DATE,scale='utc')
    elif _date == '>' or _time == '>':
        return_date = Time(FUTURE_DATE,scale='ut1')
    elif _date.lower().replace('/','') == 'na' or str(_time).replace('/','').lower() == 'na':
        return_date = None
    elif _date.lower() == 'now' or str(_time).lower() == 'now':
        return_date = Time.now()
    else:
        _date = _date.replace('/','-')
        try:
            return_date = Time(_date,scale='utc')
        except ValueError:
            return_date = ValueError
        else:
            if ':' in str(_time):
                data = _time.split(':')
                _time = float(data[0])*3600.0 + float(data[1])*60.0
                if len(data) == 3:
                    _time+=float(data[2])
            else:
                try:
                    _time = float(_time)*3600.0
                except ValueError:
                    return_date = ValueError
    if return_date == ValueError:
        print('Invalid format:  date should be YYYY/M/D or YYYY-M-D and time H[:M[:S]] (HMS can be float or int):   ',_date,_time)
        raise ValueError
    elif return_date is not None:
        return_date += TimeDelta(_time,format='sec')
    return return_date


def _get_datekeystring(_datetime):
    return "{:%Y%m%d-%H%M}".format(_datetime)


def _get_stopdate(_stop_date):
    if isinstance(_stop_date,Time):
        return _stop_date
    else:
        return Time('2025-12-31', scale=UT1)


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
