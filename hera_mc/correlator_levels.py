# This requires that the rails server is running:
# $ cd /home/davidm/local/src/rails-paper
# $ rails server --daemon
# (http://herawiki.berkeley.edu/doku.php/correlator.operations)

from __future__ import print_function
import urllib2
import os.path

pf_in__to__file_col = {'A1': 0, 'A2': 1, 'A3': 2, 'A4': 3,
                       'B1': 4, 'B2': 5, 'B3': 6, 'B4': 7,
                       'C1': 8, 'C2': 9, 'C3': 10, 'C4': 11,
                       'D1': 12, 'D2': 13, 'D3': 14, 'D4': 15,
                       'E1': 16, 'E2': 17, 'E3': 18, 'E4': 19,
                       'F1': 20, 'F2': 21, 'F3': 22, 'F4': 23,
                       'G1': 24, 'G2': 25, 'G3': 26, 'G4': 27,
                       'H1': 28, 'H2': 29, 'H3': 30, 'H4': 31}
DF_chassis_list = ['1', '2', '3', '4', '5', '6', '7', '8']
default_levels_filename = os.path.expanduser('~/.hera_mc/levels.tmp')


def get_levels(pf_input, testing, network='local', timeout=2):
    """
    This returns a dictionary containing the correlator levels for inputs givin in pf_input.
    This assumes the f-engine name structure of 'DF<int=pf_chassis><letter=input_row><int=input_col>'
    It tries to read the correlator "rails" fail, and it that fails it provides dummy values (that
    was just to check the formats...)

    Parameters:
    -----------
    pf_input:  list of f-engine inputs at prescribed naming convention.
    testing:  names of testing file (used if fail at reading values)
    network:  meant to describe different network locations.  Currently only 'local'
    timeout:  time to allow valid connection to read values.
    """

    live_values = get_current_levels_from_url(default_levels_filename, network, timeout)
    if live_values:
        levels_filename = default_levels_filename
    else:
        print("\nNOT LIVE CORRELATOR VALUES:  Reading from default test file.")
        levels_filename = testing

    levels = read_levels_file(levels_filename)
    if type(pf_input) is not list:
        pf_input = [pf_input]
    pf_levels = []
    for pf in pf_input:
        if levels is None:
            print('No valid correlator level file.')
            pf_levels.append('X')
        elif pf is None:
            pf_levels.append('-')
        elif valid_input_name(pf):
            pf_chassis = 'F' + str(pf[2])
            pf_rowcol_designator = pf[-2:]
            level_col = pf_in__to__file_col[pf_rowcol_designator]
            pf_levels.append(levels[pf_chassis][level_col])
        else:
            print("Invalid f-engine call", pf)
            pf_levels.append('-')
    return pf_levels


def valid_input_name(pf):
    if pf is None:
        return False
    elif pf[:2].upper() != 'DF':
        return False
    elif pf[2] not in DF_chassis_list:
        return False
    elif pf[-2:] not in pf_in__to__file_col.keys():
        return False
    return True


def read_levels_file(name):
    try:
        lfp = open(name, 'r')
    except IOError:
        print('Warning:', name, 'not found.')
        return None
    levels = {}
    for line in lfp:
        d = line.split()
        pf = d[0][1:].upper()
        levels[pf] = d[2:]
    lfp.close()
    return levels


def get_current_levels_from_url(name, network, timeout):
    try:
        if network == 'local':
            url = urllib2.urlopen('http://10.0.1.1:3000/instruments/psa256/levels.txt', timeout=timeout)
        else:
            print("Currently only support local network for live values.")
            return False
        levels_url = url.read()
        fp = open(name, 'w')
        fp.write(levels_url)
        fp.close()
        return True
    except urllib2.URLError:
        return False
