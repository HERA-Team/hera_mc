#! /usr/bin/env python

import ue9
import LabJackPython
from time import time, sleep
import hera_mc.mc as mc
import argparse

list_of_registers = range(240, 253, 2)
list_of_registers += range(96, 109, 2)
list_of_registers += range(144, 157, 2)
list_of_registers += range(192, 205, 2)

default_config_file = os.path.expanduser('~/.hera_mc/mc_config.json')
default_outDir = '/home/obs/TMON/Temperatures/'

parser = argparse.ArgumentParser()
parser.add_argument('--config_file', type=str, default=None,
                    help='full path to hera mc_config.json file specifiying '
                         'test_db and mc_db.')
parser.add_argument('--use_test', dest='use_test', action='store_false',
                    help='use test_db rather than mc_db')
parser.add_argument('--outDir', type=str, default=default_outDir,
                    help='Directory to save temperature files into')
parser.set_defaults(use_test=False)
args = parser.parse_args()

if args.config_file is None:
    test_db, mc_db = mc.get_configs(config_file=default_config_file)
else:
    test_db, mc_db = mc.get_configs(config_file=args.config_file)


def V2K(vi, number):
    return 100. * vi


def getJD():
    return (time() / 86400.) + 2440587.5


def ReadDat(dev, regNum):
    try:
        return V2K(dev.readRegister(regNum), regNum)
    except(IndexError):
        return -1.
    except(LabJackPython.LabJackException):
        dev.close()
        try:
            dev.open()
            return V2K(dev.readRegister(regNum), regNum)
        except(LabJackPython.LabJackException):
            return -2.


def readTemps(_d, _list_of_registers):
    # Get the internal temperature as well.
    ret = [getJD()] + [_d.getTemperature()] + [ReadDat(_d, i) for i in _list_of_registers]
    return ret


def aggData(cumList, dev, _list_of_registers, n_per_int):
    if cumList is None:
        raise(TypeError)
    else:
        for i, tnew in enumerate(readTemps(dev, _list_of_registers)):
            if cumList[i] < 0:
                pass
            if tnew < 0:
                cumList[i] = tnew
            else:
                cumList[i] += tnew / n_per_int
        return cumList

# seconds per integration
sPerInt = 10.
# minutes per file
mPerFile = 60.
outDir = '/home/obs/TMON/Temperatures/'

d = ue9.UE9()
mc_db = mc.DB_automap(use_test=args.use_test)

while True:
    fileName = '%stemp.%7.5f.txt' % (outDir, getJD())
    print 'Writing to %s' % fileName
    f = open(fileName, 'w')
    file_start_time = time()
    while(time() - file_start_time < mPerFile * 60.):
        Ts = None
        int_start_time = time()
        while(time() - int_start_time < sPerInt):
            try:
                try:
                    Ts = aggData(Ts, d, list_of_registers)
                except(TypeError):
                    Ts = readTemps(d, list_of_registers)
            except(KeyboardInterrupt):
                d.close()
        f.write("\t".join(["%7.5f" % t for t in Ts]) + "\n")
        mc_db.add_paper_temps(Ts[0], Ts[1:])
        f.flush()
    f.close()
d.close()
