# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Some low-level configuration management utility functions."""

import subprocess
from astropy.time import Time
from astropy.time import TimeDelta
import datetime

from . import mc

PAST_DATE = "2000-01-01"
VALID_FLOAT_FORMAT_FOR_TIME = ["unix", "gps", "jd"]


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
            raise ValueError("No cm_csv_path defined in mc_config file.")

    git_hash = subprocess.check_output(
        ["git", "-C", cm_csv_path, "rev-parse", "HEAD"], stderr=subprocess.STDOUT
    ).strip()
    return git_hash


def log(msg, **kwargs):
    """
    Write to the standard cm log file.

    Parameters
    ----------
    msg : str
        log message to write.
    **kwargs : dict
        keywords and arguments to log.

    """
    fp = open(mc.cm_log_file, "a")
    dt = Time.now()
    fp.write(
        "-------------------"
        + str(dt.datetime)
        + "  "
        + msg
        + "-------------------\n\n"
    )
    for key, value in kwargs.items():
        if key == "args":
            fp.write("--args\n\t")
            vargs = vars(value)
            for k, v in vargs.items():
                fp.write(str(k) + ":  " + str(v) + ";  ")
            fp.write("\n\n")
        elif key == "data_dict":
            fp.write("--data\n\t")
            for k, v in value.items():
                fp.write("    " + k + "  ")
                for d in v:
                    fp.write(str(d) + ";  ")
                fp.write("\n\n")
        else:
            fp.write("--other\n\t")
            fp.write(str(key) + ":  " + str(value) + "\n\n")
    fp.close()


# #######################################Key stuff
system_wide_key = "__Sys__"


def port_is_polarized(port, pol_list):
    """Determine if a part is polarized."""
    for pol in pol_list:
        if port.upper().startswith(pol.upper()):
            return True
    return False


def make_part_key(hpn, rev, port=None):
    """
    Return the standard part key of hpn:rev[:port].

    Port is only included if not None

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

    if rev is None:
        return hpn.upper()

    if port is None:
        return ":".join([hpn.upper(), rev.upper()])

    return ":".join([hpn.upper(), rev.upper(), port.upper()])


def split_part_key(key):
    """
    Split the standard part key.

    Only returns port if present in key.

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


def stringify(inp):
    """
    "Stringify" the input, hopefully sensibly.

    Parameters
    ----------
    inp
        Thing to be stringified.

    Returns
    -------
    str

    """
    if inp is None:
        return None
    if isinstance(inp, str):
        return inp
    if isinstance(inp, list):
        return ",".join(inp)
    return str(inp)


def listify(to_list, None_as_list=False, prefix=None, padding=None):
    """
    "Listify" the input, hopefully sensibly.

    Parameters
    ----------
    to_list
        Thing to be listified.
    None_as_list : bool
        If False return None if to_list is None, otherwise return [None]
    prefix : str or None
        If str, it will be prepended to every element in list
    padding : int or None
        If int, every integer element will be zero-padded to that length

    Returns
    -------
    List or None

    """
    if to_list is None:
        if None_as_list:
            return [None]
        else:
            return None
    if isinstance(to_list, str):
        if "-" in to_list:
            try:
                start, stop = [int(_x) for _x in to_list.split("-")]
                this_list = list(range(int(start), int(stop) + 1))
            except ValueError:
                this_list = to_list.split(",")
                padding = None
        else:
            try:
                this_list = [int(_x) for _x in to_list.split(",")]
            except ValueError:
                this_list = to_list.split(",")
                padding = None
        if prefix is None:
            return this_list
        if isinstance(padding, int):
            return ["{}{:0{pad}d}".format(prefix, x, pad=padding) for x in this_list]
        return ["{}{}".format(prefix, x) for x in this_list]
    if isinstance(to_list, list):
        return to_list
    return [to_list]


