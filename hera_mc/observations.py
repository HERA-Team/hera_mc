# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Observation table."""

from astropy.coordinates import EarthLocation
from astropy.time import Time
from sqlalchemy import BigInteger, Column, Float, String
from sqlalchemy.ext.hybrid import hybrid_property

from . import DEFAULT_DAY_TOL, DEFAULT_GPS_TOL, DEFAULT_HOUR_TOL, MCDeclarativeBase

allowed_tags = ["science", "maintenance", "engineering", "junk"]


class Observation(MCDeclarativeBase):
    """
    Definition of hera_obs table.

    Definition of node sensor table.

    Attributes
    ----------
    obsid : BigInteger Column
        Observation identification number, generally equal to the floor of
        the start time in gps seconds. The primary key.
    starttime : Float Column
        Observation start time in gps seconds.
    stoptime : Float Column
        Observation stop time in gps seconds.
    jd_start : Float Column
        Observation start time in JDs, calculated from starttime.
    lststart : Float Column
        Observation start time in lst, calculated from starttime and HERA array
        location.
    tag : String Column
        String tag labelling the type of data. One of ["science", "maintenance",
        "engineering", "junk"]. The "science" label should be used for data that are
        expected to be good for science at the time of observation. The
        "maintenance" label should be used for regular FEM load/noise observations,
        "junk" should be used for data that should not be kept, "engineering"
        should be used for any other kind of non-science data.

    """

    __tablename__ = "hera_obs"
    obsid = Column(BigInteger, primary_key=True, autoincrement=False)
    starttime = Column(
        Float, nullable=False
    )  # Float is mapped to DOUBLE PRECISION in postgresql
    stoptime = Column(Float, nullable=False)
    jd_start = Column(Float, nullable=False)
    lst_start_hr = Column(Float, nullable=False)
    tag = Column(String, nullable=True)

    # tolerances set to 1ms
    tols = {
        "starttime": DEFAULT_GPS_TOL,
        "stoptime": DEFAULT_GPS_TOL,
        "jd_start": DEFAULT_DAY_TOL,
        "lst_start_hr": DEFAULT_HOUR_TOL,
    }

    @hybrid_property
    def length(self):
        """Observation length in seconds."""
        return self.stoptime - self.starttime

    @classmethod
    def create(cls, starttime, stoptime, obsid, hera_cofa, tag):
        """
        Create a new observation object using Astropy to compute the LST.

        Parameters
        ----------
        starttime : astropy Time object
            Observation starttime.
        stoptime : astropy Time object
            Observation stoptime.
        obsid : long integer
            Observation identification number.
        hera_cofa : geo_location.GeoLocation object (row of geo_location table)
            Location of the Center OF the Array.
        tag : string
            String tag labelling the type of data. One of ["science", "maintenance",
            "engineering", "junk"]. The "science" label should be used for data that are
            expected to be good for science at the time of observation. The
            "maintenance" label should be used for regular FEM load/noise observations,
            "junk" should be used for data that should not be kept, "engineering"
            should be used for any other kind of non-science data.

        """
        if not isinstance(starttime, Time):
            raise ValueError("starttime must be an astropy Time object")
        if not isinstance(stoptime, Time):
            raise ValueError("stoptime must be an astropy Time object")
        if not isinstance(obsid, int):
            raise ValueError("obsid must be an integer")
        if abs(float(obsid) - starttime.gps) > 1.5:
            raise ValueError("obsid should be close to the starttime in gps seconds")

        if tag not in allowed_tags:
            raise ValueError(f"Tag is {tag}, should be one of: {allowed_tags}")

        # for jd need to ensure that we're in utc
        starttime = Time(
            starttime,
            location=EarthLocation.from_geodetic(hera_cofa.lon, hera_cofa.lat),
        ).utc

        return cls(
            obsid=obsid,
            starttime=starttime.gps,
            stoptime=stoptime.gps,
            jd_start=starttime.jd,
            lst_start_hr=starttime.sidereal_time("apparent").hour,
            tag=tag,
        )
