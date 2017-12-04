# -*- mode: python; coding: utf-8 -*-
# Copyright 2016-2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Some low-level configuration management utility functions.

"""

from __future__ import print_function
import os.path
import subprocess
from hera_mc import mc
from astropy.time import Time
from astropy.time import TimeDelta

PAST_DATE = '2000-01-01'


def get_cm_repo_git_hash(mc_config_path=None, cm_csv_path=None):
    """
    Get the current cm_version for recording with antenna locations.
    """
    if cm_csv_path is None:
        cm_csv_path = mc.get_cm_csv_path(mc_config_file=mc_config_path)
        if cm_csv_path is None:
            raise ValueError('No cm_csv_path defined in mc_config file.')

    git_hash = subprocess.check_output(['git', '-C', cm_csv_path, 'rev-parse', 'HEAD'],
                                       stderr=subprocess.STDOUT).strip()
    return git_hash


def future_date():
    """
    Future is defined here, since defining a far FUTURE_DATE typically gives a
    warning about UTC vs UT1 etc
    """
    return Time.now() + TimeDelta(300, format='jd')


def log(msg, **kwargs):
    fp = open(mc.cm_log_file, 'a')
    dt = Time.now()
    fp.write('-------------------' + str(dt.datetime) + '  ' + msg +
             '-------------------\n\n')
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


def make_part_key(hpn, rev):
    return ":".join([hpn, rev]).strip()


def split_part_key(key):
    return key.split(':')[0], key.split(':')[1]


def make_connection_key(hpn, rev, port, start_gps):
    return ":".join([hpn, rev, port, str(start_gps)]).strip()


def split_connection_key(key):
    ks = key.split(':')
    return ks[0], ks[1], ks[2], ks[3]


def stringify(X):
    if X is None:
        return None
    if isinstance(X, str):
        return X
    if isinstance(X, list):
        return ','.join(X)
    return str(X)


def listify(X):
    if X is None:
        return None
    if isinstance(X, (str, unicode)) and ',' in X:
        return X.split(',')
    if isinstance(X, list):
        return X
    return [X]


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
    the function `get_astropytime`.

    """
    parser.add_argument(
        '--date', help="UTC YYYY/MM/DD or '<' or '>' or 'n/a' or 'now' [now]",
        default='now')
    parser.add_argument(
        '--time', help="UTC hh:mm or float (hours), must include --date if use --time", default=0.0)


def get_astropytime(_date, _time=0):
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
            return_date = future_date()
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
            if ':' in s_time:
                data = s_time.split(':')
                add_time = float(data[0]) * 3600.0 + float(data[1]) * 60.0
                if len(data) == 3:
                    add_time += float(data[2])
            else:
                try:
                    add_time = float(_time) * 3600.0
                except ValueError:
                    raise ValueError('Invalid format:  time should be H[:M[:S]] '
                                     '(HMS can be float or int)')
        if return_date is not None:
            return_date += TimeDelta(add_time, format='sec')
    return return_date


def put_keys_in_numerical_order(keys):
    """
    Takes a list of hookup keys in the format of prefix+number:revision and puts them in number order.
    Returns the ordered list of keys
    """
    keylib = {}
    n = None
    for k in keys:
        colon = k.find(':')
        for i in range(len(k)):
            try:
                n = int(k[i:colon])
                break
            except ValueError:
                continue
        if n in keylib.keys():
            dup_key = keylib[n][0] + str(n) + keylib[n][1]
            return keys
        keylib[n] = [k[:i], k[colon:]]
    if not len(keylib.keys()):
        return keys
    keyordered = []
    for n in sorted(keylib.keys()):
        kre = keylib[n][0] + str(n) + keylib[n][1]
        keyordered.append(kre)
    return keyordered


def get_date_from_pair(d1, d2, ret='earliest'):
    """
    Returns either the earliest or latest of two dates.  This handles either ordering
    and when either or both are None.
    """
    if d1 is None and d2 is None:
        return None
    if ret == 'earliest':
        if d1 is None:
            return d2
        elif d2 is None:
            return d1
        else:
            return d1 if d1 < d2 else d2
    elif ret == 'latest':
        if d1 is None:
            return d1
        elif d2 is None:
            return d2
        else:
            return d1 if d1 > d2 else d2
    else:
        raise ValueError("Must supply earliest/latest.")


def get_displayTime(display):
    if isinstance(display, str):
        if display.lower() == 'now':
            d = Time.now()
        else:
            d = display
    elif display is None:
        d = 'None'
    elif not isinstance(display, Time):
        d = 'N/A'
    else:
        d = display
    if isinstance(d, Time):
        d = "{:%Y-%m-%d %H:%M:%S}".format(d.datetime)
    return d


def get_stopdate(stop_date):
    if isinstance(stop_date, Time):
        return stop_date
    else:
        return future_date()


def is_active(at_date, start_date, stop_date):
    stop_date = get_stopdate(stop_date)
    return at_date >= start_date and at_date <= stop_date


def query_default(a, args):
    vargs = vars(args)
    default = vargs[a]
    s = '%s [%s]:  ' % (a, str(default))
    v = raw_input(s)
    if len(v) == 0:
        v = default
    elif v.lower() == 'none':
        v = None
    return v


def query_yn(s, default='y'):
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
        ans = query_yn(s)
    return ans[0] == 'y'