def match_list(a_obj, b_obj, case_type=None):
    """
    Return a zipped list-pair of same length.

    This can handle objects of any type, but its primary use is to make sure
    part number/revision calls as lists or strings are matched.  If case_type is
    not None, then all elements will be returned as str or None.

    Parameters
    ----------
    a_obj
        First object to match
    b_obj
        Second object to match
    case_type : str or None
        To convert to 'uppercase'/'u' or 'lowercase'/'l' strings.  None keeps as supplied.

    Returns
    -------
    zip

    Raises
    ------
    ValueError
        If supplied objects can't be matched or invalid case_type.

    """
    a_obj = listify(a_obj, None_as_list=True)
    b_obj = listify(b_obj, None_as_list=True)
    if len(a_obj) > len(b_obj):
        b_obj = b_obj * len(a_obj)
    elif len(b_obj) > len(a_obj):
        a_obj = a_obj * len(b_obj)
    if len(a_obj) != len(b_obj):
        raise ValueError("Lists must be same length")
    if case_type is None:
        return zip(a_obj, b_obj)
    case_type = case_type[0].lower()
    if case_type == "u":
        return zip(to_upper(a_obj), to_upper(b_obj))
    elif case_type == "l":
        return zip(to_lower(a_obj), to_lower(b_obj))
    raise ValueError("Invalid case_type.")


def to_upper(inp):
    """
    Recursively convert inputs to uppercase strings, except if None.

    Parameters
    ----------
    inp : str or list of str
        Object to be converted to upper.

    Returns
    -------
    str, list or None

    """
    if inp is None:
        return None
    if isinstance(inp, list):
        return [to_upper(s) for s in inp]
    return str(inp).upper()


def to_lower(inp):
    """
    Recursively convert inputs to lowercase strings, except if None.

    Parameters
    ----------
    inp : str or list of str
        Object to be converted to lower.

    Returns
    -------
    str, list or None

    """
    if inp is None:
        return None
    if isinstance(inp, list):
        return [to_lower(s) for s in inp]
    return str(inp).lower()


def add_verbosity_args(parser):
    """
    Add a standardized "--verbosity" argument to an ArgParser object.

    Returns the number of 'v's (-v=1 [low], -vv=2 [medium], -vvv=3 [high]) or
    the supplied integer. Parsed by 'parse_verbosity' function. Defaults to 1.

    Parameters
    ----------
    parser : object
        Parser object

    """
    parser.add_argument(
        "-v",
        "--verbosity",
        help="Verbosity level -v -vv -vvv. [-vv].",
        nargs="?",
        default=2,
    )


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
    if vargs.count("v"):
        return vargs.count("v") + 1
    raise ValueError("Invalid argument to verbosity.")


# ##############################################DATE STUFF
def add_date_time_args(parser):
    """
    Add standardized "--date" and "--time" arguments to an ArgParser object.

    Their values should then be converted into a Python DateTime object using
    the function `get_astropytime`.

    Parameters
    ----------
    parser : object
        Parser object

    """
    parser.add_argument(
        "--date",
        help="UTC YYYY/MM/DD or '<' or '>' or 'now' or one of jd,unix,gps [now]",
        default="now",
    )
    parser.add_argument(
        "--time",
        help="UTC hh:mm or float (hours), must include --date if use --time",
        default=0.0,
    )
    parser.add_argument(
        "--format", help="Format if date is unix, gps or jd.", default=None
    )


def is_active(at_date, start_date=None, stop_date=None):
    """
    Check to see if at_date is within start/stop.

    Note that at_date, start_date and stop_date must be of the same type or None.

    Parameters
    ----------
    at_date : Time, int/float, None or 'now'
        Date to check - must be astropy.time, number, None or 'now'
    start_date : Time, int/float, None
        Start date to use - must be astropy.time, number or None
    stop_date : Time, int/float, None
        Stop date to use - must be astropy.time, number or None

    """
    if at_date is None:
        return True
    elif at_date == "now":
        at_date = Time.now()
    if start_date is None and stop_date is None:
        return True
    if isinstance(at_date, Time):
        at_date = at_date.gps
        if start_date is None:
            start_date = 0
        else:
            start_date = start_date.gps
        if stop_date is None:
            stop_date = 2000000000
        else:
            stop_date = stop_date.gps
    else:
        if start_date is None:
            start_date = 0
        if stop_date is None:
            stop_date = 2000000000

    return at_date >= start_date and at_date <= stop_date


def future_date():
    """
    Future is defined here.

    Defining a far future date typically gives a warning about UTC vs UT1 etc.

    Returns
    -------
    Time
        Time 1000 days in the future.

    """
    return Time.now() + TimeDelta(1000, format="jd")


