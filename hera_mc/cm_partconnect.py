# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""M&C logging of the parts and the connections between them."""

from astropy.time import Time
from sqlalchemy import BigInteger, Column, ForeignKeyConstraint, String, Text, func
from . import MCDeclarativeBase, NotNull
from . import mc, cm_utils

no_connection_designator = "-X-"


class PartRosetta(MCDeclarativeBase):
    """
    A table of mappings between physical and systems names within the HERA system.

    In addition to a HERA part number (hpn), some parts need a system-dependent "part number".
    For example, SNAPs have an hpn, but are referred to by their hostname in the correlator.
    As a specific example, SNPC000072 right now is also heraNode0Snap0

    Attributes
    ----------
    hpn : String Column
        HERA part number for each part.
    syspn : String Column
        System part number associated with the hpn; part of the primary key.
    start_gpstime : int
        start time for part name mapping; part of the primary key.
    stop_gpstime : int
        stop time for part name mapping.
    """

    __tablename__ = "part_rosetta"

    hpn = Column(String(64), nullable=False)
    syspn = Column(String(64), primary_key=True)
    start_gpstime = Column(BigInteger, primary_key=True)
    stop_gpstime = Column(BigInteger)

    def __repr__(self):
        """Define representation."""
        return (
            "<{self.hpn}  -  {self.syspn} :: {self.start_gpstime} - "
            "{self.stop_gpstime}>".format(self=self)
        )


def update_part_rosetta(
    hpn,
    syspn,
    at_date,
    at_time=None,
    float_format=None,
    date2=None,
    date2time=None,
    date2float_format=None,
    session=None,
):
    """
    Update rosetta relationship in part_rosetta table.

    If hpn <-> syspn relationship is active, will close it at at_date.
    If hpn <-> syspn relationship is NOT active, it will start it at at_date.
    If date2 is None, at_date is used as either start or stop, as appropriate.
    Note that hpn is cast to upper, but syspn is not modified.

    Parameters
    ----------
    hpn : str
        HERA part number
    syspn : str
        System part number
    at_date : anything interpretable by cm_utils.get_astropytime
        Date at which to initialize.
    at_time : anything interpretable by cm_utils.get_astropytime
        Time at which to initialize, ignored if at_date is a float or contains time information
    float_format : str
        Format if at_date is a number denoting gps or unix seconds or jd day.
    date2 : anything interpretable by cm_utils.get_astropytime
        If not None, Date at which to stop.
    date2time : anything interpretable by cm_utils.get_astropytime
        Time at which to stop, ignored if date2 is a float or contains time information
    date2float_format : str
        Format if at_date is a number denoting gps or unix seconds or jd day.
    session : object
        Database session to use.  If None, it will start a new session, then close.

    """
    at_date = int(cm_utils.get_astropytime(at_date, at_time, float_format).gps)
    if date2 is not None:
        date2 = int(cm_utils.get_astropytime(date2, date2time, date2float_format).gps)

    close_session_when_done = False
    if session is None:  # pragma: no cover
        db = mc.connect_to_mc_db(None)
        session = db.sessionmaker()
        close_session_when_done = True

    old_rose = None
    ctr = 0
    for trial in session.query(PartRosetta).filter(
        (func.upper(PartRosetta.syspn) == syspn.upper())
    ):
        if cm_utils.is_active(at_date, trial.start_gpstime, trial.stop_gpstime):
            ctr += 1
            old_rose = trial
    if ctr > 1:
        raise ValueError("Multiple rosetta relationships active for {}".format(syspn))
    if old_rose is None:
        new_rose = PartRosetta()
        new_rose.hpn = hpn
        new_rose.syspn = syspn
        new_rose.start_gpstime = at_date
        new_rose.stop_gpstime = date2
        session.add(new_rose)
    else:
        if old_rose.stop_gpstime is None:
            old_rose.stop_gpstime = at_date
            session.add(old_rose)
        else:
            import warnings

            warnings.warn(
                "No action taken.  {} already has a valid stop date".format(old_rose)
            )

    session.commit()
    if close_session_when_done:  # pragma: no cover
        session.close()


