# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Keep track of geo-located stations."""

from astropy.time import Time
from sqlalchemy import Column, Float, String, BigInteger, ForeignKey, func

from . import MCDeclarativeBase, NotNull
from . import mc, cm_utils


class StationType(MCDeclarativeBase):
    """
    Table to track/denote station type data categories in various ways.

    Attributes
    ----------
    station_type_name : String Column
        Name of type class, Primary_key
    prefix : String Column
        String prefix to station type, elements of which are typically
        characterized by <prefix><int>. Comma-delimit list if more than one.
        Note that prefix is not in the primary_key, so there can be multiple
        prefixes per type_name.
    description : String Column
        hort description of station type.
    plot_marker : String Column
        matplotlib marker type to use

    """

    __tablename__ = "station_type"

    station_type_name = Column(String(64), primary_key=True)
    prefix = NotNull(String(64))
    description = Column(String(64))
    plot_marker = Column(String(64))

    def __repr__(self):
        """Define representation."""
        return (
            "<subarray {self.station_type_name}: prefix={self.prefix} "
            "description={self.description} marker={self.plot_marker}>".format(
                self=self
            )
        )


class GeoLocation(MCDeclarativeBase):
    """
    A table logging stations within HERA.

    Attributes
    ----------
    station_name : String Column
        Colloquial name of station (which is a unique location on the ground).
        This one shouldn't change. Primary_key
    station_type_name : String Column
        Name of station type of which it is a member.
        Should match prefix per station_type table.
    datum : String Column
        Datum of the geoid.
    tile : String Column
        UTM tile
    northing : Float Column
        Northing coordinate in m
    easting : Float Column
        Easting coordinate in m
    elevation : Float Column
        Elevation in m
    created_gpstime : BigInteger Column
        The date when the station assigned by project.

    """

    __tablename__ = "geo_location"

    station_name = Column(String(64), primary_key=True)
    station_type_name = Column(
        String(64), ForeignKey(StationType.station_type_name), nullable=False
    )
    datum = Column(String(64))
    tile = Column(String(64))
    northing = Column(Float(precision="53"))
    easting = Column(Float(precision="53"))
    elevation = Column(Float)
    created_gpstime = NotNull(BigInteger)

    def gps2Time(self):
        """Add a created_date attribute -- an astropy Time object based on created_gpstime."""
        self.created_date = Time(self.created_gpstime, format="gps")

    def geo(self, **kwargs):
        """Add arbitrary attributes to object based on dict."""
        for key, value in kwargs.items():
            if key == "station_name":
                value = value.upper()
            setattr(self, key, value)

    def __repr__(self):
        """Define representation."""
        return "<station_name={self.station_name} station_type={self.station_type_name} \
        northing={self.northing} easting={self.easting} \
        elevation={self.elevation}>".format(
            self=self
        )


def update(session=None, data=None, add_new_geo=False):
    """
    Update the geo_location table with some data.

    Use with caution -- should usually use in a script which will do datetime
    primary key etc.

    Parameters
    ----------
    session : session
        session on current database. If session is None, a new session
        on the default database is created and used.
    data : str or list
        [[station_name0,column0,value0],[...]]
        where
                station_nameN:  station_name (starts with char)
                values:  corresponding list of values
    add_new_geo : bool
        allow a new entry to be made.

    Returns
    -------
    bool
        Flag if successful

    """
    data_dict = format_check_update_request(data)
    if data_dict is None:
        print("No update - doing nothing.")
        return False

    close_session_when_done = False
    if session is None:  # pragma: no cover
        db = mc.connect_mc_db()
        session = db.sessionmaker()
        close_session_when_done = True

    for station_name in data_dict.keys():
        geo_rec = session.query(GeoLocation).filter(
            func.upper(GeoLocation.station_name) == station_name.upper()
        )
        num_rec = geo_rec.count()
        make_update = False
        if num_rec == 0:
            if add_new_geo:
                gr = GeoLocation()
                make_update = True
            else:
                raise ValueError(
                    "{} does not exist and add_new_geo not enabled.".format(
                        station_name
                    )
                )
        elif num_rec == 1:
            if add_new_geo:
                raise ValueError(
                    "{} exists and and_new_geo is enabled.".format(station_name)
                )
            else:
                gr = geo_rec.first()
                make_update = True
        if make_update:
            for d in data_dict[station_name]:
                setattr(gr, d[1], d[2])
            session.add(gr)
            session.commit()
    cm_utils.log("geo_location update", data_dict=data_dict)
    if close_session_when_done:  # pragma: no cover
        session.close()

    return True


def format_check_update_request(request):
    """
    Parse the update request for use in the update function.

    Parameters
    ----------
    request : str or list
        station_name0:column0:value0, [station_name1:]column1:value1, [...] or list
        station_nameN: first entry must have the station_name,
                       if it does not then propagate first station_name but
                       can't restart 3 then 2
        columnN:  name of geo_location column
        valueN:  corresponding new value

    Returns
    -------
    dict
        Parsed request for update

    """
    if request is None:
        return None
    data = {}
    if type(request) == str:
        tmp = request.split(",")
        data_to_proc = []
        for d in tmp:
            data_to_proc.append(d.split(":"))
    else:
        data_to_proc = request
    if len(data_to_proc[0]) == 3:
        station_name0 = data_to_proc[0][0]
        for d in data_to_proc:
            if len(d) == 2:
                d.insert(0, station_name0)
            elif len(d) != 3:
                raise ValueError("Invalid format for update request.")
            if d[0] in data.keys():
                data[d[0]].append(d)
            else:
                data[d[0]] = [d]
    else:
        raise ValueError(
            "Invalid parse request - need 3 parameters for at least first one."
        )
    return data
