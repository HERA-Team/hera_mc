# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Some dumb low-level configuration management utility functions.

"""

from __future__ import print_function

import datetime

def _get_datetime(_date,_time):
    if _date.lower() == 'now':
        dt_d = datetime.datetime.now()
    else:
        data = _date.split('/')
        dt_d = datetime.datetime(int(data[2])+2000,int(data[0]),int(data[1]))
    if _time.lower() == 'now':
        dt_t = datetime.datetime.now()
    else:
        data = _time.split(':')
        dt_t = datetime.datetime(dt_d.year,dt_d.month,dt_d.day,int(data[0]),int(data[1]),0)
    dt = datetime.datetime(dt_d.year,dt_d.month,dt_d.day,dt_t.hour,dt_t.minute)
    return dt

    
def _get_stopdate(_stop_date):
    if _stop_date:
        return _stop_date
    else:
        return datetime.datetime(2020,12,31)

def _is_active(current, _start_date, _stop_date):
    _stop_date = _get_stopdate(_stop_date)
    if current > _start_date and current < _stop_date:
        is_active=True
    else:
        is_active=False
    return is_active

def _query_default(a,args):
    vargs = vars(args)
    default = vargs[a]
    s = '%s [%s]:  ' % (a,str(default))
    v = raw_input(s).strip()
    if len(v) == 0:
        v = default
    return v

def _query_yn(s,default='y'):
    if default:
        s+=' ['+default+']'
    s+=':  '
    ans = raw_input(s)
    if len(ans)==0 and default:
        ans = default
    elif len(ans)>0:
        ans = ans.lower()
    else:
        print('No answer provided.')
        ans = _query_yn(s,default)
    if ans[0]=='y':
        return True
    else:
        return False