def get_stopdate(stop_date, stop_time=None, float_format=None):
    """
    Provide an appropriate stop date.

    Parameters
    ----------
    stop_date : Anything intelligible by `get_astropytime`.
        If None, uses `future_date`.
    stop_time : Anything intelligible by `get_astropytime`.
        Passed to get_astropytime, ignored if at_date is a float or contains time information.
    float_format : str or None
        Format if stop_date is unix or gps time or jd day.

    Returns
    -------
    Time object
        Time object for stop_date.

    """
    if stop_date is None:
        return future_date()
    return get_astropytime(stop_date, stop_time, float_format)


def get_time_for_display(display, display_time=None, float_format=None):
    """
    Provide a reader-friendly time string.

    Accepts any time parse-able by get_astropytime -
    if that results in None, then the string None is displayed.

    Parameters
    ----------
    display : Anything intelligible by `get_astropytime`.
        Date to display.
    display_time : Any time intelligible by `get_astropytime`.
        Passed to get_astropytime, ignored if at_date is a float or contains time information.
    float_format : str or None
        Format if display is unix or gps or jd day.

    Returns
    -------
    str
        Human readable string of time in display.

    """
    d = get_astropytime(display, display_time, float_format)

    if d is None:
        d = "None"
    elif isinstance(d, Time):
        d = "{:%Y-%m-%d %H:%M:%S}".format(d.datetime)
    return d


# Bound between 1/1/2010 and 12/31/2029
bounds = {
    "gps": [946339215.0, 1577404818.0],
    "jd": [2455197.5, 2462501.5],
    "unix": [1262332800.0, 1893398400.0],
}


def _check_time_as_a_number(val, fmt):
    if fmt in VALID_FLOAT_FORMAT_FOR_TIME:
        if val < bounds[fmt][0] or val > bounds[fmt][1]:
            from warnings import warn

            warn(f"{val} out of nominal range for {fmt}")
        return fmt
    elif fmt is None:
        if val > bounds["jd"][0] and val < bounds["jd"][1]:
            from warnings import warn

            warn(f"No time format given -- assuming jd based on value {val}")
            return "jd"
        else:
            raise ValueError(f"No time format given for ambiguous value {val}")
    else:
        raise ValueError(f"Invalid time format: {fmt}")


def get_astropytime(adate, atime=None, float_format=None):
    """
    Get an astropy.Time object based on provided values.

    Take in various incarnations of adate/atime and return astropy.Time or None.

    Note that atime is only used if adate is a str (so ignored if adate is a Time
    or number).  Also, float_format is only used if adate is a number (checked as
    "float(adate)").

    Returns:  either astropy.Time or None

    Parameters
    ----------
    adate : Time, int, float, datetime, str
            A date in various formats:
                return astropy Time
                    astropy Time:  just gets returned
                    datetime: just gets converted
                    int, float:  interpreted per supplied float_format
                    string:  '<' - PAST_DATE
                             '>' - future_date()
                             'now' or 'current'
                             'YYYY/M/D' or 'YYYY-M-D'
                return None:
                    string:  'none' return None
                    None/False:  return None
    atime : float, int, str
            A time in various formats, ignored unless adate is a str
                float, int:  hours in decimal time
                string:  HH[:MM[:SS]] or hours in decimal time
    float_format : str or None
                    force to format if adate is convertable as a number
                    one of VALID_FLOAT_FORMAT_FOR_TIME above.  Some limited checking if None

    Returns
    -------
    astropy.Time or None

    """
    if isinstance(adate, Time):
        return adate
    if isinstance(adate, datetime.datetime):
        return Time(adate, format="datetime")
    if adate is None or adate is False:
        return None
    try:
        adate = float(adate)
    except ValueError:
        pass
    if isinstance(adate, float):
        float_format = _check_time_as_a_number(adate, float_format)
        return Time(adate, format=float_format)
    if isinstance(adate, str):
        if adate == "<":
            return Time(PAST_DATE, scale="utc")
        if adate == ">":
            return future_date()
        if adate.lower() == "now" or adate.lower() == "current":
            return Time.now()
        if adate.lower() == "none":
            return None
        adate = adate.replace("/", "-")
        try:
            return_date = Time(adate, scale="utc")
        except ValueError:
            raise ValueError(
                "Invalid format:  date should be YYYY/M/D or YYYY-M-D, not {}".format(
                    adate
                )
            )
        if atime is None:
            return return_date
        try:
            atime = float(atime)
        except ValueError:
            pass
        if isinstance(atime, float):
            return return_date + TimeDelta(atime * 3600.0, format="sec")
        if isinstance(atime, str):
            if ":" not in atime:
                raise ValueError(
                    "Invalid format:  time should be H[:M[:S]] (ints or floats)"
                )
            add_time = 0.0
            for i, d in enumerate(atime.split(":")):
                if i > 2:
                    raise ValueError(
                        "Time can only be hours[:minutes[:seconds]], not {}.".format(
                            atime
                        )
                    )
                add_time += (float(d)) * 3600.0 / (60.0**i)
            return return_date + TimeDelta(add_time, format="sec")