class Parts(MCDeclarativeBase):
    """
    A table logging parts within the HERA system.

    Stations will be considered parts of type='station'
    Note that ideally install_date would also be a primary key, but that
    screws up ForeignKey in connections

    Attributes
    ----------
    hpn : String Column
        HERA part number for each part; part of the primary key.
    hpn_rev : String Column
        A revision letter of sequences of hpn - starts with A. . Part of the primary_key
    hptype : String Column
        A part-dependent string, i.e. feed, frontend, ...
    manufacturer_number : String Column
        A part number/serial number as specified by manufacturer
    start_gpstime : BigInteger Column
        The date when the part was installed (or otherwise assigned by project).
    stop_gpstime : BigInteger Column
        The date when the part was removed (or otherwise de-assigned by project).

    """

    __tablename__ = "parts"

    hpn = Column(String(64), primary_key=True)
    hpn_rev = Column(String(32), primary_key=True)
    hptype = NotNull(String(64))
    manufacturer_number = Column(String(64))
    start_gpstime = Column(BigInteger, nullable=False)
    stop_gpstime = Column(BigInteger)

    def __repr__(self):
        """Define representation."""
        return (
            "<heraPartNumber id={self.hpn}:{self.hpn_rev} "
            "type={self.hptype} :: {self.start_gpstime} - {self.stop_gpstime}>".format(
                self=self
            )
        )

    def __eq__(self, other):
        """Define equality."""
        if (
            isinstance(other, self.__class__)
            and self.hpn.upper() == other.hpn.upper()
            and self.hpn_rev.upper() == other.hpn_rev.upper()
        ):
            return True
        return False

    def gps2Time(self):
        """Make astropy.Time object from gps."""
        self.start_date = Time(self.start_gpstime, format="gps")
        if self.stop_gpstime is None:
            self.stop_date = None
        else:
            self.stop_date = Time(self.stop_gpstime, format="gps")

    def part(self, **kwargs):
        """Allow specification of an arbitrary part."""
        for key, value in kwargs.items():
            setattr(self, key, value)


def stop_existing_parts(session, part_list, at_date, allow_override=False):
    """
    Add stop times to the previous parts.

    Parameters
    ----------
    session : object
        Database session to use.  If None, it will start a new session, then close.
    part_list : list of lists
        List containing hpn and revision pair(s).  [[hpn0, rev0], ...]
    at_date : astropy.Time object
        Date to use for logging the stop
    allow_override : bool
        Flag to allow a reset of the stop time even if one exists.

    """
    stop_at = int(at_date.gps)
    data = []
    close_session_when_done = False
    if session is None:  # pragma: no cover
        db = mc.connect_to_mc_db(None)
        session = db.sessionmaker()
        close_session_when_done = True

    for hpnr in part_list:
        existing = (
            session.query(Parts)
            .filter(
                (func.upper(Parts.hpn) == hpnr[0].upper())
                & (func.upper(Parts.hpn_rev) == hpnr[1].upper())
            )
            .first()
        )
        if existing is None:
            print("{}:{} is not found, so can't stop it.".format(hpnr[0], hpnr[1]))
            continue
        if existing.stop_gpstime is not None:
            print(
                "{}:{} already has a stop time ({})".format(
                    hpnr[0], hpnr[1], existing.stop_gpstime
                )
            )
            if allow_override:
                print("\tOverride enabled.   New value {}".format(stop_at))
            else:
                print("\tOverride not enabled.  No action.")
                continue
        else:
            print("Stopping part {}:{} at {}".format(hpnr[0], hpnr[1], str(at_date)))
        data.append([hpnr[0], hpnr[1], "stop_gpstime", stop_at])

    update_part(session, data)
    if close_session_when_done:  # pragma: no cover
        session.close()


