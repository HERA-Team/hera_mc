# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Contains geographic location information and methods."""
import os.path
from . import cm_utils

from .data import DATA_PATH

# fmt: off
region = {'herahexw': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
                       16, 17, 18, 19, 20, 21,
                       23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 36, 37, 38,
                       39, 40, 41, 42, 43, 44, 45, 46,
                       50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 65, 66, 67,
                       68, 69, 70, 71, 72, 73, 74, 75,
                       81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 98, 99, 100,
                       101, 102, 103, 104, 105, 106, 107, 108,
                       116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126,
                       135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145],
          'herahexe': [22, 34, 35, 47, 48, 49, 61, 62, 63, 64, 76, 77, 76, 78,
                       79, 80, 92, 93, 94, 95, 96, 97,
                       109, 110, 111, 112, 113, 114, 115, 127, 128, 129, 130,
                       131, 132, 133, 134, 146, 147, 148, 149, 150, 151, 152,
                       153, 154,
                       166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 187,
                       188, 189, 190, 191, 192, 193, 194, 195,
                       207, 208, 209, 210, 211, 212, 213, 214, 226, 227, 228,
                       229, 230, 231, 232, 244, 245, 246, 247, 248, 249,
                       261, 262, 263, 264, 265, 277, 278, 279, 280, 292, 293,
                       294, 306, 307, 319],
          'herahexn': [155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165,
                       176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186,
                       196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206,
                       215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225,
                       233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243,
                       250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260,
                       266, 267, 268, 269, 270, 271, 272, 273, 274, 275, 276,
                       281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291,
                       295, 296, 297, 298, 299, 300, 301, 302, 303, 304, 305,
                       308, 309, 310, 311, 312, 313, 314, 315, 316, 317, 318],
          'heraringa': [325, 326, 327, 330, 331, 334, 335, 338, 339, 342, 343, 344],
          'heraringb': [320, 321, 322, 323, 324, 328, 329, 332, 333, 336, 337,
                        340, 341, 345, 346, 347, 348, 349]}

# fmt: on


def _get_region(this_ant):
    """
    Properly handle a single entry for finding a region.

    If a full HERA part number is given and is for a ring, it will issue a
    warning if the prefix given and the ring don't match.

    Parameter
    ---------
    this_ant : str or int
        Antenna number for which to check.
    """
    prefix = ""
    try:
        this_ant = int(this_ant)
    except ValueError:
        peeled = cm_utils.peel_key(this_ant, "NPR")
        this_ant = peeled[0]
        prefix = peeled[1].upper()
    for this_region, region_list in region.items():
        if this_ant in region_list:
            val = this_region[-1].upper()
            break
    else:
        raise ValueError(f"{this_ant} is not valid antenna.")
    if val in ["A", "B"] and len(prefix) == 2:
        if val != prefix[1]:
            import warnings

            warnings.warn(f"{prefix} does not match region {val}")
    return val


def ant_region(ants):
    """
    Provide the region of an antenna or list of antennas.

    If a list (list, tuple, set, numpy array), it will return a list,
    otherwise it will return a str.
    Note that the regions are:  N, E, W, A, B for
        North "tridrant"
        East  "
        West  "
        A ring (inner)
        B ring (outer)

    Parameter
    ---------
    ants : str, number or list (list, tuple, set, numpy array)
            Antenna number or HERA part number of antenna.

    Return
    ------
    str or list-of-str : single character region designations
    """
    try:
        ants = [int(ants)]
        return_as = "str"
    except ValueError:
        ants = [ants]
        return_as = "str"
    except TypeError:
        return_as = "list"
    found_regions = [_get_region(_a) for _a in ants]
    if return_as == "str":
        return found_regions[0]
    return found_regions


def read_nodes():
    """
    Read in the node information from nodes.txt.

    Returns
    -------
    dict
        Contains location and antenna list for all nodes.  Keyed on node number as int.

    """
    node_coord_file_name = os.path.join(DATA_PATH, "nodes.txt")
    default_elevation = 1050.0
    nodes = {}
    with open(node_coord_file_name, "r") as fp:
        for line in fp:
            node_num = int(line.split(":")[0])
            node_e = float(line.split(":")[1].split(",")[0])
            node_n = float(line.split(":")[1].split(",")[1])
            ants = line.split(":")[2].split(",")
            ants = [int(x) for x in ants]
            nodes[node_num] = {
                "E": node_e,
                "N": node_n,
                "elevation": default_elevation,
                "ants": ants,
            }
    return nodes


def read_antennas():
    """
    Read in the antenna information from HERA_350.txt.

    Returns
    -------
    dict
        Contains location for all antennas.  Keyed on antenna hpn

    """
    antenna_coord_file_name = os.path.join(DATA_PATH, "HERA_350.txt")
    antennas = {}
    with open(antenna_coord_file_name, "r") as fp:
        for line in fp:
            data = line.split()
            coords = [data[0], float(data[1]), float(data[2]), float(data[3])]
            antennas[coords[0]] = {
                "E": coords[1],
                "N": coords[2],
                "elevation": coords[3],
            }
    return antennas