def peel_key(key, sort_order):
    """
    Separate a hookup key into its parts.

    Parameters
    ----------
    key : str
        key to separate.
    sort_order : str
        String specifying how to sort the key parts.

    """
    rev = ""
    if ":" not in key:
        rev = ":A"
    c = key + rev
    colon = c.find(":")
    for i in range(len(c)):
        try:
            n = int(c[i:colon])
            break
        except ValueError:
            n = 0
            continue
    prefix = c[:i]
    rev = c[colon + 1 :]
    sort_order = sort_order.upper()
    if sort_order == "NPR":
        return (n, prefix, rev)
    if sort_order == "PNR":
        return (prefix, n, rev)
    if sort_order == "RPN":
        return (rev, prefix, n)
    if sort_order == "NRP":
        return (n, rev, prefix)
    if sort_order == "RNP":
        return (rev, n, prefix)
    if sort_order == "PRN":
        return (prefix, rev, n)


def put_keys_in_order(keys, sort_order="NPR"):
    """
    Order hookup keys by alpha+number order.

    Takes a list of hookup keys in the format of prefix[number][:revision] and
    puts them in alpha+number order.

    Parameters
    ----------
    keys : list
        List of hookup keys
    sort_order : str
        Order of sorting: N=number, P=prefix, R=revision

    Returns
    -------
    list
        Ordered list of keys

    """
    keylib = {}
    for k in keys:
        keylib[peel_key(k, sort_order)] = k

    keyordered = []
    for k in sorted(keylib.keys()):
        keyordered.append(keylib[k])
    return keyordered


def html_table(headers, table):
    """
    Format a table into an html table.

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
        String containing the full html table.

    """
    s_table = '<table border="1">\n<tr>'
    for h in headers:
        s_table += "<th>{}</th>".format(h)
    s_table += "</tr>\n"
    for tr in table:
        s_table += "<tr>"
        for d in tr:
            f = str(d).replace("<", "&lt ")
            f = f.replace(">", "&gt ")
            s_table += "<td>{}</td>".format(f)
        s_table += "</tr>\n"
    s_table += "</table>"
    return s_table


def csv_table(headers, table):
    """
    Format a table into an csv string.

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
        String containing the full csv table.

    """
    s_table = ""
    for h in headers:
        s_table += '"{}",'.format(h)
    s_table = s_table.strip(",") + "\n"
    for tr in table:
        for d in tr:
            s_table += '"{}",'.format(d)
        s_table = s_table.strip(",") + "\n"
    return s_table


def general_table_handler(headers, table_data, output_format=None):
    """Return formatted table."""
    from tabulate import tabulate

    if output_format.lower().startswith("htm"):
        dtime = get_time_for_display("now") + "\n"
        table = html_table(headers, table_data)
        table = (
            "<html>\n\t<body>\n\t\t<pre>\n"
            + dtime
            + table
            + dtime
            + "\t\t</pre>\n\t</body>\n</html>\n"
        )
    elif output_format.lower().startswith("csv"):
        table = csv_table(headers, table_data)
    else:
        if output_format == "table":
            output_format = "orgtbl"
        table = tabulate(table_data, headers=headers, tablefmt=output_format) + "\n"
    return table


def query_default(param, args):
    """
    Allow for a parameter to be queried, and return defaults for those not provided.

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
    if "unittesting" in vargs.keys():
        v = vargs["unittesting"]
    else:  # pragma: no cover
        s = "{} [{}]:  ".format(param, str(default))
        v = input(s)
    if len(v) == 0:
        return default
    if v.lower() == "none":
        return None
    if v.lower() == "false":
        return False
    if v.lower() == "true":
        return True
    return v