def add_new_parts(session, part_list, at_date, allow_restart=False):
    """
    Add new parts.

    If a part is there and is stopped, it will log that info
    and restart the part.  If it is there and is not stopped, it does nothing.

    Parameters
    ----------
    session : object
        Database session to use.  If None, it will start a new session, then close.
    part_list : list of lists
        List containing hpn and revision pair(s).  [[hpn0, rev0], ...]
    at_date : astropy.Time object
        Date to use for logging the stop
    allow_restart : bool
        Flag to allow the part to restarted if it already existed.

    """
    start_at = int(at_date.gps)
    data = []
    close_session_when_done = False
    if session is None:  # pragma: no cover
        db = mc.connect_to_mc_db(None)
        session = db.sessionmaker()
        close_session_when_done = True

    for hpnr in part_list:
        existing = (
            session.query(Parts)
            .filter(
                (func.upper(Parts.hpn) == hpnr[0].upper())
                & (func.upper(Parts.hpn_rev) == hpnr[1].upper())
            )
            .first()
        )
        if existing is not None and existing.stop_gpstime is None:
            print(
                "No action. {}:{} already in database with no stop date".format(
                    hpnr[0], hpnr[1]
                )
            )
            continue
        this_data = []
        this_data.append([hpnr[0], hpnr[1], "hpn", hpnr[0]])
        this_data.append([hpnr[0], hpnr[1], "hpn_rev", hpnr[1]])
        this_data.append([hpnr[0], hpnr[1], "hptype", hpnr[2]])
        this_data.append([hpnr[0], hpnr[1], "manufacturer_number", hpnr[3]])
        this_data.append([hpnr[0], hpnr[1], "start_gpstime", start_at])
        print_out = "starting part {}:{} at {}".format(hpnr[0], hpnr[1], str(at_date))
        if existing is not None:
            if allow_restart:
                print_out = "re" + print_out
                this_data.append([hpnr[0], hpnr[1], "stop_gpstime", None])
                comment = "Restarting part.  Previous data {}".format(existing)
                add_part_info(
                    session,
                    hpn=hpnr[0],
                    rev=hpnr[1],
                    comment=comment,
                    at_date=at_date,
                    reference=None,
                )
            else:
                print_out = (
                    "No action. The request {} not an allowed part restart.".format(
                        hpnr
                    )
                )
                this_data = None
        if this_data is not None:
            data = data + this_data
        print(print_out.capitalize())

    update_part(session, data)
    if close_session_when_done:  # pragma: no cover
        session.close()


def update_part(session=None, data=None):
    """
    Update the database given a hera part number with columns/values.

    This is a low-level module, generally called from somewhere else

    Parameters
    ----------
    session : object
        Database session to use.  If None, it will start a new session, then close.
    data : list of lists
        List containing the hpn, rev, column and value to update
            [[hpn0,rev0,column0,value0],[...]]
                hpnN:  hera part number as primary key
                revN:  hera part number revision as primary key
                columnN:  column name(s)
                valueN:  corresponding list of values

    Returns
    -------
    bool
        True if any updates were made, else False

    """
    data_dict = format_and_check_update_part_request(data)
    if data_dict is None:
        return False

    close_session_when_done = False
    if session is None:  # pragma: no cover
        db = mc.connect_to_mc_db(None)
        session = db.sessionmaker()
        close_session_when_done = True

    for dkey, dval in data_dict.items():
        hpn_to_change = dval[0][0]
        rev_to_change = dval[0][1]
        part_rec = session.query(Parts).filter(
            (func.upper(Parts.hpn) == hpn_to_change.upper())
            & (func.upper(Parts.hpn_rev) == rev_to_change.upper())
        )
        num_part = part_rec.count()
        if num_part == 0:
            part = Parts()
        elif num_part == 1:
            part = part_rec.first()
        set_an_attrib = False
        for d in dval:
            try:
                getattr(part, d[2])
                setattr(part, d[2], d[3])
                set_an_attrib = True
            except AttributeError:
                print(d[2], "does not exist as a field")
                continue
        if set_an_attrib:
            session.add(part)
            session.commit()
    cm_utils.log("cm_partconnect part update", data_dict=data_dict)
    if close_session_when_done:  # pragma: no cover
        session.close()

    return True


def format_and_check_update_part_request(request):
    """
    Parse the update request into a standard format dictionary keyed on the part/rev pair.

    Parameters
    ----------
    request : string or list
        hpn0:rev0:column0:value0,hpn1:rev1:column1:value1,... or
        [[hpn0, rev0, column0, value0], [...]] where
            hpnN:  hera part number (first entry must have one) if absent, propagate first
            revN:  hera part revision number (first entry must have one) if absent, propagate first
            columnN:  name of parts column
            valueN:  corresponding new value

    Returns
    -------
    dict or None
        Dictionary containing the parsed commands, otherwise None if the request is None or empty

    """
    if request is None or len(request) == 0:
        return None

    # Split out and get first
    data = {}
    if type(request) == str:
        tmp = request.split(",")
        data_to_proc = []
        for d in tmp:
            data_to_proc.append(d.split(":"))
    else:
        data_to_proc = request
    if len(data_to_proc[0]) == 4:
        hpn0 = data_to_proc[0][0]
        rev0 = data_to_proc[0][1]
    else:
        raise ValueError("Wrong format for first part update entry request.")
    for d in data_to_proc:
        if len(d) == 4:
            pass
        elif len(d) == 3:
            d.insert(1, rev0)
        elif len(d) == 2:
            d.insert(0, hpn0)
            d.insert(1, rev0)
        else:
            print("Invalid format for update request.")
            continue
        dkey = d[0] + ":" + d[1]
        if dkey in data.keys():
            data[dkey].append(d)
        else:
            data[dkey] = [d]
    return data


def get_part_revisions(hpn, session=None):
    """
    Retrieve revision numbers for a given part (exact match).

    Parameters
    ----------
    hpn :  str
        hera part number
    session : object
        Database session to use.  If None, it will start a new session, then close.

    """
    if hpn is None:
        return {}

    uhpn = hpn.upper()
    close_session_when_done = False
    if session is None:  # pragma: no cover
        db = mc.connect_to_mc_db(None)
        session = db.sessionmaker()
        close_session_when_done = True

    revisions = {}
    for parts_rec in session.query(Parts).filter(func.upper(Parts.hpn) == uhpn):
        parts_rec.gps2Time()
        revisions[parts_rec.hpn_rev] = {}
        revisions[parts_rec.hpn_rev]["hpn"] = hpn  # Just carry this along
        revisions[parts_rec.hpn_rev]["started"] = parts_rec.start_date
        revisions[parts_rec.hpn_rev]["ended"] = parts_rec.stop_date
    if close_session_when_done:  # pragma: no cover
        session.close()
    return revisions


class AprioriAntenna(MCDeclarativeBase):
    """
    Table for a priori antenna status.

    Parameters
    ----------
    antenna :  str
        antenna designation, e.g. HH123
    start_gpstime : int
        start time for antenna status
    stop_gpstime : int
        stop time for antenna status
    status :  str
        status - "dish_maintenance", "dish_ok","RF_maintenance", "RF_ok",
                 "digital_maintenance", "digital_ok",
                 "calibration_maintenance", "calibration_ok","calibration_triage"

                 OLDER VALUES - Maintained for backwards compatibility
                 "passed_checks", "needs_checking", "known_bad", "not_connected"
    """

    __tablename__ = "apriori_antenna"

    antenna = Column(Text, primary_key=True)
    start_gpstime = Column(BigInteger, primary_key=True)
    stop_gpstime = Column(BigInteger)
    status = Column(Text, nullable=False)

    def __repr__(self):
        """Define representation."""
        return "<{}: {}  [{} - {}]>".format(
            self.antenna, self.status, self.start_gpstime, self.stop_gpstime
        )

    def old_statuses(self):
        """Define old statuses in database but no longer used."""
        return ["passed_checks", "needs_checking", "known_bad", "not_connected"]

    def valid_statuses(self):
        """Define current valid statuses."""
        return [
            "dish_maintenance",
            "dish_ok",
            "RF_maintenance",
            "RF_ok",
            "digital_maintenance",
            "digital_ok",
            "calibration_maintenance",
            "calibration_ok",
            "calibration_triage",
        ]

    def status_enum(self):
        """Get list of valid statuses."""
        return self.valid_statuses()


def get_apriori_antenna_status_enum():
    """Get list of valid apriori statuses."""
    apa = AprioriAntenna()
    return apa.status_enum()


def update_apriori_antenna(
    antenna, status, start_gpstime, stop_gpstime=None, session=None
):
    """
    Update the 'apriori_antenna' status table to one of the class enum values.

    If the status is not allowed, an error will be raised.
    Adds the appropriate stop time to the previous apriori_antenna status.

    Parameters
    ----------
    antenna : str
        Antenna designator, e.g. HH104
    status : str
        Apriori status.  Must be one of apriori enums.
    start_gpstime : int
        Start time for new apriori status, in GPS seconds
    stop_gpstime : int
        Stop time for new apriori status, in GPS seconds, or None.
    session : object
        Database session to use.  If None, it will start a new session, then close.

    """
    new_apa = AprioriAntenna()

    if status in new_apa.old_statuses():
        raise ValueError(
            "The status '{0}' is deprecated. "
            "Please select one of the new status values {1}.".format(
                status, new_apa.valid_statuses()
            ),
        )

    if status not in new_apa.status_enum():
        raise ValueError(
            "Antenna apriori status must be in {}".format(new_apa.status_enum())
        )

    close_session_when_done = False
    if session is None:  # pragma: no cover
        db = mc.connect_to_mc_db(None)
        session = db.sessionmaker()
        close_session_when_done = True

    antenna = antenna.upper()
    last_one = 1000
    old_apa = None
    for trial in session.query(AprioriAntenna).filter(
        func.upper(AprioriAntenna.antenna) == antenna
    ):
        if trial.start_gpstime > last_one:
            last_one = trial.start_gpstime
            old_apa = trial
    if old_apa is not None:
        if old_apa.stop_gpstime is None:
            old_apa.stop_gpstime = start_gpstime
        else:
            raise ValueError("Stop time must be None to update AprioriAntenna")
        session.add(old_apa)
    new_apa.antenna = antenna
    new_apa.status = status
    new_apa.start_gpstime = start_gpstime
    new_apa.stop_gpstime = stop_gpstime
    session.add(new_apa)

    session.commit()

    if close_session_when_done:  # pragma: no cover
        session.close()


class PartInfo(MCDeclarativeBase):
    """
    A table for logging test information etc for parts.

    Attributes
    ----------
    hpn : String Column
        A HERA part number for each part; intend to QRcode with this string.
        Part of the primary_key
    hpn_rev : String Column
        HERA part revision number for each part; if sequencing same part number.
        Part of the primary_key
    posting_gpstime : BigInteger Column
        Time that the data are posted. Part of the primary_key
    comment : String Column
        Comment associated with this data - or the data itself...
    reference : String Column
        Other reference associated with this entry.
    """

    __tablename__ = "part_info"

    hpn = Column(String(64), nullable=False, primary_key=True)
    hpn_rev = Column(String(32), nullable=False, primary_key=True)
    posting_gpstime = NotNull(BigInteger, primary_key=True)
    comment = NotNull(String(2048))
    reference = Column(String(256))

    def __repr__(self):
        """Define representation."""
        return (
            "<heraPartNumber id = {self.hpn}:{self.hpn_rev} "
            "comment = {self.comment}>".format(self=self)
        )

    def gps2Time(self):
        """Add a posting_date attribute (astropy Time object) based on posting_gpstime."""
        self.posting_date = Time(self.posting_gpstime, format="gps")

    def info(self, **kwargs):
        """Add arbitrary attributes passed in a dict to this object."""
        for key, value in kwargs.items():
            setattr(self, key, value)


def add_part_info(
    session, hpn, rev, comment, at_date, at_time=None, float_format=None, reference=None
):
    """
    Add part information into database.

    Parameters
    ----------
    session : object
        Database session to use.  If None, it will start a new session, then close.
    hpn : str
        HERA part number
    rev : str
        Part revision number
    at_date : any format that cm_utils.get_astropytime understands
        Date to use for the log entry
    at_time : any format that cm_utils.get_astropytime understands
        Time to use for the log entry, ignored if at_date is a float or contains time information
    float_format : str
        Format if at_date is unix or gps or jd day.
    comment : str
        String containing the comment to be logged.
    reference : str, None
        If appropriate, name or link of library file or other information.

    """
    comment = comment.strip()
    if not len(comment):
        import warnings

        warnings.warn("No action taken. Comment is empty.")
        return
    close_session_when_done = False
    if session is None:  # pragma: no cover
        db = mc.connect_to_mc_db(None)
        session = db.sessionmaker()
        close_session_when_done = True

    pi = PartInfo()
    pi.hpn = hpn
    pi.hpn_rev = rev
    pi.posting_gpstime = int(
        cm_utils.get_astropytime(at_date, at_time, float_format).gps
    )
    pi.comment = comment
    pi.reference = reference
    session.add(pi)
    session.commit()
    if close_session_when_done:  # pragma: no cover
        session.close()


class Connections(MCDeclarativeBase):
    """
    A table for logging connections between parts.

    Part and Port must be unique when combined

    Attributes
    ----------
    upstream_part : String Column
        up refers to the skyward part,
        e.g. frontend:cable, 'A' is the frontend, 'B' is the cable.
        Signal flows from A->B"
        Part of the primary_key, Foreign Key into parts
    up_part_rev : String Column
        up refers to the skyward part revision number.
        Part of the primary_key, Foreign Key into parts
    upstream_output_port : String Column
        connected output port on upstream (skyward) part.
        Part of the primary_key
    downstream_part : String Column
        down refers to the part that is further from the sky, e.g.
        Part of the primary_key, Foreign Key into parts
    down_part_rev : String Column
        down refers to the part that is further from the sky, e.g.
        Part of the primary_key, Foreign Key into parts
    downstream_input_port : String Column
        connected input port on downstream (further from the sky) part
        Part of the primary_key
    start_gpstime : BigInteger Column
        start_time is the time that the connection is set
        Part of the primary_key
    stop_gpstime : BigInteger Column
        stop_time is the time that the connection is removed

    """

    __tablename__ = "connections"

    upstream_part = Column(String(64), nullable=False, primary_key=True)
    up_part_rev = Column(String(32), nullable=False, primary_key=True)
    upstream_output_port = NotNull(String(64), primary_key=True)
    downstream_part = Column(String(64), nullable=False, primary_key=True)
    down_part_rev = Column(String(64), nullable=False, primary_key=True)
    downstream_input_port = NotNull(String(64), primary_key=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["upstream_part", "up_part_rev"], ["parts.hpn", "parts.hpn_rev"]
        ),
        ForeignKeyConstraint(
            ["downstream_part", "down_part_rev"], ["parts.hpn", "parts.hpn_rev"]
        ),
    )

    start_gpstime = NotNull(BigInteger, primary_key=True)
    stop_gpstime = Column(BigInteger)

    def __repr__(self):
        """Define representation."""
        up = "{self.upstream_part}:{self.up_part_rev}".format(self=self)
        down = "{self.downstream_part}:{self.down_part_rev}".format(self=self)
        return (
            "<{}<{self.upstream_output_port}|{self.downstream_input_port}>{}>".format(
                up, down, self=self
            )
        )

    def __eq__(self, other):
        """Define equality."""
        if (
            isinstance(other, self.__class__)
            and self.upstream_part.upper() == other.upstream_part.upper()
            and self.up_part_rev.upper() == other.up_part_rev.upper()
            and self.upstream_output_port.upper() == other.upstream_output_port.upper()
            and self.downstream_part.upper() == other.downstream_part.upper()
            and self.down_part_rev.upper() == other.down_part_rev.upper()
            and self.downstream_input_port.upper()
            == other.downstream_input_port.upper()
        ):
            return True
        return False

    def gps2Time(self):
        """
        Add start_date and stop_date attributes (astropy Time objects).

        Based on start_gpstime and stop_gpstime.
        """
        self.start_date = Time(self.start_gpstime, format="gps")
        if self.stop_gpstime is None:
            self.stop_date = None
        else:
            self.stop_date = Time(self.stop_gpstime, format="gps")

    def connection(self, **kwargs):
        """
        Add arbitrary attributes passed in a dict to this object.

        Allows arbitrary connection to be specified.
        """
        for key, value in kwargs.items():
            setattr(self, key, value)

    def _to_dict(self):
        return {
            "upstream_part": self.upstream_part,
            "up_part_rev": self.up_part_rev,
            "upstream_output_port": self.upstream_output_port,
            "downstream_part": self.downstream_part,
            "down_part_rev": self.down_part_rev,
            "downstream_input_port": self.downstream_input_port,
        }


def get_connection_from_dict(input_dict):
    """
    Convert a dictionary holding the connection info into a Connections object.

    Parameter
    ---------
    input_dict : dictionary
        The dictionary must have the following keys:
            upstream_part, up_part_rev, upstream_output_port
            downstream_part, down_part_rev, downstream_input_port
        Other keys will be ignored.

    Returns
    -------
    Connections object

    """
    return Connections(
        upstream_part=input_dict["upstream_part"],
        up_part_rev=input_dict["up_part_rev"],
        upstream_output_port=input_dict["upstream_output_port"],
        downstream_part=input_dict["downstream_part"],
        down_part_rev=input_dict["down_part_rev"],
        downstream_input_port=input_dict["downstream_input_port"],
    )


def get_null_connection():
    """
    Return a null connection.

    All components hold the no_connection_designator and dates/times are None

    Returns
    -------
    Connections object

    """
    nc = no_connection_designator
    return Connections(
        upstream_part=nc,
        up_part_rev=nc,
        upstream_output_port=nc,
        downstream_part=nc,
        down_part_rev=nc,
        downstream_input_port=nc,
        start_gpstime=None,
        stop_gpstime=None,
    )


def stop_existing_connections_to_part(session, handling, conn_list, at_date):
    """
    Add stop times to the connections for parts listed in conn_list.

    Use this method with caution, as it currently doesn't include much checking.
    You probably should use the much more specific stop_connections method below.
    It is being kept around for possible use in future scripts that "remove" replaced parts.

    Parameters
    ----------
    session : object
        Database session to use.  If None, it will start a new session, then close.
    handling :  cm_handling object
        This is an instance of cm_handling used within this method.
    conn_list :  list
        This containing the connections to stop, as [[hpn0, rev0, port0], ...]
    at_date : astropy.Time object
        date at which to stop

    """
    stop_at = int(at_date.gps)
    data = []

    for conn in conn_list:
        part = handling.get_dossier(conn[0], conn[1], at_date=at_date, exact_match=True)
        if len(part):
            key = cm_utils.make_part_key(conn[0], conn[1])
            x = None
            if conn[2].lower() in part[key].input_ports:
                x = part[key].connections.down[conn[2].upper()]
            elif conn[2].lower() in part[key].output_ports:
                x = part[key].connections.up[conn[2].upper()]
            if x is not None:
                print("Stopping connection {} at {}".format(x, str(at_date)))
                stopping = [
                    x.upstream_part,
                    x.up_part_rev,
                    x.downstream_part,
                    x.down_part_rev,
                    x.upstream_output_port,
                    x.downstream_input_port,
                    x.start_gpstime,
                    "stop_gpstime",
                    stop_at,
                ]
                data.append(stopping)

    update_connection(session, data, False)


def stop_connections(session, conn_list, at_date):
    """
    Add a stop_date to the connections in conn_list.

    Parameters
    ----------
    session : object
        Database session to use.  If None, it will start a new session, then close.
    conn_list:  list of lists
        List with data [[upstream_part,rev,port,downstream_part,rev,port,start_gpstime],...]
    at_date : astropy.Time
        date at which to stop connection

    """
    stop_at = int(at_date.gps)
    data = []
    for conn in conn_list:
        print(
            "Stopping connection {}:{}<{} - {}>{}:{} at {}".format(
                conn[0], conn[1], conn[4], conn[2], conn[3], conn[5], str(at_date)
            )
        )
        this_one = []
        for cc in conn:
            this_one.append(cc)
        this_one.append("stop_gpstime")
        this_one.append(stop_at)
        data.append(this_one)

    update_connection(session, data, False)


def add_new_connections(session, cobj, conn_list, at_date):
    """
    Add a new connection based on a Connection object.

    This uses a connection object to send data to the update_connection method
    to make a new connection

    Parameters
    ----------
    session : object
        Database session to use.  If None, it will start a new session, then close.
    cobj : Connections object
        connection handling object
    conn_list:  list of lists
        List with data [[upstream_part,rev,port,downstream_part,rev,port,start_gpstime],...]
    at_date : astropy.Time
        date at which to start connection

    """
    start_at = int(at_date.gps)
    data = []

    for conn in conn_list:
        cobj.connection(
            upstream_part=conn[0],
            up_part_rev=conn[1],
            downstream_part=conn[3],
            down_part_rev=conn[4],
            upstream_output_port=conn[2],
            downstream_input_port=conn[5],
            start_gpstime=start_at,
            stop_gpstime=None,
        )
        print("Starting connection {} at {}".format(cobj, str(at_date)))
        data.append(
            [
                cobj.upstream_part,
                cobj.up_part_rev,
                cobj.downstream_part,
                cobj.down_part_rev,
                cobj.upstream_output_port,
                cobj.downstream_input_port,
                cobj.start_gpstime,
                "upstream_part",
                cobj.upstream_part,
            ]
        )
        data.append(
            [
                cobj.upstream_part,
                cobj.up_part_rev,
                cobj.downstream_part,
                cobj.down_part_rev,
                cobj.upstream_output_port,
                cobj.downstream_input_port,
                cobj.start_gpstime,
                "up_part_rev",
                cobj.up_part_rev,
            ]
        )
        data.append(
            [
                cobj.upstream_part,
                cobj.up_part_rev,
                cobj.downstream_part,
                cobj.down_part_rev,
                cobj.upstream_output_port,
                cobj.downstream_input_port,
                cobj.start_gpstime,
                "downstream_part",
                cobj.downstream_part,
            ]
        )
        data.append(
            [
                cobj.upstream_part,
                cobj.up_part_rev,
                cobj.downstream_part,
                cobj.down_part_rev,
                cobj.upstream_output_port,
                cobj.downstream_input_port,
                cobj.start_gpstime,
                "down_part_rev",
                cobj.down_part_rev,
            ]
        )
        data.append(
            [
                cobj.upstream_part,
                cobj.up_part_rev,
                cobj.downstream_part,
                cobj.down_part_rev,
                cobj.upstream_output_port,
                cobj.downstream_input_port,
                cobj.start_gpstime,
                "upstream_output_port",
                cobj.upstream_output_port,
            ]
        )
        data.append(
            [
                cobj.upstream_part,
                cobj.up_part_rev,
                cobj.downstream_part,
                cobj.down_part_rev,
                cobj.upstream_output_port,
                cobj.downstream_input_port,
                cobj.start_gpstime,
                "downstream_input_port",
                cobj.downstream_input_port,
            ]
        )
        data.append(
            [
                cobj.upstream_part,
                cobj.up_part_rev,
                cobj.downstream_part,
                cobj.down_part_rev,
                cobj.upstream_output_port,
                cobj.downstream_input_port,
                cobj.start_gpstime,
                "start_gpstime",
                cobj.start_gpstime,
            ]
        )

    update_connection(session, data, True)


def update_connection(session=None, data=None, add_new_connection=False):
    """
    Update the database given a connection with columns/values.

    Will add a new connection if add_new_connection flag is true

    Parameters
    ----------
    session : object
        Database session to use.  If None, it will start a new session, then close.
    data : list
        data for connection, parsable by format_check_update_connection_request
            columnN:  column name(s)
            values:  corresponding list of values
    add_new_connection :  bool
        Flag to actually allow it to be updated

    Returns
    -------
    bool
        True if succesful, otherwise False

    """
    data_dict = format_check_update_connection_request(data)
    if data_dict is None:
        print("Error: invalid update")
        return False

    close_session_when_done = False
    if session is None:  # pragma: no cover
        db = mc.connect_to_mc_db(None)
        session = db.sessionmaker()
        close_session_when_done = True

    for dkey in data_dict.keys():
        upcn_to_change = data_dict[dkey][0][0]
        urev_to_change = data_dict[dkey][0][1]
        dncn_to_change = data_dict[dkey][0][2]
        drev_to_change = data_dict[dkey][0][3]
        boup_to_change = data_dict[dkey][0][4]
        aodn_to_change = data_dict[dkey][0][5]
        strt_to_change = data_dict[dkey][0][6]
        conn_rec = session.query(Connections).filter(
            (Connections.upstream_part == upcn_to_change)
            & (Connections.up_part_rev == urev_to_change)
            & (Connections.downstream_part == dncn_to_change)
            & (Connections.down_part_rev == drev_to_change)
            & (Connections.upstream_output_port == boup_to_change)
            & (Connections.downstream_input_port == aodn_to_change)
            & (Connections.start_gpstime == strt_to_change)
        )
        num_conn = conn_rec.count()
        if num_conn == 0:
            if add_new_connection:
                connection = Connections()
                connection.connection(
                    up=upcn_to_change,
                    up_rev=urev_to_change,
                    down=dncn_to_change,
                    down_rev=drev_to_change,
                    upstream_output_port=boup_to_change,
                    downstream_input_port=aodn_to_change,
                    start_gpstime=strt_to_change,
                )
            else:
                print(
                    "Error:",
                    dkey,
                    "does not exist and add_new_connection is " "not enabled.",
                )
                connection = None
        elif num_conn == 1:
            if add_new_connection:
                print("Error:", dkey, "exists and and_new_connection is enabled")
                connection = None
            else:
                connection = conn_rec.first()
        else:  # pragma: no cover
            # we don't know how to cause this, thus the no cover. But we want to catch it
            # if it does happen.
            raise RuntimeError(
                "More than one of ",
                dkey,
                " exists. This should not happen, please " "make an issue on the repo!",
            )
            connection = None
        if connection:
            for d in data_dict[dkey]:
                try:
                    setattr(connection, d[7], d[8])
                except AttributeError:
                    print(dkey, "does not exist as a field")
                    continue
            session.add(connection)
            session.commit()
    cm_utils.log("cm_partconn connection update", data_dict=data_dict)
    if close_session_when_done:  # pragma: no cover
        session.close()

    return True


def format_check_update_connection_request(request):
    """
    Parse the update request.

    Parameters
    ----------
    request:   str, list
        columnN:  name of parts column
        valueN:  corresponding new value

    Returns
    -------
    dictionary
        The dictionary holds the parsed request appropriate for update_connection

    """
    if request is None:
        return None
    # Split out and get first
    data = {}
    if type(request) == str:
        tmp = request.split(",")
        data_to_proc = []
        for d in tmp:
            data_to_proc.append(d.split(":"))
    else:
        data_to_proc = request
    for d in data_to_proc:
        if len(d) == 9:
            pass
        elif len(d) == 7:
            d.insert(1, "LAST")
            d.insert(3, "LAST")
        else:
            print("Invalid format for connection update request.")
            continue
        dkey = d[0] + ":" + d[2] + ":" + d[4] + ":" + d[5]
        if dkey in data.keys():
            data[dkey].append(d)
        else:
            data[dkey] = [d]
    return data
