# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.
"""
Primary session object which handles most DB queries.

See INSTALL.md in the Git repository for instructions on how to initialize
your database and configure M&C to find it.
"""

import os
import warnings
from math import floor

import numpy as np
import yaml
from astropy.time import Time
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import func

from . import cm_utils
from . import correlator as corr
from . import geo_handling, node, rtp
from .autocorrelations import (
    HeraAuto,
    HeraAutoSpectrum,
    _get_autos_from_redis,
    measurement_func_dict,
)
from .cm_active import ActiveData
from .cm_hookup import Hookup
from .daemon_status import DaemonStatus
from .librarian import (
    LibFiles,
    LibRAIDErrors,
    LibRAIDStatus,
    LibRemoteStatus,
    LibStatus,
)
from .observations import Observation
from .qm import AntMetrics, ArrayMetrics, MetricList
from .subsystem_error import SubsystemError
from .weather import WeatherData, create_from_sensors, weather_sensor_dict


class MCSession(Session):
    """Primary session object that handles most DB queries."""

    def __enter__(self):
        """Enter the session."""
        return self

    def __exit__(self, etype, evalue, etb):
        """Exit the session, rollback if there's an error otherwise commit."""
        if etype is not None:
            self.rollback()  # exception raised
        else:
            self.commit()  # success
        self.close()
        return False  # propagate exception if any occurred

    def get_current_db_time(self):
        """
        Get the current time according to the database.

        Returns
        -------
        astropy Time object
            Current database time as an astropy time object.

        """
        db_timestamp = self.execute(func.current_timestamp()).scalar()

        # convert to astropy time object
        db_time = Time(db_timestamp)
        return db_time

    def add_corr_obj(self, force=False, redishost=corr.DEFAULT_REDIS_ADDRESS):
        """
        Add a HeraCorrCM object to self to talk to the correlator.

        Parameters
        ----------
        force : bool
            Option to force a command that might interfere with observing even
            if the correlator is currently taking data. This will only have an
            effect for commands that are not usually allowed while data is being
            taken (e.g restart, hard_stop, phase switching/load/noise diode
            state changes). Done by setting the `danger_mode` keyword on the
            HeraCorrCM object. To avoid unexpected behavior, always set this
            attribute so it will be False unless specifically set to True.
        redishost : str
            redis address to use. Defaults to correlator.DEFAULT_REDIS_ADDRESS.

        """
        import hera_corr_cm

        if (
            not hasattr(self, "corr_obj")
            or redishost not in self.corr_obj.redis_connections
        ):
            self.corr_obj = hera_corr_cm.HeraCorrCM(redishost=redishost)

        self.corr_obj.danger_mode = force

    def _write_query_to_file(self, query, table_class, filename=None):
        """
        Write out query results to a file.

        Parameters
        ----------
        table_class : class
            Class specifying a table to query.
        query : query object
            Query to write results of to filename.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.

        """
        if filename is None:
            table_name = getattr(table_class, "__tablename__")
            filename = table_name + ".csv"

        column_names = [
            col.name for col in (getattr(getattr(table_class, "__table__"), "_columns"))
        ]
        with open(filename, "w") as the_file:
            # write header
            the_file.write(", ".join(column_names) + "\n")

            # write rows
            for item in query:
                item_vals = [str(getattr(item, col)) for col in column_names]
                the_file.write(", ".join(item_vals) + "\n")

    def _time_filter(
        self,
        table_class,
        time_column,
        most_recent=None,
        starttime=None,
        stoptime=None,
        filter_column=None,
        filter_value=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Fiter entries by time, used by most get methods on this object.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        table_class : class
            Class specifying a table to query.
        time_column : str
            column name holding the time to filter on.
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record(s) after starttime will be returned
            (can be more than one record if multiple records share the same
            time). Ignored if most_recent is True.
        filter_column : str or list of str
            Column name(s) to use as an additional filter (often a part of the
            primary key).
        filter_value : str or int or list of str or int
            Type coresponds to filter_column(s), value(s) to require
            that the filter_column(s) are equal to.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of objects, optional
            If write_to_file is False: List of objects that match the filtering.

        """
        if starttime is None and most_recent is None:
            most_recent = True

        if not isinstance(most_recent, (type(None), bool)):
            raise TypeError("most_recent must be None or a boolean")

        if not most_recent:
            if starttime is None:
                raise ValueError("starttime must be specified if most_recent is False")

        if starttime is not None and not isinstance(starttime, Time):
            raise ValueError(
                "starttime must be an astropy time object. "
                "value was: {t}".format(t=starttime)
            )

        if stoptime is not None and not isinstance(stoptime, Time):
            raise ValueError(
                "stoptime must be an astropy time object. "
                "value was: {t}".format(t=stoptime)
            )

        time_attr = getattr(table_class, time_column)

        if filter_value is not None:
            if isinstance(filter_column, (list)):
                assert isinstance(filter_value, (list)), (
                    f"Inconsistent filtering keywords for {table_class.__tablename__} "
                    "table. This is a bug, please report it in the issue log."
                )
                assert len(filter_column) == len(filter_value), (
                    f"Inconsistent filtering keywords for {table_class.__tablename__} "
                    "table. This is a bug, please report it in the issue log."
                )
            else:
                filter_column = [filter_column]
                filter_value = [filter_value]
            filter_attr = []
            for col in filter_column:
                filter_attr.append(getattr(table_class, col))

        query = self.query(table_class)
        if filter_value is not None:
            for index, val in enumerate(filter_value):
                if val is not None:
                    query = query.filter(filter_attr[index] == val)

        if most_recent or stoptime is None:
            if most_recent and starttime is None:
                current_time = Time.now()
                # get most recent row
                first_query = (
                    query.filter(time_attr <= current_time.gps)
                    .order_by(desc(time_attr))
                    .limit(1)
                )
            elif most_recent:
                # get last row before starttime
                first_query = (
                    query.filter(time_attr <= starttime.gps)
                    .order_by(desc(time_attr))
                    .limit(1)
                )
            else:
                # get first row after starttime
                first_query = (
                    query.filter(time_attr >= starttime.gps)
                    .order_by(asc(time_attr))
                    .limit(1)
                )

            # get the time of the first row
            first_result = first_query.all()
            if len(first_result) < 1:
                query = first_query
            else:
                first_time = getattr(first_result[0], time_column)
                if isinstance(first_time, float):
                    query = first_query
                else:
                    # then get all results at that time (for integer times)
                    query = query.filter(time_attr == first_time)
                    if filter_value is not None:
                        for attr in filter_attr:
                            query = query.order_by(asc(attr))

        else:
            query = query.filter(time_attr.between(starttime.gps, stoptime.gps))
            query = query.order_by(time_attr)
            if filter_value is not None:
                for attr in filter_attr:
                    query = query.order_by(asc(attr))

        if write_to_file:
            self._write_query_to_file(query, table_class, filename=filename)
        else:
            return query.all()

    def _insert_ignoring_duplicates(self, table_class, obj_list, update=False):
        """
        Insert record handling duplication based on update flag.

        If the current database is PostgreSQL, this function will use a
        special insertion method that will ignore or update records that are
        redundant with ones already in the database. This makes it convenient to
        sample certain data (especially redis data) densely on qmaster or to
        update an existing record.

        Parameters
        ----------
        table_class : class
            Class specifying a table to insert into.
        obj_list : list of objects
            List of objects (of class table_class) to insert into the table.
        update : bool
            If true, update the existing record with the new data, otherwise do
            nothing (which is appropriate if the data is the same because of
            dense sampling).

        """
        if self.bind.dialect.name == "postgresql":
            from sqlalchemy import inspect
            from sqlalchemy.dialects.postgresql import insert

            ies = [c.name for c in inspect(table_class).primary_key]
            conn = self.connection()

            for obj in obj_list:
                # This appears to be the most correct way to map each row
                # object into a dictionary:
                values = {}
                for col in inspect(obj).mapper.column_attrs:
                    values[col.expression.name] = getattr(obj, col.key)

                if update:
                    # create dict of columns to update (everything other than
                    # the primary keys)
                    update_dict = {}
                    for col, val in values.items():
                        if col not in ies:
                            update_dict[col] = val

                    # The special PostgreSQL insert statement lets us update
                    # existing rows via `ON CONFLICT ... DO UPDATE` syntax.
                    stmt = (
                        insert(table_class)
                        .values(**values)
                        .on_conflict_do_update(index_elements=ies, set_=update_dict)
                    )
                else:
                    # The special PostgreSQL insert statement lets us ignore
                    # existing rows via `ON CONFLICT ... DO NOTHING` syntax.
                    stmt = (
                        insert(table_class)
                        .values(**values)
                        .on_conflict_do_nothing(index_elements=ies)
                    )
                conn.execute(stmt)
        else:  # pragma: no cover
            # Generic approach:
            for obj in obj_list:
                self.add(obj)

    def add_obs(self, starttime, stoptime, obsid, tag):
        """
        Add a new observation to the M&C database.

        Parameters
        ----------
        starttime : astropy Time object
            Observation starttime.
        stoptime : astropy Time object
            Observation stoptime.
        obsid : long integer
            Observation identification number, the gps second of the starttime,
            floored.
        tag : string
            String tag labelling the type of data. One of ["science", "maintainence",
            "engineering", "junk"]. The "science" label should be used for data that are
            expected to be good for science at the time of observation. The
            "mantainence" label should be used for regular FEM load/noise observations,
            "junk" should be used for data that should not be kept, "engineering"
            should be used for any other kind of non-science data.

        """
        h = geo_handling.Handling(session=self)
        hera_cofa = h.cofa()[0]

        self.add(Observation.create(starttime, stoptime, obsid, hera_cofa, tag))

    def get_obs(self, obsid=None, tag=None):
        """
        Get observation(s) from the M&C database.

        Parameters
        ----------
        obsid : long integer
            Observation identification number, generally the gps second
            corresponding to the observation start time. If obsid is None,
            all obsids will be returned.
        tag : string
            Observing tag, one of ["science", "maintainence", "engineering", "junk"].
            If tag is none, no filtering by tag is applied. Note that older obsids have
            a null tag, so tag should not be used for data from before the 2022-2023
            season.

        Returns
        -------
        list of Observation objects

        """
        query = self.query(Observation)
        if obsid is not None:
            query = query.filter(Observation.obsid == obsid)
        if tag is not None:
            query = query.filter(Observation.tag == tag)
        obs_list = query.all()

        return obs_list

    def get_obs_by_time(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        tag=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get observation(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        tag : string
            Observing tag, one of ["science", "maintainence", "engineering", "junk"].
            If tag is none, no filtering by tag is applied. Note that older obsids have
            a null tag, so tag should not be used for data from before the 2022-2023
            season.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of Observation objects.

        """
        return self._time_filter(
            Observation,
            "obsid",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            filter_column=["tag"],
            filter_value=tag,
            write_to_file=write_to_file,
            filename=filename,
        )

    def add_server_status(
        self,
        subsystem,
        hostname,
        ip_address,
        system_time,
        num_cores,
        cpu_load_pct,
        uptime_days,
        memory_used_pct,
        memory_size_gb,
        disk_space_pct,
        disk_size_gb,
        network_bandwidth_mbs=None,
    ):
        """
        Add a new subsystem server_status to the M&C database.

        Parameters
        ----------
        subsystem : str
            Name of subsystem. Must be one of ['rtp', 'lib'].
        hostname : str
            Name of server.
        ip_address : str
            IP address of server
        system_time : astropy Time object
            Time report sent by server.
        num_cores : int
            Number of cores on server.
        cpu_load_pct : float
            CPU load percent = total load / num_cores, 5 min average.
        uptime_days : float
            Server uptime in decimal days.
        memory_used_pct : float
            Percent of memory used, 5 min average.
        memory_size_gb : float
            Amount of memory on server in GB.
        disk_space_pct : float
            Percent of disk used.
        disk_size_gb : float
            Amount of disk space on server in GB.
        network_bandwidth_mbs : float
            Network bandwidth in MB/s, 5 min average. Can be null if not
            applicable.

        """
        if subsystem == "rtp":
            from .rtp import RTPServerStatus as ServerStatus
        elif subsystem == "lib":
            from .librarian import LibServerStatus as ServerStatus
        else:
            raise ValueError('subsystem must be one of: ["rtp", "lib"]')

        db_time = self.get_current_db_time()

        self.add(
            ServerStatus.create(
                db_time,
                hostname,
                ip_address,
                system_time,
                num_cores,
                cpu_load_pct,
                uptime_days,
                memory_used_pct,
                memory_size_gb,
                disk_space_pct,
                disk_size_gb,
                network_bandwidth_mbs=network_bandwidth_mbs,
            )
        )

    def get_server_status(
        self,
        subsystem,
        most_recent=None,
        starttime=None,
        stoptime=None,
        hostname=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get subsystem server_status record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        subsystem : str
            Name of subsystem. Must be one of ['rtp', 'lib'].
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        hostname : str
            Hostname to get records for. If none, all hostnames will be
            included.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of ServerStatus objects

        """
        if subsystem == "rtp":
            from .rtp import RTPServerStatus as ServerStatus
        elif subsystem == "lib":
            from .librarian import LibServerStatus as ServerStatus
        else:
            raise ValueError('subsystem must be one of: ["rtp", "lib"]')

        return self._time_filter(
            ServerStatus,
            "mc_time",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            filter_column="hostname",
            filter_value=hostname,
            write_to_file=write_to_file,
            filename=filename,
        )

    def get_rtp_server_status(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        hostname=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get rtp_server_status record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        hostname : str
            Hostname to get records for. If none, all hostnames will be
            included.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of RTPServerStatus objects

        """
        return self.get_server_status(
            "rtp",
            most_recent=None,
            starttime=None,
            stoptime=None,
            hostname=None,
            write_to_file=False,
            filename=None,
        )

    def get_librarian_server_status(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        hostname=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get librarian_server_status record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        hostname : str
            Hostname to get records for. If none, all hostnames will be
            included.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of LibServerStatus objects

        """
        return self.get_server_status(
            "lib",
            most_recent=None,
            starttime=None,
            stoptime=None,
            hostname=None,
            write_to_file=False,
            filename=None,
        )

    def add_subsystem_error(self, time, subsystem, severity, log, testing=False):
        """
        Add a new subsystem_error to the M&C database.

        Parameters
        ----------
        time : astropy Time object
            Time of this error report.
        subsystem : str
            Name of subsystem with error.
        severity : int
            Integer indicating severity level, 1 is most severe.
        log : str
            Error message or log file name (TBD).
        testing : bool
            Option to just return the objects rather than adding them to the DB.

        """
        db_time = self.get_current_db_time()

        error_obj = SubsystemError.create(db_time, time, subsystem, severity, log)

        if testing:
            return error_obj

        self.add(error_obj)

    def get_subsystem_error(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        subsystem=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get subsystem server_status record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        subsystem : str
            subsystem to get records for. If none, all subsystems will be
            included.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of SubsystemError objects

        """
        return self._time_filter(
            SubsystemError,
            "time",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            filter_column="subsystem",
            filter_value=subsystem,
            write_to_file=write_to_file,
            filename=filename,
        )

    def add_daemon_status(self, name, hostname, time, status, testing=False):
        """
        Add a new daemon_status to the M&C database.

        If the current database is PostgreSQL, this function will use a
        special insertion method that will update records that are redundant
        with ones already in the database.

        Parameters
        ----------
        name : str
            Name of the daemon.
        hostname : str
            Name of server where daemon is running.
        time : astropy Time object
            Time of this status report, updated on every iteration of the
            daemon.
        status : str
            Status, one of the values in status_list.
        testing : bool
            Option to just return the objects rather than adding them to the DB.

        """
        daemon_status_obj = DaemonStatus.create(name, hostname, time, status)

        if testing:
            return daemon_status_obj

        self._insert_ignoring_duplicates(DaemonStatus, [daemon_status_obj], update=True)

    def get_daemon_status(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        daemon_name=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get daemon_status record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        daemon_name : str
            Name of daemon to get records for. If none, all daemons will be
            included.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of DaemonStatus objects

        """
        return self._time_filter(
            DaemonStatus,
            "time",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            filter_column="name",
            filter_value=daemon_name,
            write_to_file=write_to_file,
            filename=filename,
        )

    def add_lib_status(
        self,
        time,
        num_files,
        data_volume_gb,
        free_space_gb,
        upload_min_elapsed,
        num_processes,
        git_version,
        git_hash,
    ):
        """
        Add a new lib_status object.

        Parameters
        ----------
        time : astropy Time object
            Time of this status.
        num_files : int
            Number of files in librarian.
        data_volume_gb : float
            Data volume in GB.
        free_space_gb : float
            Free space in GB.
        upload_min_elapsed : float
            Minutes since last file upload.
        num_processes : int
            Number of background tasks running.
        git_version : str
            Librarian git version.
        git_hash : str
            Librarian git hash.

        """
        self.add(
            LibStatus.create(
                time,
                num_files,
                data_volume_gb,
                free_space_gb,
                upload_min_elapsed,
                num_processes,
                git_version,
                git_hash,
            )
        )

    def get_lib_status(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get lib_status record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of LibStatus objects

        """
        return self._time_filter(
            LibStatus,
            "time",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            write_to_file=write_to_file,
            filename=filename,
        )

    def add_lib_raid_status(self, time, hostname, num_disks, info):
        """
        Add a new lib_raid_status object.

        Parameters
        ----------
        time : astropy Time object
            Time of this status.
        hostname : str
            Name of RAID server.
        num_disks : int
            Number of disks in RAID server.
        info : str
            TBD info from megaraid controller.

        """
        self.add(LibRAIDStatus.create(time, hostname, num_disks, info))

    def get_lib_raid_status(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        hostname=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get lib_raid_status record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        hostname : str
            RAID hostname to get records for. If none, all hostnames will be
            included.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of LibRAIDStatus objects

        """
        return self._time_filter(
            LibRAIDStatus,
            "time",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            filter_column="hostname",
            filter_value=hostname,
            write_to_file=write_to_file,
            filename=filename,
        )

    def add_lib_raid_error(self, time, hostname, disk, log):
        """
        Add a new lib_raid_error object.

        Parameters
        ----------
        time : astropy Time object
            Time of this error.
        hostname : str
            Name of RAID server with error.
        disk : str
            Name of disk with error.
        log : str
            Error message or log file name (TBD).

        """
        self.add(LibRAIDErrors.create(time, hostname, disk, log))

    def get_lib_raid_error(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        hostname=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get lib_raid_error record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        hostname : str
            RAID hostname to get records for. If none, all hostnames will be
            included.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of LibRAIDErrors objects

        """
        return self._time_filter(
            LibRAIDErrors,
            "time",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            filter_column="hostname",
            filter_value=hostname,
            write_to_file=write_to_file,
            filename=filename,
        )

    def add_lib_remote_status(
        self, time, remote_name, ping_time, num_file_uploads, bandwidth_mbs
    ):
        """
        Add a new lib_remote_status object.

        Parameters
        ----------
        time : astropy Time object
            Time of this status.
        remote_name : str
            Name of remote server.
        ping_time : float
            Ping time to remote in seconds.
        num_file_uploads : int
            Number of file uploads to remote in last 15 minutes.
        bandwidth_mbs : float
            Bandwidth to remote in Mb/s, 15 minute average.

        """
        self.add(
            LibRemoteStatus.create(
                time, remote_name, ping_time, num_file_uploads, bandwidth_mbs
            )
        )

    def get_lib_remote_status(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        remote_name=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get lib_remote_status record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        remote_name : str
            Name of remote librarian to get records for. If none, all
            remote_names will be included.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of LibRemoteStatus objects

        """
        return self._time_filter(
            LibRemoteStatus,
            "time",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            filter_column="remote_name",
            filter_value=remote_name,
            write_to_file=write_to_file,
            filename=filename,
        )

    def add_lib_file(self, filename, obsid, time, size_gb):
        """
        Add a new lib_file row.

        Parameters
        ----------
        filename : str
            Name of file created.
        obsid : long or None
            Optional observation obsid (Foreign key into Observation).
        time : astropy Time object
            Time file was created.
        size_gb : float
            File size in GB.

        """
        self.add(LibFiles.create(filename, obsid, time, size_gb))

    def get_lib_files(
        self,
        filename=None,
        obsid=None,
        most_recent=None,
        starttime=None,
        stoptime=None,
        write_to_file=False,
        write_filename=None,
    ):
        """
        Get lib_files record(s) from the M&C database.

        If filename is provided, all other optional keywords are ignored.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        filename : str
            Filename to get records for.
        obsid : long
            Obsid to get records for. If starttime and most_recent are both
            None, all files for this obsid will be returned.
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        write_to_file : bool
            Option to write records to a CSV file.
        write_filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of LibFiles objects

        """
        if filename is not None:
            query = self.query(LibFiles).filter(LibFiles.filename == filename)
        else:
            if most_recent is not None or starttime is not None:
                return self._time_filter(
                    LibFiles,
                    "time",
                    most_recent=most_recent,
                    starttime=starttime,
                    stoptime=stoptime,
                    filter_column="obsid",
                    filter_value=obsid,
                    write_to_file=write_to_file,
                    filename=write_filename,
                )
            else:
                if obsid is not None:
                    query = self.query(LibFiles).filter(LibFiles.obsid == obsid)
                else:
                    query = self.query(LibFiles)

        if write_to_file:
            self._write_query_to_file(query, LibFiles, filename=write_filename)
        else:
            return query.all()

    def add_rtp_process_event(self, time, obsid, event):
        """
        Add a new rtp_process_event row.

        Parameters
        ----------
        time : astropy Time object
            Time of event.
        obsid : long
            Observation obsid (Foreign key into observation).
        event : {"queued", "started", "finished", "error"}
            Event type.

        """
        self.add(rtp.RTPProcessEvent.create(time, obsid, event))

    def get_rtp_process_event(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        obsid=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get rtp_process_event record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        obsid : long
            obsid to get records for. If none, all obsid will be included.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of RTPProcessEvent objects

        """
        return self._time_filter(
            rtp.RTPProcessEvent,
            "time",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            filter_column="obsid",
            filter_value=obsid,
            write_to_file=write_to_file,
            filename=filename,
        )

    def add_rtp_task_process_event(self, time, obsid, task_name, event):
        """
        Add a new rtp_task_process_event row.

        Parameters
        ----------
        time : astropy Time object
            Time of event.
        obsid : long
            Observation obsid (Foreign key into observation).
        task_name : str
            Name of task in pipeline (e.g., OMNICAL).
        event : {"queued", "started", "finished", "error"}
            Event type.

        """
        self.add(rtp.RTPTaskProcessEvent.create(time, obsid, task_name, event))

    def get_rtp_task_process_event(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        obsid=None,
        task_name=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get rtp_task_process_event record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None. If
            None, only the first record after starttime will be
            returned. Ignored if most_recent is True.
        obsid : long
            obsid to get records for. If None, all obsids will be included.
        task_name : str
            task_name to get records for. If None, all task_names will be included.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name. Ignored if
            write_to_file is False.

        Returns
        -------
        list of RTPTaskProcessEvent objects

        Raises
        ------
        ValueError
            If `most_recent` is False and all of obsid, task_name, and starttime are None.

        """
        if obsid is None and task_name is None and starttime is None:
            if most_recent is None:
                most_recent = True
            elif most_recent is False:
                raise ValueError(
                    "If most_recent is set to False, at least one of obsid, "
                    "task_name, or starttime must be specified."
                )

        if most_recent is True or starttime is not None:
            return self._time_filter(
                rtp.RTPTaskProcessEvent,
                "time",
                most_recent=most_recent,
                starttime=starttime,
                stoptime=stoptime,
                filter_column=["obsid", "task_name"],
                filter_value=[obsid, task_name],
                write_to_file=write_to_file,
                filename=filename,
            )

        query = self.query(rtp.RTPTaskProcessEvent)
        if obsid is not None:
            query = query.filter(rtp.RTPTaskProcessEvent.obsid == obsid)
        if task_name is not None:
            query = query.filter(rtp.RTPTaskProcessEvent.task_name == task_name)

        if write_to_file:
            self._write_query_to_file(query, rtp.RTPTaskProcessEvent, filename=filename)
        else:
            return query.all()

    def add_rtp_task_multiple_process_event(self, time, obsid, task_name, event):
        """
        Add a new rtp_task_multiple_process_event row.

        Parameters
        ----------
        time : astropy Time object
            Time of event.
        obsid : long
            Observation obsid for the first obsid (Foreign key into observation).
        task_name : str
            Name of task in pipeline (e.g., OMNICAL)
        event : {"started", "finished", "error"}
            Event type.
        """
        self.add(rtp.RTPTaskMultipleProcessEvent.create(time, obsid, task_name, event))

    def get_rtp_task_multiple_process_event(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        obsid_start=None,
        task_name=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get rtp_task_multiple_process_event record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None. If
            None, only the first record after starttime will be
            returned. Ignored if most_recent is True.
        obsid_start : long
            obsid_start to get records for. If None, all task_names will be
            included.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directoryo named based on the table name. Ignored if
            write_to_file is False.

        Returns
        -------
        list of RTPTaskMultipleProcessEvent objects

        Raises
        ------
        ValueError
            If `most_recent` is False and all of obsid_start, task_name, and
            starttime are None.
        """
        if obsid_start is None and task_name is None and starttime is None:
            if most_recent is None:
                most_recent = True
            elif most_recent is False:
                raise ValueError(
                    "If most_recent is set to False, at least one of obsid, "
                    "task_name, or starttime must be specified."
                )

        if most_recent is True or starttime is not None:
            return self._time_filter(
                rtp.RTPTaskMultipleProcessEvent,
                "time",
                most_recent=most_recent,
                starttime=starttime,
                stoptime=stoptime,
                filter_column=["obsid_start", "task_name"],
                filter_value=[obsid_start, task_name],
                write_to_file=write_to_file,
                filename=filename,
            )

        query = self.query(rtp.RTPTaskMultipleProcessEvent)
        if obsid_start is not None:
            query = query.filter(
                rtp.RTPTaskMultipleProcessEvent.obsid_start == obsid_start
            )
        if task_name is not None:
            query = query.filter(rtp.RTPTaskMultipleProcessEvent.task_name == task_name)

        if write_to_file:
            self._write_query_to_file(
                query, rtp.RTPTaskMultipleProcessEvent, filename=filename
            )
        else:
            return query.all()

    def add_rtp_process_record(
        self,
        time,
        obsid,
        pipeline_list,
        rtp_git_version,
        rtp_git_hash,
        hera_qm_git_version,
        hera_qm_git_hash,
        hera_cal_git_version,
        hera_cal_git_hash,
        pyuvdata_git_version,
        pyuvdata_git_hash,
    ):
        """
        Add a new rtp_process_record row.

        Parameters
        ----------
        time : astropy Time object
            Time of event.
        obsid : long
            Observation obsid (Foreign key into observation).
        pipeline_list : str
            Concatentated list of RTP tasks.
        rtp_git_version : str
            RTP git version.
        rtp_git_hash : str
            RTP git hash.
        hera_qm_git_version : str
            hera_qm git version.
        hera_qm_git_hash : str
            hera_qm git hash.
        hera_cal_git_version : str
            hera_cal git version.
        hera_cal_git_hash : str
            hera_cal git hash.
        pyuvdata_git_version : str
            pyuvdata git version.
        pyuvdata_git_hash : str
            pyuvdata git hash.

        """
        self.add(
            rtp.RTPProcessRecord.create(
                time,
                obsid,
                pipeline_list,
                rtp_git_version,
                rtp_git_hash,
                hera_qm_git_version,
                hera_qm_git_hash,
                hera_cal_git_version,
                hera_cal_git_hash,
                pyuvdata_git_version,
                pyuvdata_git_hash,
            )
        )

    def get_rtp_process_record(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        obsid=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get rtp_process_record record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        obsid : long
            obsid to get records for. If none, all obsid will be included.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of RTPProcessRecord objects

        """
        return self._time_filter(
            rtp.RTPProcessRecord,
            "time",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            filter_column="obsid",
            filter_value=obsid,
            write_to_file=write_to_file,
            filename=filename,
        )

    def add_rtp_task_jobid(self, obsid, task_name, start_time, job_id):
        """
        Add a new rtp_task_jobid row.

        Parameters
        ----------
        obsid : long
            Observation obsid, Foreign key into observation.
        task_name : str
            Name of the task (e.g., OMNICAL).
        start_time : astropy Time object
            GPS time of job start.
        job_id : int
            Job ID of the task.

        """
        self.add(rtp.RTPTaskJobID.create(obsid, task_name, start_time, job_id))

    def get_rtp_task_jobid(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        obsid=None,
        task_name=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get rtp_task_jobid record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        If either or both of obsid & task_name are set, then all records that match
        those are returned unless most_recent or starttime is set.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime,
            obsid and task_name are all None. If both most_recent and starttime are set,
            get the most recent record before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for. Ignored if both obsid and task_name are set.
        stoptime : astropy Time object
            last time to get records for, only used if starttime is used.
            If none, only the first record after starttime will be returned.
        obsid : long
            obsid to get records for. If none, all obsids will be included.
        task_name : str
            task_name to get records for. If none, all tasks will be included.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of RTPTaskJobID objects

        Raises
        ------
        ValueError
            If `most_recent` is False and all of obsid, task_name, and starttime are None.

        """
        if obsid is None and task_name is None and starttime is None:
            if most_recent is None:
                most_recent = True
            elif most_recent is False:
                raise ValueError(
                    "If most_recent is set to False, at least one of obsid, task_name "
                    "or starttime must be specified."
                )

        if most_recent is True or starttime is not None:
            return self._time_filter(
                rtp.RTPTaskJobID,
                "start_time",
                most_recent=most_recent,
                starttime=starttime,
                stoptime=stoptime,
                filter_column=["obsid", "task_name"],
                filter_value=[obsid, task_name],
                write_to_file=write_to_file,
                filename=filename,
            )

        query = self.query(rtp.RTPTaskJobID)
        if obsid is not None:
            query = query.filter(rtp.RTPTaskJobID.obsid == obsid)
        if task_name is not None:
            query = query.filter(rtp.RTPTaskJobID.task_name == task_name)

        if write_to_file:
            self._write_query_to_file(query, rtp.RTPTaskJobID, filename=filename)

        else:
            return query.all()

    def add_rtp_task_resource_record(
        self,
        obsid,
        task_name,
        start_time,
        stop_time,
        max_memory=None,
        avg_cpu_load=None,
    ):
        """
        Add a new rtp_task_resource_record row.

        Parameters
        ----------
        obsid : long
            Observation obsid, Foreign key into observation.
        task_name : str
            Name of the task (e.g., OMNICAL).
        start_time : astropy Time object
            GPS time of task start.
        stop_time : astropy Time object
            Time of task end.
        max_memory : float
            Maximum amount of memory used by the task, in MB.
        avg_cpu_load : float
            Average number of CPUs used by task.

        """
        self.add(
            rtp.RTPTaskResourceRecord.create(
                obsid, task_name, start_time, stop_time, max_memory, avg_cpu_load
            )
        )

    def get_rtp_task_resource_record(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        obsid=None,
        task_name=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get rtp_task_resource_record from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        If either or both of obsid & task_name are set, then all records that match
        those are returned unless most_recent or starttime is set.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime,
            obsid and task_name are all None. If both most_recent and starttime are set,
            get the most recent record before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for. Ignored if both obsid and task_name are set.
        stoptime : astropy Time object
            last time to get records for, only used if starttime is used.
            If none, only the first record after starttime will be returned.
        obsid : long
            obsid to get records for. If none, all obsids will be included.
        task_name : str
            task_name to get records for. If none, all tasks will be included.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of RTPTaskResourceRecord objects

        Raises
        ------
        ValueError
            If `most_recent` is False and all of obsid, task_name, and starttime are None.

        """
        if obsid is None and task_name is None and starttime is None:
            if most_recent is None:
                most_recent = True
            elif most_recent is False:
                raise ValueError(
                    "If most_recent is set to False, at least one of obsid, task_name "
                    "or starttime must be specified."
                )

        if most_recent is True or starttime is not None:
            return self._time_filter(
                rtp.RTPTaskResourceRecord,
                "start_time",
                most_recent=most_recent,
                starttime=starttime,
                stoptime=stoptime,
                filter_column=["obsid", "task_name"],
                filter_value=[obsid, task_name],
                write_to_file=write_to_file,
                filename=filename,
            )

        query = self.query(rtp.RTPTaskResourceRecord)
        if obsid is not None:
            query = query.filter(rtp.RTPTaskResourceRecord.obsid == obsid)
        if task_name is not None:
            query = query.filter(rtp.RTPTaskResourceRecord.task_name == task_name)

        if write_to_file:
            self._write_query_to_file(
                query, rtp.RTPTaskResourceRecord, filename=filename
            )

        else:
            return query.all()

    def add_rtp_task_multiple_track(self, obsid_start, task_name, obsid):
        """
        Add a new rtp_task_multiple_track row.

        This table tracks which obsids are included in an rtp task that includes
        multiple obsids. This is a many-to-one mapping table with a row per obsid that
        is included in the task.

        Parameters
        ----------
        obsid_start : BigInteger Column
            Starting obsid for the set of obsids included in the task. Used along with the
            task_name as the unique identifier in the `rtp_task_resource_record_multiple` table.
            Part of primary_key. Foreign key into Observation table.
        task_name : String Column
            Name of task in pipeline (e.g., OMNICAL). Part of primary_key.
        obsid : BigInteger Column
            Start time of the job in floor(gps_seconds). Part of primary_key. Foreign key into
            Observation table.

        """
        self.add(rtp.RTPTaskMultipleTrack.create(obsid_start, task_name, obsid))

    def get_rtp_task_multiple_track(
        self,
        obsid_start=None,
        task_name=None,
        obsid=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get rtp_task_multiple_track record(s) from the M&C database.

        Parameters
        ----------
        obsid_start : long
            Starting obsids for tasks with multiple obsids to get records for.
            If none, all starting obsids will be included.
        task_name : str
            task_name to get records for. If none, all tasks will be included.
        obsid : long
            obsid to get records for. If none, all obsids will be included.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of RTPTaskMultipleTrack objects

        """
        query = self.query(rtp.RTPTaskMultipleTrack)
        if obsid_start is not None:
            query = query.filter(rtp.RTPTaskMultipleTrack.obsid_start == obsid_start)
        if task_name is not None:
            query = query.filter(rtp.RTPTaskMultipleTrack.task_name == task_name)
        if obsid is not None:
            query = query.filter(rtp.RTPTaskMultipleTrack.obsid == obsid)

        if write_to_file:
            self._write_query_to_file(
                query, rtp.RTPTaskMultipleTrack, filename=filename
            )

        else:
            return query.all()

    def add_rtp_task_multiple_jobid(self, obsid_start, task_name, start_time, job_id):
        """
        Add a new rtp_task_jobid row.

        Parameters
        ----------
        obsid_start : long
            Starting obsid for the set of obsids included in the task.
            (Foreign key into Observation).
        task_name : str
            Name of the task (e.g., OMNICAL).
        start_time : astropy Time object
            GPS time of job start.
        job_id : int
            Job ID of the task.

        """
        self.add(
            rtp.RTPTaskMultipleJobID.create(obsid_start, task_name, start_time, job_id)
        )

    def get_rtp_task_multiple_jobid(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        obsid_start=None,
        task_name=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get rtp_task_multiple_jobid record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        If either or both of obsid & task_name are set, then all records that match
        those are returned unless most_recent or starttime is set.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime,
            obsid and task_name are all None. If both most_recent and starttime are set,
            get the most recent record before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for. Ignored if both obsid and task_name are set.
        stoptime : astropy Time object
            last time to get records for, only used if starttime is used.
            If none, only the first record after starttime will be returned.
        obsid_start : long
            Starting obsid for the set of obsids included in the task to get records for.
            If none, all obsids will be included.
        task_name : str
            task_name to get records for. If none, all tasks will be included.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of RTPTaskMultipleJobID objects

        Raises
        ------
        ValueError
            If `most_recent` is False and all of obsid_start, task_name, and starttime are None.

        """
        if obsid_start is None and task_name is None and starttime is None:
            if most_recent is None:
                most_recent = True
            elif most_recent is False:
                raise ValueError(
                    "If most_recent is set to False, at least one of obsid_start, task_name "
                    "or starttime must be specified."
                )

        if most_recent is True or starttime is not None:
            return self._time_filter(
                rtp.RTPTaskMultipleJobID,
                "start_time",
                most_recent=most_recent,
                starttime=starttime,
                stoptime=stoptime,
                filter_column=["obsid_start", "task_name"],
                filter_value=[obsid_start, task_name],
                write_to_file=write_to_file,
                filename=filename,
            )

        query = self.query(rtp.RTPTaskMultipleJobID)
        if task_name is not None:
            query = query.filter(rtp.RTPTaskMultipleJobID.task_name == task_name)
        if obsid_start is not None:
            query = query.filter(rtp.RTPTaskMultipleJobID.obsid_start == obsid_start)

        if write_to_file:
            self._write_query_to_file(
                query, rtp.RTPTaskMultipleJobID, filename=filename
            )

        else:
            return query.all()

    def add_rtp_task_multiple_resource_record(
        self,
        obsid_start,
        task_name,
        start_time,
        stop_time,
        max_memory=None,
        avg_cpu_load=None,
    ):
        """
        Add a new rtp_task_multiple_resource_record row.

        Parameters
        ----------
        obsid_start : long
            Starting obsid for the set of obsids included in the task, Foreign key into
            observation table
        task_name : str
            Name of the task (e.g., OMNICAL).
        start_time : astropy Time object
            GPS time of task start.
        stop_time : astropy Time object
            Time of task end.
        max_memory : float
            Maximum amount of memory used by the task, in MB.
        avg_cpu_load : float
            Average number of CPUs used by task.

        """
        self.add(
            rtp.RTPTaskMultipleResourceRecord.create(
                obsid_start, task_name, start_time, stop_time, max_memory, avg_cpu_load
            )
        )

    def get_rtp_task_multiple_resource_record(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        obsid_start=None,
        task_name=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get rtp_task_multiple_resource_record from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        If either or both of obsid & task_name are set, then all records that match
        those are returned unless most_recent or starttime is set.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime,
            obsid and task_name are all None. If both most_recent and starttime are set,
            get the most recent record before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for. Ignored if both obsid and task_name are set.
        stoptime : astropy Time object
            last time to get records for, only used if starttime is used.
            If none, only the first record after starttime will be returned.
        obsid_start : long
            Starting obsid for the set of obsids included in the task to get records for.
            If none, all obsids will be included.
        task_name : str
            task_name to get records for. If none, all tasks will be included.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of RTPTaskMultipleResourceRecord objects

        Raises
        ------
        ValueError
            If `most_recent` is False and all of obsid_start, task_name, and starttime are None.

        """
        if obsid_start is None and task_name is None and starttime is None:
            if most_recent is None:
                most_recent = True
            elif most_recent is False:
                raise ValueError(
                    "If most_recent is set to False, at least one of obsid_start, task_name "
                    "or starttime must be specified."
                )

        if most_recent is True or starttime is not None:
            return self._time_filter(
                rtp.RTPTaskMultipleResourceRecord,
                "start_time",
                most_recent=most_recent,
                starttime=starttime,
                stoptime=stoptime,
                filter_column=["obsid_start", "task_name"],
                filter_value=[obsid_start, task_name],
                write_to_file=write_to_file,
                filename=filename,
            )

        query = self.query(rtp.RTPTaskMultipleResourceRecord)
        if obsid_start is not None:
            query = query.filter(
                rtp.RTPTaskMultipleResourceRecord.obsid_start == obsid_start
            )
        if task_name is not None:
            query = query.filter(
                rtp.RTPTaskMultipleResourceRecord.task_name == task_name
            )

        if write_to_file:
            self._write_query_to_file(
                query, rtp.RTPTaskMultipleResourceRecord, filename=filename
            )

        else:
            return query.all()

    def add_rtp_launch_record(
        self,
        obsid,
        jd,
        obs_tag,
        filename,
        prefix,
        submitted_time=None,
        rtp_attempts=0,
    ):
        """
        Add new rtp_launch_record entry to the M&C database.

        Parameters
        ----------
        obsid : long
            The obsid to add a record for.
        jd : int
            The integer Julian Date of the obsid.
        obs_tag : str
            The observation tag of the data.
        filename : str
            The filename of the corresponding raw data.
        prefix : str
            The path to the directory where the data file is stored.
        submitted_time : astropy Time, optional
            If not None, an astropy Time object corresponding to job submission
            time.
        rtp_attempts : int, optional
            The number of times the job has been run by RTP.

        Returns
        -------
        None
        """
        self.add(
            rtp.RTPLaunchRecord.create(
                obsid, jd, obs_tag, filename, prefix, submitted_time, rtp_attempts
            )
        )
        return

    def get_rtp_launch_record(self, obsid):
        """
        Fetch rtp_launch_record entries for a given obsid.

        Parameters
        ----------
        obsid : long
            The obsid to fetch a record for.

        Returns
        -------
        list of RTPLaunchRecord objects
        """
        query = self.query(rtp.RTPLaunchRecord).filter(
            rtp.RTPLaunchRecord.obsid == obsid
        )
        return query.all()

    def get_rtp_launch_record_by_time(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Fetch rtp_launch_record entries based on their submitted_time.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime,
            obsid and task_name are all None. If both most_recent and starttime are set,
            get the most recent record before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for. Ignored if both obsid and task_name are set.
        stoptime : astropy Time object
            last time to get records for, only used if starttime is used.
            If none, only the first record after starttime will be returned.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of RTPLaunchRecord objects
        """
        return self._time_filter(
            rtp.RTPLaunchRecord,
            "submitted_time",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            write_to_file=write_to_file,
            filename=filename,
        )

    def get_rtp_launch_record_by_jd(self, jd):
        """
        Fetch rtp_launch_record entries based on their jd.

        Parameters
        ----------
        jd : int
            The integer JD of the corresponding records.

        Returns
        -------
        list of RTPLaunchRecord objects
        """
        query = self.query(rtp.RTPLaunchRecord).filter(rtp.RTPLaunchRecord.jd == jd)
        return query.all()

    def get_rtp_launch_record_by_rtp_attempts(self, rtp_attempts):
        """
        Fetch rtp_launch_record entries based on their number of RTP attempts.

        Parameters
        ----------
        rtp_attempts : int
            The number of times a file has been submitted to RTP.

        Returns
        -------
        list of RTPLaunchRecord objects
        """
        query = self.query(rtp.RTPLaunchRecord).filter(
            rtp.RTPLaunchRecord.rtp_attempts == rtp_attempts
        )
        return query.all()

    def get_rtp_launch_record_by_obs_tag(self, obs_tag):
        """
        Fetch rtp_launch_record entries based on their observation tag.

        Parameters
        ----------
        obs_tag : str
            The observation tag to search for.

        Returns
        -------
        list of RTPLaunchRecord objects
        """
        query = self.query(rtp.RTPLaunchRecord).filter(
            rtp.RTPLaunchRecord.obs_tag == obs_tag
        )
        return query.all()

    def update_rtp_launch_record(self, obsid, submitted_time):
        """
        Update an rtp_launch_record entry in the M&C database.

        This method should be called to update an existing record with the
        latest start time, and to increment the counter for the number of times
        a job has been launched.

        Parameters
        ----------
        obsid : long
            The obsid to update a record for.
        submitted_time : astropy Time object
            Astropy time object for the timestamp of job submission.

        Returns
        -------
        None

        Raises
        ------
        ValueError:
            This is raised if submitted_time is not an astropy Time object.
        RuntimeError:
            This is raised if the obsid does not match exactly one record.
        """
        # check type of input data
        if not isinstance(submitted_time, Time):
            raise ValueError("submitted_time must be an astropy Time object")
        submitted_time = int(floor(submitted_time.gps))
        # query the table for the existing row
        query = self.query(rtp.RTPLaunchRecord).filter(
            rtp.RTPLaunchRecord.obsid == obsid
        )
        result = query.all()
        if len(result) != 1:
            raise RuntimeError(f"RTP launch record does not exist for obsid {obsid}")
        result = result[0]
        # get the current number of rtp_attempts and increment
        rtp_attempts = result.rtp_attempts
        rtp_attempts += 1
        # update result
        result.rtp_attempts = rtp_attempts
        result.submitted_time = submitted_time
        self.commit()
        return

    def add_weather_data(self, time, variable, value):
        """
        Add new weather data to the M&C database.

        Parameters
        ----------
        time : astropy Time object
            Astropy time object based on a timestamp from the katportal sensor.
        variable : str
            Must be a key in weather.weather_sensor_dict
        value : float
            Value from the sensor associated with the variable

        """
        self.add(WeatherData.create(time, variable, value))

    def add_weather_data_from_sensors(self, starttime, stoptime, variables=None):
        """
        Add weather data for a given variable and timespan from KAT sensors.

        This function connects to the meerkat db and grabs the latest data
        using the "create_from_sensors" function.

        Parameters
        ----------
        starttime : astropy Time object
            Time to start getting history.
        stoptime : astropy Time object
            Time to stop getting history.
        variable : str
            Variable to get history for. Must be a key in
            weather.weather_sensor_dict, defaults to all keys in
            weather.weather_sensor_dict

        """
        if variables is not None:
            if isinstance(variables, (list, tuple)):
                for var in variables:
                    if var not in weather_sensor_dict.keys():
                        raise ValueError(
                            "variables must be a key in weather_sensor_dict."
                        )
            else:
                if variables not in weather_sensor_dict.keys():
                    raise ValueError("variables must be a key in weather_sensor_dict.")

        weather_data_list = create_from_sensors(
            starttime, stoptime, variables=variables
        )
        for obj in weather_data_list:
            self.add(obj)

    def get_weather_data(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        variable=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get weather_data record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        variable : str
            Name of variable to get records for, must be a key in
            weather.weather_sensor_dict. If none, all variables will be
            included.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        if write_to_file is False: list of WeatherData objects

        """
        if variable is not None:
            if variable not in weather_sensor_dict.keys():
                raise ValueError("variable must be a key in weather_sensor_dict.")

        return self._time_filter(
            WeatherData,
            "time",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            filter_column="variable",
            filter_value=variable,
            write_to_file=write_to_file,
            filename=filename,
        )

    def add_node_sensor_readings(
        self,
        time,
        nodeID,
        top_sensor_temp,
        middle_sensor_temp,
        bottom_sensor_temp,
        humidity_sensor_temp,
        humidity,
    ):
        """
        Add new node sensor data to the M&C database.

        Parameters
        ----------
        time : astropy Time object
            Astropy time object based on a timestamp reported by node.
        nodeID : int
            Node number (within 1 to 30).
        top_sensor_temp : float
            Temperature of top sensor reported by node in Celsius.
        middle_sensor_temp : float
            Temperature of middle sensor reported by node in Celsius.
        bottom_sensor_temp : float
            Temperature of bottom sensor reported by node in Celsius.
        humidity_sensor_temp : float
            Temperature of the humidity sensor reported by node in Celsius.
        humidity : float
            Percent humidity measurement reported by node.

        """
        self.add(
            node.NodeSensor.create(
                time,
                nodeID,
                top_sensor_temp,
                middle_sensor_temp,
                bottom_sensor_temp,
                humidity_sensor_temp,
                humidity,
            )
        )

    def add_node_sensor_readings_from_node_control(
        self, nodeServerAddress=node.defaultServerAddress
    ):
        """
        Get and add node sensor information using a nodeControl object.

        This function connects to the node and gets the latest data using the
        `create_sensor_readings` function.

        If the current database is PostgreSQL, this function will use a
        special insertion method that will ignore records that are redundant
        with ones already in the database. This makes it convenient to sample
        the node sensor data densely on qmaster.

        Parameters
        ----------
        nodeServerAddress : str
            Address of server where the node redis database can be accessed. Defaults to
            node.defaultServerAddress

        """
        node_sensor_list = node.create_sensor_readings(
            nodeServerAddress=nodeServerAddress
        )

        self._insert_ignoring_duplicates(node.NodeSensor, node_sensor_list)

    def get_node_sensor_readings(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        nodeID=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get node_sensor record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.


        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        nodeID : int
            node number (integer running from 0 to 30)
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        if write_to_file is False: list of NodeSensor objects

        """
        return self._time_filter(
            node.NodeSensor,
            "time",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            filter_column="node",
            filter_value=nodeID,
            write_to_file=write_to_file,
            filename=filename,
        )

    def add_node_power_status(
        self,
        time,
        nodeID,
        snap_relay_powered,
        snap0_powered,
        snap1_powered,
        snap2_powered,
        snap3_powered,
        fem_powered,
        pam_powered,
    ):
        """
        Add new node power status data to the M&C database.

        Parameters
        ----------
        time : astropy Time object
            Astropy time object based on a timestamp reported by node.
        nodeID : int
            Node number (integer running from 0 to 30).
        snap_relay_powered : bool
            Power status of the snap relay, True=powered.
        snap0_powered : bool
            Power status of the SNAP 0 board, True=powered.
        snap1_powered : bool
            Power status of the SNAP 1 board, True=powered.
        snap2_powered : bool
            Power status of the SNAP 2 board, True=powered.
        snap3_powered : bool
            Power status of the SNAP 3 board, True=powered.
        fem_powered : bool
            Power status of the FEM, True=powered.
        pam_powered : bool
            Power status of the PAM, True=powered.

        """
        self.add(
            node.NodePowerStatus.create(
                time,
                nodeID,
                snap_relay_powered,
                snap0_powered,
                snap1_powered,
                snap2_powered,
                snap3_powered,
                fem_powered,
                pam_powered,
            )
        )

    def add_node_power_status_from_node_control(
        self, nodeServerAddress=node.defaultServerAddress
    ):
        """
        Get and add node power status information using a nodeControl object.

        This function connects to the node and gets the latest data using the
        `create_power_status` function.

        If the current database is PostgreSQL, this function will use a
        special insertion method that will ignore records that are redundant
        with ones already in the database. This makes it convenient to sample
        the node power status data densely on qmaster.

        Parameters
        ----------
        nodeServerAddress : str
            Address of server where the node redis database can be accessed. Defaults to
            node.defaultServerAddress

        """
        node_power_list = node.create_power_status(nodeServerAddress=nodeServerAddress)

        self._insert_ignoring_duplicates(node.NodePowerStatus, node_power_list)

    def get_node_power_status(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        nodeID=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get node power status record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        nodeID : int
            node number (integer running from 0 to 30)
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of NodePowerStatus objects

        """
        return self._time_filter(
            node.NodePowerStatus,
            "time",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            filter_column="node",
            filter_value=nodeID,
            write_to_file=write_to_file,
            filename=filename,
        )

    def add_node_power_command(self, time, nodeID, part, command):
        """
        Add new node sensor data to the M&C database.

        Parameters
        ----------
        time : astropy Time
            Time when added to database.
        nodeID : int
            Node number. Part of the primary key.
        part : str
            Part to be powered on/off. Part of the primary key.
        command : str
            Command, one of 'on' or 'off'.
        """
        self.add(node.NodePowerCommand.create(time, nodeID, part, command))

    def add_node_power_command_from_node_control(
        self, nodeServerAddress=node.defaultServerAddress
    ):
        """
        Get and add node power command information using a node_control object.

        This function connects to the node and gets the latest data using the
        `create_power_command_list` function which gets value from redis.

        If the current database is PostgreSQL, this function will use a
        special insertion method that will ignore records that are redundant
        with ones already in the database. This makes it convenient to sample
        the node power command data densely on qmaster.

        Parameters
        ----------
        nodeServerAddress : str
            Address of server where the node redis database can be accessed. Defaults to
            node.defaultServerAddress

        """
        node_power_list = node.create_power_command_list(
            nodeServerAddress=nodeServerAddress
        )

        self._insert_ignoring_duplicates(node.NodePowerCommand, node_power_list)

    def get_node_power_command(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        nodeID=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get node power command record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        nodeID : int
            node number (integer running from 0 to 30)
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of NodePowerCommand objects

        """
        return self._time_filter(
            node.NodePowerCommand,
            "time",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            filter_column="node",
            filter_value=nodeID,
            write_to_file=write_to_file,
            filename=filename,
        )

    def add_node_white_rabbit_status(self, col_dict):
        """
        Add new node white rabbit status data to the M&C database.

        Parameters
        ----------
        col_dict : dict
            dictionary that must contain the following entries:

            node_time : astropy Time object
                Astropy time object based on a timestamp reported by node.
            node : int
                Node number (within 1 to 30).
            board_info_str : str
                A raw string representing the WR-LEN's response to the `ver` command.
                Relevant parts of this string are individually unpacked in other entries.
            aliases : str
                Hostname aliases of this node's WR-LEN (comma separated if more than one).
            ip : str
                IP address of this node's WR-LEN
            mode : str
                WR-LEN operating mode (eg. "WRC_SLAVE_WR0")
            serial : str
                Canonical HERA hostname (~= serial number) of this node's WR-LEN
            temperature : float
                WR-LEN temperature in degrees C
            build_date : astropy Time object
                Build date of WR-LEN software in floored GPS seconds.
            gw_date : astropy Time object
                WR-LEN gateware build date in floored GPS seconds.
            gw_version : str
                WR-LEN gateware version number
            gw_id : str
                WR-LEN gateware ID number
            build_hash : str
                WR-LEN build git hash
            manufacture_tag : str
                Custom manufacturer tag
            manufacture_device : str
                Manufacturer device name designation
            manufacture_date : astropy Time object
                Manufacturer invoice(?) date
            manufacture_partnum : str
                Manufacturer part number
            manufacture_serial : str
                Manufacturer serial number
            manufacture_vendor : str
                Vendor name
            port0_ad : int
                ???
            port0_link_asymmetry_ps : int
                Port 0 total link asymmetry in picosec
            port0_manual_phase_ps : int
                ??? Port 0 manual phase adjustment in picosec
            port0_clock_offset_ps : int
                Port 0 Clock offset in picosec
            port0_cable_rt_delay_ps : int
                Port 0 Cable round-trip delay in picosec
            port0_master_slave_delay_ps : int
                Port 0 Master-Slave delay in in picosec
            port0_master_rx_phy_delay_ps : int
                Port 0 Master RX PHY delay in picosec
            port0_slave_rx_phy_delay_ps : int
                Port 0 Slave RX PHY delay in picosec
            port0_master_tx_phy_delay_ps : int
                Port 0 Master TX PHY delay in picosec
            port0_slave_tx_phy_delay_ps : int
                Port 0 Slave TX PHY delay in picosec
            port0_hd : int
                ???
            port0_link : bool
                Port 0 link up state
            port0_lock : bool
                Port 0 timing lock state
            port0_md : int
                ???
            port0_rt_time_ps : int
                Port 0 round-trip time in picosec
            port0_nsec : int
                ???
            port0_packets_received : int
                Port 0 number of packets received
            port0_phase_setpoint_ps : int
                Port 0 phase setpoint in picosec
            port0_servo_state : str
                Port 0 servo state
            port0_sv : int
                ???
            port0_sync_source : str
                Port 0 source of synchronization (either 'wr0' or 'wr1')
            port0_packets_sent : int
                Port 0 number of packets transmitted
            port0_update_counter : int
                Port 0 update counter
            port0_time : astropy Time object
                Astropy Time object based on Port 0 current TAI time in seconds from UNIX epoch.
            port1_ad : int
                ???
            port1_link_asymmetry_ps : int
                Port 1 total link asymmetry in picosec
            port1_manual_phase_ps : int
                ??? Port 1 manual phase adjustment in picosec
            port1_clock_offset_ps : int
                Port 1 Clock offset in picosec
            port1_cable_rt_delay_ps : int
                Port 1 Cable round-trip delay in picosec
            port1_master_slave_delay_ps : int
                Port 1 Master-Slave delay in in picosec
            port1_master_rx_phy_delay_ps : int
                Port 1 Master RX PHY delay in picosec
            port1_slave_rx_phy_delay_ps : int
                Port 1 Slave RX PHY delay in picosec
            port1_master_tx_phy_delay_ps : int
                Port 1 Master TX PHY delay in picosec
            port1_slave_tx_phy_delay_ps : int
                Port 1 Slave TX PHY delay in picosec
            port1_hd : int
                ???
            port1_link : bool
                Port 1 link up state
            port1_lock : bool
                Port 1 timing lock state
            port1_md : int
                ???
            port1_rt_time_ps : int
                Port 1 round-trip time in picosec
            port1_nsec : int
                ???
            port1_packets_received : int
                Port 1 number of packets received
            port1_phase_setpoint_ps : int
                Port 1 phase setpoint in picosec
            port1_servo_state : str
                Port 1 servo state
            port1_sv : int
                ???
            port1_sync_source : str
                Port 1 source of synchronization (either 'wr0' or 'wr1')
            port1_packets_sent : int
                Port 1 number of packets transmitted
            port1_update_counter : int
                Port 1 update counter
            port1_time : astropy Time object
                Astropy Time object based on Port 1 current TAI time in seconds from UNIX epoch.

        """
        self.add(node.NodeWhiteRabbitStatus.create(col_dict))

    def add_node_white_rabbit_status_from_node_control(
        self, nodeServerAddress=node.defaultServerAddress
    ):
        """
        Get and add node white rabbit information using a nodeControl object.

        This function connects to the node and gets the latest data using the
        `create_wr_status` function.

        If the current database is PostgreSQL, this function will use a
        special insertion method that will ignore records that are redundant
        with ones already in the database. This makes it convenient to sample
        the node white rabbit data densely on qmaster.

        Parameters
        ----------
        nodeServerAddress : str
            Address of server where the node redis database can be accessed. Defaults to
            node.defaultServerAddress

        """
        node_wr_status_list = node.create_wr_status(nodeServerAddress=nodeServerAddress)

        self._insert_ignoring_duplicates(
            node.NodeWhiteRabbitStatus, node_wr_status_list
        )

    def get_node_white_rabbit_status(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        nodeID=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get node_white_rabbit_status record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        nodeID : int
            node number (integer running from 0 to 30)
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        if write_to_file is False: list of NodeWhiteRabbitStatus objects

        """
        return self._time_filter(
            node.NodeWhiteRabbitStatus,
            "node_time",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            filter_column="node",
            filter_value=nodeID,
            write_to_file=write_to_file,
            filename=filename,
        )

    def add_array_signal_source(self, time, source):
        """
        Add an array signal source to the M&C database.

        Parameters
        ----------
        time : astropy Time object
            Astropy time object based on a timestamp reported by the correlator.
        source : str
            One of "antenna", "load", "noise", "digital_noise_same",
            "digital_noise_different" (listed in corr.signal_source_list).

        """
        self.add(corr.ArraySignalSource.create(time, source))

    def add_array_signal_source_from_redis(
        self,
        testing=False,
        redishost=corr.DEFAULT_REDIS_ADDRESS,
    ):
        """
        Get and add the current array signal source from redis.

        Uses the `correlator._get_array_source_from_redis` function

        If the current database is PostgreSQL, this function will use a
        special insertion method that will ignore records that are redundant
        with ones already in the database. This makes it convenient to sample
        the array signal source data densely on qmaster.

        Parameters
        ----------
        testing : bool
            If true, return the ArraySignalSource object and don't add it to the database.
        redishost : str
            redis address to use. Defaults to correlator.DEFAULT_REDIS_ADDRESS.

        Returns
        -------
        ArraySignalSource
            If testing is True, returns the ArraySignalSource object rather than adding
            it to the database.

        """
        time, source = corr._get_array_source_from_redis(redishost=redishost)

        signal_source_obj = corr.ArraySignalSource.create(time, source)

        if testing:
            return signal_source_obj

        self._insert_ignoring_duplicates(corr.ArraySignalSource, [signal_source_obj])

    def get_array_signal_source(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        source=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get array_signal_source record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        source : str
            One of "antenna", "load", "noise", "digital_noise_same",
            "digital_noise_different" (listed in corr.signal_source_list).
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        if write_to_file is False: list of ArraySignalSource objects

        """
        return self._time_filter(
            corr.ArraySignalSource,
            "time",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            filter_column="source",
            filter_value=source,
            write_to_file=write_to_file,
            filename=filename,
        )

    def add_correlator_component_event_time(self, component, event, time):
        """
        Add new correlator component event time to the M&C database.

        Parameters
        ----------
        component : str
            Correlator component, one of "f_engine", "x_engine", "catcher"
            (key in corr.corr_component_events).
        event : str
            Correlator component event, one of "sync" (f-engine),
            "integration_start" (x-engine), "start", "stop", "stop_timeout" (catcher).
            Component and event must be paired in corr.corr_component_events.
        time : astropy Time object
            Astropy time object based on a timestamp reported by the correlator.


        """
        self.add(corr.CorrelatorComponentEventTime.create(component, event, time))

    def get_correlator_component_event_time(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        component=None,
        event=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get correlator_component_event_time record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        component : str
            Correlator component, one of "f_engine", "x_engine", "catcher"
            (key in corr_component_events).
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        if write_to_file is False: list of CorrelatorComponentEventTime objects

        """
        return self._time_filter(
            corr.CorrelatorComponentEventTime,
            "time",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            filter_column=["component", "event"],
            filter_value=[component, event],
            write_to_file=write_to_file,
            filename=filename,
        )

    def add_correlator_component_event_time_from_redis(
        self,
        redishost=corr.DEFAULT_REDIS_ADDRESS,
        taking_data_dict=None,
        testing=False,
    ):
        """
        Get and add correlator component event times from redis.

        Uses the `correlator._get_correlator_component_event_times_from_redis` function

        If the current database is PostgreSQL, this function will use a
        special insertion method that will ignore records that are redundant
        with ones already in the database. This makes it convenient to sample
        the correlator component event times densely on qmaster.

        Parameters
        ----------
        redishost : str
            redis address to use. Defaults to correlator.DEFAULT_REDIS_ADDRESS.
        testing : bool
            If true, return the CorrelatorComponentEventTime object and don't add it to
            the database.
        taking_data_dict: A dict spoofing the dict returned by the redis call
            `hgetall("corr:is_taking_data")` for testing purposes.
            Example: {b'state': b'True', b'time': b'1654884281'} or empty dict

        Returns
        -------
        list of CorrelatorComponentEventTime
            If testing is True, returns the list of CorrelatorComponentEventTime objects
            rather than adding them to the database.

        """
        component_event_dict = corr._get_correlator_component_event_times_from_redis(
            redishost=redishost,
            taking_data_dict=taking_data_dict,
        )

        comp_event_list = []
        catcher_event = None
        catcher_time = None
        for component, event_dict in component_event_dict.items():
            comp_event_list.append(
                corr.CorrelatorComponentEventTime.create(
                    component, event_dict["event"], event_dict["time"]
                )
            )
            if component == "catcher":
                catcher_event = event_dict["event"]
                catcher_time = event_dict["time"]

        # If the redis key times out (catcher_event is None) before it registers that
        # it stopped taking data, add a row with catcher stop_timeout with the most
        # recent time. If the key comes back as taking data with the old start time,
        # then remove the row that was added about it stopping (this should not happen,
        # but is not an interesting error case to raise up to the correlator team.)
        last_catcher_event = self.get_correlator_component_event_time(
            most_recent=True, component="catcher"
        )
        if len(last_catcher_event) > 0:
            if catcher_event is None:
                if last_catcher_event[0].event == "start":
                    # A timeout occurred before the catcher stopped "naturally"
                    # Add a record that the catcher has stopped (detected via a timeout)
                    comp_event_list.append(
                        corr.CorrelatorComponentEventTime.create(
                            "catcher", "stop_timeout", Time.now()
                        )
                    )
            elif (
                catcher_event == "start"
                and last_catcher_event[0].event == "stop_timeout"
                and catcher_time.gps < last_catcher_event[0].time
            ):
                # Uh oh. We are now getting a catcher start time that comes before the most
                # recent status and that status was caused by a redis key timeout.
                # Either this is the previous start time and the time out was a fluke or
                # This is a later start time than before and the timeout wasn't
                # detected as early as it occurred.
                # Get the most recent catcher start event to see which case we're in.
                # There is guaranteed to be a catcher start entry in the table because a
                # "stop_timeout" event is only recorded if there was a preceeding "start".
                last_catcher_start = self.get_correlator_component_event_time(
                    most_recent=True,
                    component="catcher",
                    event="start",
                )
                if catcher_time.gps == last_catcher_start[0].time:
                    # The timeout recorded before was a fluke, remove the record in the
                    # DB associated with it.
                    self.query(corr.CorrelatorComponentEventTime).filter(
                        corr.CorrelatorComponentEventTime.event == "stop_timeout"
                        and corr.CorrelatorComponentEventTime.time > catcher_time.gps
                    ).delete()
                elif catcher_time.gps > last_catcher_start[0].time:
                    # The timeout time should be moved earlier, to before the start
                    # we're now detecting. Set it to 1 second earlier.
                    self.query(corr.CorrelatorComponentEventTime).filter(
                        corr.CorrelatorComponentEventTime.event == "stop_timeout"
                        and corr.CorrelatorComponentEventTime.time > catcher_time.gps
                    ).update({"time": last_catcher_start[0].time - 1})

        if testing:
            return comp_event_list

        self._insert_ignoring_duplicates(
            corr.CorrelatorComponentEventTime, comp_event_list
        )

    def add_correlator_catcher_file(self, time, filename):
        """
        Add new correlator catcher file records to the M&C database.

        Parameters
        ----------
        time : astropy Time object
            Astropy time object based on a timestamp reported by the correlator.
        filename : str
            Name of the current file being written by the catcher. Can be null when the
            catcher first starts.

        """
        self.add(corr.CorrelatorCatcherFile.create(time, filename))

    def add_correlator_catcher_file_from_redis(
        self,
        testing=False,
        redishost=corr.DEFAULT_REDIS_ADDRESS,
    ):
        """
        Get the current catcher file from redis and add it to the database.

        Uses the `correlator._get_catcher_file_from_redis` function

        If the current database is PostgreSQL, this function will use a
        special insertion method that will ignore records that are redundant
        with ones already in the database. This makes it convenient to sample
        the array signal source data densely on qmaster.

        Parameters
        ----------
        testing : bool
            If true, return the CorrelatorCatcherFile object and don't add it to the
            database.
        redishost : str
            redis address to use. Defaults to correlator.DEFAULT_REDIS_ADDRESS.

        Returns
        -------
        CorrelatorCatcherFile
            If testing is True, returns the CorrelatorCatcherFile object rather than
            adding it to the database.

        """
        time, filename = corr._get_catcher_file_from_redis(redishost=redishost)

        catcher_file_obj = corr.CorrelatorCatcherFile.create(time, filename)

        if testing:
            return catcher_file_obj

        self._insert_ignoring_duplicates(corr.CorrelatorCatcherFile, [catcher_file_obj])

    def get_correlator_catcher_file(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get correlator_catcher_file record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        if write_to_file is False: list of CorrelatorCatcherFile objects

        """
        return self._time_filter(
            corr.CorrelatorCatcherFile,
            "time",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            write_to_file=write_to_file,
            filename=filename,
        )

    def add_correlator_file_queues(
        self, time, queue, length, oldest_entry, newest_entry
    ):
        """
        Add new correlator file queue records to the M&C database.

        Parameters
        ----------
        time : astropy Time object
            Astropy time object based on when the queue was queried.
        queue : str
            Name of queue, one of: "raw", "conversion_purgatory", "conversion_failed",
            "converted", "lib_upload_purgatory", "lib_upload_failed", "lib_uploaded".
        length : int
            Length of the queue.
        latest_entry : str
            File most recently added to the queue.

        """
        self.add(
            corr.CorrelatorFileQueues.create(
                time, queue, length, oldest_entry, newest_entry
            )
        )

    def add_correlator_file_queues_from_redis(
        self,
        testing=False,
        redishost=corr.DEFAULT_REDIS_ADDRESS,
    ):
        """
        Get the current file queue info from redis and add it to the database.

        Uses the `correlator._get_correlator_file_queues_from_redis` function

        Parameters
        ----------
        testing : bool
            If true, return the list of CorrelatorFileQueues objects and don't add them
            to the database.
        redishost : str
            redis address to use. Defaults to correlator.DEFAULT_REDIS_ADDRESS.

        Returns
        -------
        list of CorrelatorFileQueues objects
            If testing is True, returns the list of CorrelatorFileQueues objects rather
            than adding them to the database.

        """
        file_queue_list = corr._get_correlator_file_queues_from_redis(
            redishost=redishost
        )

        if testing:
            return file_queue_list

        self._insert_ignoring_duplicates(corr.CorrelatorFileQueues, file_queue_list)

    def get_correlator_file_queues(
        self,
        queue=None,
        most_recent=None,
        starttime=None,
        stoptime=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get correlator_file_queues record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        queue : str
            Name of queue, one of: "raw", "conversion_purgatory", "conversion_failed",
            "converted", "lib_upload_purgatory", "lib_upload_failed", "lib_uploaded".
            Default is to include all queue names.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        if write_to_file is False: list of CorrelatorFileQueues objects

        """
        return self._time_filter(
            corr.CorrelatorFileQueues,
            "time",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            filter_column="queue",
            filter_value=queue,
            write_to_file=write_to_file,
            filename=filename,
        )

    def get_correlator_file_eod(self, jd):
        """
        Get correlator file EOD status record(s) from the M&C database.

        Parameter
        ---------
        jd : int
            Julian day to get the EOD status for.

        Returns
        -------
        list
            CorrelatorFileEOD for the specified jd, or None if no rows exist for the jd.

        """
        query = self.query(corr.CorrelatorFileEOD).filter(
            corr.CorrelatorFileEOD.jd == jd
        )

        return query.all()

    def update_correlator_file_eod(self, time, jd, status):
        """
        Update the correlator_file_eod table.

        This only records the time associated with a status when it is first observed.
        If the jd and status already exist in the database, the database will not be
        updated, making it convenient to sample the eod information densely on qmaster.

        Parameters
        ----------
        time : astropy Time object
            Astropy time object based on when the correlator file end of day status was
            queried.
        jd : int
            Julian day that the status is for.
        status : int
            Status value, one of: 0 (meaning conversion is ongoing), 1 (meaning
            conversion is done, librarian uploading is ongoing), 2 (meaning librarian
            uploading is done), or -1 (meaning that RTP launch failed on that jd).

        """
        file_eod_status_columns = {
            0: "time_start",
            1: "time_converted",
            2: "time_uploaded",
            -1: "time_launch_failed",
        }
        if not isinstance(time, Time):
            raise ValueError("time must an astropy Time object")

        # Check to see if this jd and status is in the db already. If so, do nothing
        jd_result = self.get_correlator_file_eod(jd)
        if len(jd_result) == 0:
            # This jd isn't in the table. Add it with this status at this time
            eod_kwarg = {}
            for eod_status, name in file_eod_status_columns.items():
                if eod_status == status:
                    eod_kwarg[name] = int(time.gps)
                else:
                    eod_kwarg[name] = None

            self.add(corr.CorrelatorFileEOD(jd=jd, **eod_kwarg))
        else:
            existing_obj = jd_result[0]
            # This jd is in the table. Check to see if this status column has been set.
            status_column = file_eod_status_columns[status]
            existing_time = getattr(existing_obj, status_column)
            if existing_time is None:
                setattr(existing_obj, status_column, int(time.gps))

    def update_correlator_file_eod_from_redis(
        self,
        redishost=corr.DEFAULT_REDIS_ADDRESS,
    ):
        """
        Get the current file EOD info from redis and add it to the database.

        Uses the `correlator._get_correlator_file_eod_status_from_redis` function

        Parameters
        ----------
        redishost : str
            redis address to use. Defaults to correlator.DEFAULT_REDIS_ADDRESS.

        Returns
        -------
        list of CorrelatorFileEOD objects
            If testing is True, returns the list of CorrelatorFileEOD objects rather
            than adding them to the database.

        """
        jd_eod_dict = corr._get_correlator_file_eod_status_from_redis(
            redishost=redishost
        )

        time = Time.now()
        for jd, status in jd_eod_dict.items():
            self.update_correlator_file_eod(time, jd, status)

    def add_correlator_config_file(self, config_hash, config_file):
        """
        Add new correlator config file to the M&C database.

        Parameters
        ----------
        config_hash : str
            Unique hash of the config.
        config_file : str
            Name of the config file in the Librarian.

        """
        self.add(corr.CorrelatorConfigFile.create(config_hash, config_file))

    def get_correlator_config_file(
        self, config_hash=None, most_recent=None, starttime=None, stoptime=None
    ):
        """
        Get a correlator config file record from the M&C database.

        If a config_hash is provided, the time-related optional keywords are ignored.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        config_hash : str
            Unique hash for config file.
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        Returns
        -------
        list
            List of CorrelatorConfigFile objects.
        time_list : list of Astropy Time objects, optional
            List of start times when the config files were used, same length as the list
            of CorrelatorConfigFile objects. Only provided if `config_hash` is None.

        """
        if config_hash is not None:
            query = self.query(corr.CorrelatorConfigFile).filter(
                corr.CorrelatorConfigFile.config_hash == config_hash
            )

            return query.all()
        else:
            # get the config statuses to get hashes for the times of interest
            config_status_list = self.get_correlator_config_status(
                most_recent=most_recent, starttime=starttime, stoptime=stoptime
            )
            time_list = []
            config_file_obj_list = []
            for config_status in config_status_list:
                config_file_obj_list.extend(
                    self.get_correlator_config_file(config_status.config_hash)
                )
                time_list.append(Time(config_status.time, format="gps"))

            return config_file_obj_list, time_list

    def get_correlator_config_params(
        self,
        config_hash=None,
        parameter=None,
        most_recent=None,
        starttime=None,
        stoptime=None,
    ):
        """
        Get correlator config params record(s) from the M&C database.

        If a config_hash is provided, the time-related optional keywords are ignored.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        config_hash : str
            Unique MD5 hash of the config to get records for.
        parameter : str, optional
            Parameter to get record for. If None, get all parameters for this hash.
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        Returns
        -------
        list
            List of CorrelatorConfigParams objects.
        time_list : list of Astropy Time objects, optional
            List of start times when the config params were used, same length as the list
            of CorrelatorConfigParams objects. Only provided if `config_hash` is None.

        """
        if config_hash is not None:
            query = self.query(corr.CorrelatorConfigParams).filter(
                corr.CorrelatorConfigParams.config_hash == config_hash
            )

            if parameter is not None:
                query = query.filter(corr.CorrelatorConfigParams.parameter == parameter)

            return query.all()
        else:
            # get the config statuses to get hashes for the times of interest
            config_status_list = self.get_correlator_config_status(
                most_recent=most_recent, starttime=starttime, stoptime=stoptime
            )
            time_list = []
            config_params_obj_list = []
            for config_status in config_status_list:
                this_param_list = self.get_correlator_config_params(
                    config_hash=config_status.config_hash, parameter=parameter
                )
                config_params_obj_list.extend(this_param_list)
                time_list.extend(
                    [Time(config_status.time, format="gps")] * len(this_param_list)
                )

            return config_params_obj_list, time_list

    def get_snap_hostname_from_serial(self, serial_number, at_date="now"):
        """
        Get SNAP hostname from the SNAP serial number (also called hpn or part number).

        This method uses the PartRosetta table. If the hostname cannot be found there,
        it returns None.

        Parameters
        ----------
        serial_number : str
            SNAP serial number.
        at_date : 'now', Time or gps second
            Date at which to initialize.

        Returns
        -------
        str or None
            SNAP hostname if serial_number is found in the part_rosetta None otherwise.

        """
        active = ActiveData(session=self, at_date=at_date, float_format="gps")
        active.load_rosetta()
        if serial_number in active.rosetta.keys():
            return active.rosetta[serial_number].syspn
        else:
            return None

    def get_snap_serial_from_hostname(self, hostname, at_date):
        """
        Get SNAP serial number (also called hpn or part number) from the SNAP hostname.

        This method uses the PartRosetta table. If the hostname cannot
        be found there it returns None.

        Parameters
        ----------
        hostname : str
            SNAP hostname.
        at_date : 'now', Time or gps second
            Date at which to initialize.

        Returns
        -------
        str or None
            SNAP serial number (also called hpn or part number) if the hostname is found
            in the part_rosetta, None otherwise.

        """
        active = ActiveData(session=self, at_date=at_date, float_format="gps")
        active.load_rosetta()

        serial_number = None
        for hpn, part_rosetta in active.rosetta.items():
            if part_rosetta.syspn == hostname:
                serial_number = hpn
                break

        return serial_number

    def _get_node_snap_from_serial(self, snap_serial, session=None, at_date="now"):
        """
        Get SNAP connection information from SNAP serial number.

        Parameters
        ----------
        snap_serial : str
            SNAP serial number (also called hpn or part number).
        session : Session object
            Session to pass to cm_handling.Handling. Defaults to self.
        at_date : "now", Time or gps second
            Date at which to initialize.

        Returns
        -------
        nodeID: int
            Node number.
        snap_loc_num : int
            SNAP location number.

        """
        if session is None:
            session = self
        active = ActiveData(session=self, at_date=at_date, float_format="gps")
        active.load_parts()
        active.load_connections()
        rev_list = active.revs(snap_serial, exact_match=True)
        if len(rev_list) < 1:
            warnings.warn(
                f"No active connections returned for snap serial {snap_serial}. "
                "Setting node and snap location numbers to None"
            )
            return None, None
        if len(rev_list) > 1:
            warnings.warn(
                f"There is more that one active revision for snap serial {snap_serial}. "
                "Setting node and snap location numbers to None"
            )
            return None, None

        this_rev = rev_list[0].rev
        this_conn_key = cm_utils.make_part_key(snap_serial, this_rev)
        nodeID = int(
            active.connections["up"][this_conn_key]["RACK"].downstream_part[1:]
        )
        snap_loc_num = int(
            active.connections["up"][this_conn_key]["RACK"].downstream_input_port[3:]
        )

        return nodeID, snap_loc_num

    def _get_node_snap_from_snap_hostname(self, hostname, at_date):
        """
        Get SNAP connection information from SNAP hostname.

        Parameters
        ----------
        hostname : str
            SNAP hostname.
        at_date : 'now', Time or gps second
            Date at which to initialize.

        Returns
        -------
        nodeID: int
            Node number.
        snap_loc_num : int
            SNAP location number.

        """
        snap_hpn = self.get_snap_serial_from_hostname(hostname, at_date=at_date)
        if snap_hpn is not None:
            nodeID, snap_loc_num = self._get_node_snap_from_serial(
                snap_hpn, at_date=at_date
            )
        else:
            nodeID = None
            snap_loc_num = None

        return nodeID, snap_loc_num

    def _get_node_snap_lists_for_configs(self, config_obj_list, time_list=None):
        """
        Get SNAP connection information for lists of config objects.

        Parameters
        ----------
        config_obj_list : list
            list of instances of CorrelatorConfigActiveSNAP, CorrelatorConfigInputIndex
            or CorrelatorConfigPhaseSwitchIndex.
        time_list : list of astropy Time objects
            Times corresponding to objects in config_obj_list. Use now if None.

        Returns
        -------
        node_list: list of int
            List of node numbers.
        loc_num_list : list of int
            List of SNAP location numbers.

        """
        node_list = []
        loc_num_list = []
        for index, obj in enumerate(config_obj_list):
            if time_list is None:
                at_date = "now"
            else:
                at_date = time_list[index]
            node, loc_num = self._get_node_snap_from_snap_hostname(
                obj.hostname, at_date=at_date
            )
            node_list.append(node)
            loc_num_list.append(loc_num)

        return node_list, loc_num_list

    def get_correlator_config_active_snaps(
        self,
        config_hash=None,
        most_recent=None,
        starttime=None,
        stoptime=None,
        return_node_loc_num=False,
    ):
        """
        Get correlator config active SNAP records from the M&C database.

        If a config_hash is provided, the time-related optional keywords are ignored and
        if return_node_loc_num is True, the returned mappings are the ones currently in
        effect (regardless of when the config hash was last used).

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        config_hash : str
            Unique MD5 hash of the config to get records for.
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        return_node_loc_num : bool
            If True, return the node and SNAP location numbers for the active SNAPS.
            If a config_hash is provided, setting this to True will get the node and
            SNAP location numbers currently in effect (effectively time="now").

        Returns
        -------
        list
            List of CorrelatorConfigActiveSNAP objects.
        time_list : list of Astropy Time objects, optional
            List of start times when the config params were used, same length as the list
            of CorrelatorConfigActiveSNAP objects. Only provided if `config_hash` is None.
        node_list : list of int, optional
            List of nodes for each object in the list of CorrelatorConfigActiveSNAP objects.
        loc_num_list : list of int, optional
            List of SNAP location numbers for each object in the list of
            CorrelatorConfigActiveSNAP objects.

        """
        if config_hash is not None:
            query = self.query(corr.CorrelatorConfigActiveSNAP).filter(
                corr.CorrelatorConfigActiveSNAP.config_hash == config_hash
            )

            config_active_snap_list = query.all()
            retval = [config_active_snap_list]
            time_list = None
        else:
            # get the config statuses to get hashes for the times of interest
            config_status_list = self.get_correlator_config_status(
                most_recent=most_recent, starttime=starttime, stoptime=stoptime
            )
            time_list = []
            config_active_snap_list = []
            for config_status in config_status_list:
                this_active_snap_list = self.get_correlator_config_active_snaps(
                    config_hash=config_status.config_hash
                )
                config_active_snap_list.extend(this_active_snap_list)
                time_list.extend(
                    [Time(config_status.time, format="gps")]
                    * len(this_active_snap_list)
                )

            retval = [config_active_snap_list, time_list]

        if return_node_loc_num:
            node_list, loc_num_list = self._get_node_snap_lists_for_configs(
                config_active_snap_list, time_list=time_list
            )
            retval.extend([node_list, loc_num_list])

        if len(retval) == 1:
            return retval[0]
        else:
            return tuple(retval)

    def get_correlator_config_input_index(
        self,
        config_hash=None,
        correlator_index=None,
        most_recent=None,
        starttime=None,
        stoptime=None,
        return_node_loc_num=False,
    ):
        """
        Get a correlator config input index records from the M&C database.

        If a config_hash is provided, the time-related optional keywords are ignored and
        if return_node_loc_num is True, the returned mappings are the ones currently in
        effect (regardless of when the config hash was last used).

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        config_hash : str
            Unique MD5 hash of the config to get records for.
        correlator_index : int
            Correlator index to get records for. If None, get all correlator index
            records for this hash or time.
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        return_node_loc_num : bool
            If True, return the node and SNAP location numbers for the active SNAPS
            If a config_hash is provided, setting this to True will get the node and
            SNAP location numbers currently in effect (effectively time="now").

        Returns
        -------
        list
            list of CorrelatorConfigInputIndex objects.
        time_list : list of Astropy Time objects, optional
            List of start times when the config params were used, same length as the list
            of CorrelatorConfigInputIndex objects. Only provided if `config_hash` is None.
        node_list : list of int, optional
            List of nodes for each object in the list of CorrelatorConfigInputIndex objects.
        loc_num_list : list of int, optional
            List of SNAP location numbers for each object in the list of
            CorrelatorConfigInputIndex objects.

        """
        if config_hash is not None:
            query = self.query(corr.CorrelatorConfigInputIndex).filter(
                corr.CorrelatorConfigInputIndex.config_hash == config_hash
            )

            if correlator_index is not None:
                query = query.filter(
                    corr.CorrelatorConfigInputIndex.correlator_index == correlator_index
                )

            config_input_index_list = query.all()
            retval = [config_input_index_list]
            time_list = None
        else:
            # get the config statuses to get hashes for the times of interest
            config_status_list = self.get_correlator_config_status(
                most_recent=most_recent, starttime=starttime, stoptime=stoptime
            )
            time_list = []
            config_input_index_list = []
            for config_status in config_status_list:
                this_input_index_list = self.get_correlator_config_input_index(
                    config_hash=config_status.config_hash,
                    correlator_index=correlator_index,
                )
                config_input_index_list.extend(this_input_index_list)
                time_list.extend(
                    [Time(config_status.time, format="gps")]
                    * len(this_input_index_list)
                )

            retval = [config_input_index_list, time_list]

        if return_node_loc_num:
            node_list, loc_num_list = self._get_node_snap_lists_for_configs(
                config_input_index_list, time_list=time_list
            )
            retval.extend([node_list, loc_num_list])

        if len(retval) == 1:
            return retval[0]
        else:
            return tuple(retval)

    def get_correlator_config_phase_switch_index(
        self,
        config_hash=None,
        most_recent=None,
        starttime=None,
        stoptime=None,
        return_node_loc_num=False,
    ):
        """
        Get a correlator config phase switch index records from the M&C database.

        If a config_hash is provided, the time-related optional keywords are ignored and
        if return_node_loc_num is True, the returned mappings are the ones currently in
        effect (regardless of when the config hash was last used).

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        config_hash : str
            Unique MD5 hash of the config to get records for.
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        return_node_loc_num : bool
            If True, return the node and SNAP location numbers for the active SNAPS
            If a config_hash is provided, setting this to True will get the node and
            SNAP location numbers currently in effect (effectively time="now").

        Returns
        -------
        list
            list of CorrelatorConfigPhaseSwitchIndex objects.
        time_list : list of Astropy Time objects, optional
            List of start times when the config params were used, same length as the list
            of CorrelatorConfigPhaseSwitchIndex objects. Only provided if `config_hash` is None.
        node_list : list of int, optional
            List of nodes for each object in the list of CorrelatorConfigPhaseSwitchIndex objects.
        loc_num_list : list of int, optional
            List of SNAP location numbers for each object in the list of
            CorrelatorConfigPhaseSwitchIndex objects.

        """
        if config_hash is not None:
            query = self.query(corr.CorrelatorConfigPhaseSwitchIndex).filter(
                corr.CorrelatorConfigPhaseSwitchIndex.config_hash == config_hash
            )

            config_ps_index_list = query.all()
            retval = [config_ps_index_list]
            time_list = None
        else:
            # get the config statuses to get hashes for the times of interest
            config_status_list = self.get_correlator_config_status(
                most_recent=most_recent, starttime=starttime, stoptime=stoptime
            )
            time_list = []
            config_ps_index_list = []
            for config_status in config_status_list:
                this_ps_index_list = self.get_correlator_config_phase_switch_index(
                    config_hash=config_status.config_hash,
                )
                config_ps_index_list.extend(this_ps_index_list)
                time_list.extend(
                    [Time(config_status.time, format="gps")] * len(this_ps_index_list)
                )

            retval = [config_ps_index_list, time_list]

        if return_node_loc_num:
            node_list, loc_num_list = self._get_node_snap_lists_for_configs(
                config_ps_index_list, time_list=time_list
            )
            retval.extend([node_list, loc_num_list])

        if len(retval) == 1:
            return retval[0]
        else:
            return tuple(retval)

    def add_correlator_config_status(self, time, config_hash):
        """
        Add new correlator config status to the M&C database.

        Parameters
        ----------
        time : astropy Time object
            Astropy time object based on a timestamp reported by the correlator.
        config_hash : str
            Unique hash of the config.

        """
        self.add(corr.CorrelatorConfigStatus.create(time, config_hash))

    def get_correlator_config_status(
        self,
        most_recent=None,
        starttime=None,
        config_hash=None,
        stoptime=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get correlator config status record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        config_hash : str
            unique hash for config file
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of CorrelatorConfigStatus objects

        """
        return self._time_filter(
            corr.CorrelatorConfigStatus,
            "time",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            filter_column="config_hash",
            filter_value=config_hash,
            write_to_file=write_to_file,
            filename=filename,
        )

    def _add_config_file_to_librarian(
        self, config, config_hash, librarian_filename
    ):  # pragma: no cover
        """
        Save a new config file in the Librarian.

        Parameters
        ----------
        config : dict
            Dict of config info from redis/hera_corr_cm.
        config_hash : str
            Unique hash of the config.
        librarian_filename : str
            Name of the file in the librarian.

        """
        from hera_librarian import LibrarianClient

        # write config out to a file
        lib_store_path = "correlator_yaml/" + librarian_filename
        librarian_filename_full = os.path.join("/tmp", librarian_filename)
        with open(librarian_filename_full, "w") as outfile:
            yaml.dump(config, outfile, default_flow_style=False)

        # add config file to librarian
        lib_client = LibrarianClient("local-maint")

        lib_client.upload_file(
            librarian_filename_full,
            lib_store_path,
            "infer",
            deletion_policy="disallowed",
            null_obsid=True,
        )

        # delete the file
        os.remove(librarian_filename_full)

    def add_correlator_config_from_corrcm(
        self,
        config_state_dict=None,
        testing=False,
        redishost=corr.DEFAULT_REDIS_ADDRESS,
    ):
        """
        Get and add correlator config information using a HeraCorrCM object.

        This function connects to the correlator and gets the latest config
        using the `corr._get_config` function. If it is a new config file, it
        connects to the Librarian to upload the config file. It also parses the config
        information into the config related tables (correlator_config_params,
        correlator_config_active_snap, correlator_config_input_index,
        correlator_config_phase_switch_index).
        For testing purposes, it can optionally accept an input dict instead of
        connecting to the correlator.

        Parameters
        ----------
        config_state_dict : dict
            A dict containing info as in the return dict from _get_config() for
            testing purposes. If None, _get_config() is called.
        testing : bool
            If true, don't add config file to the Librarian or add a record of
            it to the database and return the CorrelatorConfigFile and
            CorrelatorConfigStatus objects.
        redishost : str
            redis address to use. Defaults to correlator.DEFAULT_REDIS_ADDRESS.

        Returns
        -------
        list of objects, optional
            If testing is True, returns the list of CorrelatorConfigStatus,
            CorrelatorConfigFile, CorrelatorConfigParams, CorrelatorConfigActiveSNAP,
            CorrelatorConfigInputIndex, and CorrelatorConfigPhaseSwitchIndex objects
            based on the config_state_dict.

        """
        if config_state_dict is None:
            self.add_corr_obj(redishost=redishost)
            config_state_dict = corr._get_config(
                corr_cm=self.corr_obj, redishost=redishost
            )

        time = config_state_dict["time"]
        config = config_state_dict["config"]
        config_hash = config_state_dict["hash"]

        config_obj_list = []
        # first check to see if a status with this hash (so identical)
        # already exists
        same_config_status = self.get_correlator_config_status(
            most_recent=True, config_hash=config_hash
        )
        if len(same_config_status) == 0:
            # There's not a status with this config hash.
            # now check to see if a file with this hash (so identical)
            # already exists
            same_config_file = self.get_correlator_config_file(config_hash=config_hash)

            if len(same_config_file) == 0:
                # There's not a file with this config hash.
                librarian_filename = (
                    "correlator_config_" + str(int(floor(time.gps))) + ".yaml"
                )
                config_file_obj = corr.CorrelatorConfigFile.create(
                    config_hash, librarian_filename
                )

                # parse it get a list of config related objects
                config_objs = corr._parse_config(config, config_hash)

                if not testing:  # pragma: no cover
                    # This config is new.
                    # save it to the Librarian
                    self._add_config_file_to_librarian(
                        config, config_hash, librarian_filename
                    )

                    # add it to the config file table
                    self.add(config_file_obj)
                    # commit to ensure that the hash is in the config file table before
                    # anything that uses that hash as a Foreign key is added.
                    self.commit()

                    # add the config details to their respective tables
                    for obj in config_objs:
                        self.add(obj)

                    self.commit()
                else:
                    config_obj_list.append(config_file_obj)
                    config_obj_list.extend(config_objs)

            # make the config status object
            config_status_obj = corr.CorrelatorConfigStatus.create(time, config_hash)
            if not testing:  # pragma: no cover
                self.add(config_status_obj)
                self.commit()
            else:
                config_obj_list.append(config_status_obj)
        else:
            if same_config_status[0].time != floor(time.gps):
                # time is different, so need a new row
                config_status_obj = corr.CorrelatorConfigStatus.create(
                    time, config_hash
                )

                if not testing:  # pragma: no cover
                    # use the `ignoring_duplicates` so there's no error if this
                    # already exists (this happened on site at one point)
                    self._insert_ignoring_duplicates(
                        corr.CorrelatorConfigStatus, [config_status_obj]
                    )
                    self.commit()
                else:
                    config_obj_list.append(config_status_obj)

        if testing:
            return config_obj_list

    def add_correlator_software_versions(self, time, package, version):
        """
        Add new correlator software versions to the M&C database.

        Parameters
        ----------
        time : astropy Time object
            Astropy time object based on the version report timestamp.
        package : str
            Name of the correlator software module or <package>:<script> for
                daemonized processes(e.g. 'hera_corr_cm',
                'udpSender:hera_node_keep_alive.py').
        version : str
            Version string for this package or script.

        """
        self.add(corr.CorrelatorSoftwareVersions.create(time, package, version))

    def get_correlator_software_versions(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        package=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get correlator software versions record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        package : str
            name of the correlator software module (e.g. "hera_corr_f")
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of CorrelatorSoftwareVersions objects

        """
        return self._time_filter(
            corr.CorrelatorSoftwareVersions,
            "time",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            filter_column="package",
            filter_value=package,
            write_to_file=write_to_file,
            filename=filename,
        )

    def add_snap_config_version(self, init_time, version, init_args, config_hash):
        """
        Add new SNAP configuration and version to the M&C database.

        Parameters
        ----------
        init_time : astropy Time object
            Astropy time object for when the SNAPs were last initialized with
            the `hera_snap_feng_init.py` script
        version : str
            Version string for the hera_corr_f package
        init_args : str
            Arguments passed to the initialization script at runtime
        config_hash : str
            Unique hash of the config, foreign key into correlator_config_file
            table

        """
        self.add(
            corr.SNAPConfigVersion.create(init_time, version, init_args, config_hash)
        )

    def get_snap_config_version(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get SNAP configuration and version record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of SNAPConfigVersion objects

        """
        return self._time_filter(
            corr.SNAPConfigVersion,
            "init_time",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            write_to_file=write_to_file,
            filename=filename,
        )

    def add_corr_snap_versions_from_corrcm(
        self,
        corr_snap_version_dict=None,
        testing=False,
        redishost=corr.DEFAULT_REDIS_ADDRESS,
    ):
        """
        Get and add correlator and SNAP configuration and version info.

        This function connects to the correlator and gets the latest data using
        the `_get_corr_versions` function. For testing purposes, it can
        optionally accept an input dict instead of connecting to the correlator.

        If the current database is PostgreSQL, this function will use a
        special insertion method that will ignore records that are redundant
        with ones already in the database. This makes it convenient to sample
        the data frequently on qmaster.

        Parameters
        ----------
        corr_snap_version_dict : dict
            A dict containing info as in the return dict from
            `corr._get_corr_versions()` for testing purposes. If None,
            `_get_corr_versions()` is called.
        testing : bool
            If true, don't add a record of it to the database and return the
            list of CorrelatorSoftwareVersions, CorrelatorConfigFile,
            CorrelatorConfigStatus and SNAPConfigVersion objects.
        redishost : str
            redis address to use. Defaults to correlator.DEFAULT_REDIS_ADDRESS.

        Returns
        -------
        list of objects, optional
            Optionally returns the list of CorrelatorSoftwareVersions,
            CorrelatorConfigFile, CorrelatorConfigStatus and
            SNAPConfigVersion objects (if testing is True)

        """
        if corr_snap_version_dict is None:
            self.add_corr_obj(redishost=redishost)
            corr_snap_version_dict = corr._get_corr_versions(corr_cm=self.corr_obj)

        corr_version_list = []
        snap_version_list = []
        for package, version_dict in corr_snap_version_dict.items():
            time = Time(version_dict["timestamp"], format="datetime")
            version = version_dict["version"]

            if package == "hera_corr_cm":
                # we get a new timestamp every time we call hera_corr_cm.
                # Don't make a new row unless it's a new version.
                # First, get most recent version in table
                last_hera_corr_cm_entry = self.get_correlator_software_versions(
                    package="hera_corr_cm"
                )
                if len(last_hera_corr_cm_entry) == 0:
                    last_version = ""
                else:
                    last_version = last_hera_corr_cm_entry[0].version
                if last_version != version:
                    # this is a new version, make a new object
                    corr_version_list.append(
                        corr.CorrelatorSoftwareVersions.create(time, package, version)
                    )
            elif package != "snap":
                corr_version_list.append(
                    corr.CorrelatorSoftwareVersions.create(time, package, version)
                )
            else:
                init_args = version_dict["init_args"]
                config_hash = version_dict["config_md5"]
                snap_version_list.append(
                    corr.SNAPConfigVersion.create(time, version, init_args, config_hash)
                )

                config_time = Time(version_dict["config_timestamp"], format="datetime")
                config = version_dict["config"]
                snap_config_dict = {
                    "time": config_time,
                    "hash": config_hash,
                    "config": config,
                }

        # make sure this config is in the correlator config status table
        # (really should be, but this will add it if it was somehow missed)
        config_obj_list = self.add_correlator_config_from_corrcm(
            config_state_dict=snap_config_dict, testing=testing
        )

        if testing:
            return corr_version_list + config_obj_list + snap_version_list
        else:  # pragma: no cover
            self._insert_ignoring_duplicates(
                corr.CorrelatorSoftwareVersions, corr_version_list
            )
            self._insert_ignoring_duplicates(corr.SNAPConfigVersion, snap_version_list)

    def add_snap_status(
        self,
        time,
        hostname,
        serial_number,
        psu_alert,
        pps_count,
        fpga_temp,
        uptime_cycles,
        last_programmed_time,
        is_programmed,
        adc_is_configured,
        is_initialized,
        dest_is_configured,
        version,
        sample_rate,
    ):
        """
        Add new snap status data to the M&C database.

        Parameters
        ----------
        time : astropy Time object
            Astropy time object based on a timestamp reported by the correlator.
        hostname : str
            SNAP hostname.
        serial_number : str
            Serial number of the SNAP board.
        psu_alert : bool
            True if SNAP PSU (aka PMB) controllers have issued an alert.
            False otherwise.
        pps_count : int
            Number of PPS pulses received since last programming cycle.
        fpga_temp : float
            Reported FPGA temperature in degrees Celsius.
        uptime_cycles : int
            Multiples of 500e6 ADC clocks since last programming cycle.
        last_programmed_time : astropy Time object
            Astropy time object based on the last time this FPGA was programmed.
        is_programmed : bool
            True if the host is programmed.
        adc_is_configured : bool
            True if the host adc is configured
        is_initialized : bool
            True if host is initialized
        dest_is_configured : bool
            True if the ethernet destination is configured.
        version : str
            Version of firmware installed
        sample_rate : float
            Sample rate in MHz

        """
        # get node & snap location number from config management
        nodeID, snap_loc_num = self._get_node_snap_from_serial(serial_number)

        self.add(
            corr.SNAPStatus.create(
                time,
                hostname,
                nodeID,
                snap_loc_num,
                serial_number,
                psu_alert,
                pps_count,
                fpga_temp,
                uptime_cycles,
                last_programmed_time,
                is_programmed,
                adc_is_configured,
                is_initialized,
                dest_is_configured,
                version,
                sample_rate,
            )
        )

    def get_snap_status(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        hostname=None,
        nodeID=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get snap status record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        hostname : str
            SNAP hostname.
        nodeID : int
            node number (integer running from 0 to 30)
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of SNAPStatus objects

        """
        return self._time_filter(
            corr.SNAPStatus,
            "time",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            filter_column=["hostname", "node"],
            filter_value=[hostname, nodeID],
            write_to_file=write_to_file,
            filename=filename,
        )

    def _get_antennas_for_snap(
        self, snap_hostname, snap_channel_number=None, session=None, at_date="now"
    ):
        """
        Get antenna number and pol connected to SNAP hostname and input from cm.

        Parameters
        ----------
        snap_hostname : str
            SNAP hostname.
        snap_channel_number : list of int or None
            List of channel numbers to get antennas for. If None, get all inputs (0-5).
        session : Session object
            Session to pass to cm_handling.Handling. Defaults to self.
        at_date : "now", Time or gps second
            Date at which to initialize.

        Returns
        -------
        dict
            keyed on snap_channel_number, values are dicts with keys of "antenna"
            (integer antenna number) and "pol" string, either "e" or "n".

        """
        if session is None:
            session = self

        snap_input_name_dict = {0: "n0", 1: "e2", 2: "n4", 3: "e6", 4: "n8", 5: "e10"}

        if snap_channel_number is None:
            snap_channel_number = snap_input_name_dict.keys()
        elif not isinstance(snap_channel_number, list):
            snap_channel_number = [snap_channel_number]

        snap_serial = self.get_snap_serial_from_hostname(snap_hostname, at_date=at_date)

        if snap_serial is None:
            output_dict = {}
            for input_id in snap_channel_number:
                output_dict[input_id] = {}
                output_dict[input_id]["antenna"] = None
                output_dict[input_id]["pol"] = None

            return output_dict

        hookup = Hookup(session)
        hd = hookup.get_hookup(snap_serial, at_date="now", exact_match=True)
        snapr = f"{snap_serial.upper()}:A"

        output_dict = {}
        for input_id in snap_channel_number:
            output_dict[input_id] = {}
            this_input_name = snap_input_name_dict[input_id]

            polport = None
            for key in hd[snapr].hookup.keys():
                if this_input_name in key:
                    polport = key
                    break
            if polport is not None and hd[snapr].fully_connected[polport]:
                output_dict[input_id]["antenna"] = int(
                    hd[snapr].hookup[polport][0].upstream_part[2:]
                )
                output_dict[input_id]["pol"] = polport[0].lower()
            else:
                output_dict[input_id]["antenna"] = None
                output_dict[input_id]["pol"] = None

        return output_dict

    def add_snap_input(
        self,
        time,
        hostname,
        snap_channel_number,
        snap_input,
    ):
        """
        Add new snap status data to the M&C database.

        Parameters
        ----------
        time : astropy Time object
            Astropy time object based on a timestamp reported by the correlator.
        hostname : str
            SNAP hostname.
        snap_channel_number : int
            The SNAP ADC channel number (0-5).
        snap_input : str
            Either "adc" or "noise-%d" where %d is the noise seed.

        """
        # get attached antpols from config management
        antpol_dict = self._get_antennas_for_snap(hostname, snap_channel_number)

        self.add(
            corr.SNAPInput.create(
                time,
                hostname,
                snap_channel_number,
                antpol_dict[snap_channel_number]["antenna"],
                antpol_dict[snap_channel_number]["pol"],
                snap_input,
            )
        )

    def get_snap_input(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        hostname=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get snap input record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        hostname : str
            SNAP hostname
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of SNAPInput objects

        """
        return self._time_filter(
            corr.SNAPInput,
            "time",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            filter_column="hostname",
            filter_value=hostname,
            write_to_file=write_to_file,
            filename=filename,
        )

    def add_snap_status_from_corrcm(
        self,
        snap_status_dict=None,
        testing=False,
        cm_session=None,
        redishost=corr.DEFAULT_REDIS_ADDRESS,
    ):
        """Get and add snap status information using a HeraCorrCM object.

        This function connects to the correlator and gets the latest data using
        the `_get_snap_status` function. For testing purposes, it can
        optionally accept an input dict instead of connecting to the correlator.
        It can use a different session for the cm info (this is useful for
        testing onsite).

        If the current database is PostgreSQL, this function will use a
        special insertion method that will ignore records that are redundant
        with ones already in the database. This makes it convenient to sample
        the data frequently on qmaster.

        Parameters
        ----------
        snap_status_dict : dict
            A dict containing info as in the return dict from _get_snap_status()
            for testing purposes. If None, _get_snap_status() is called.
        testing : bool
            If true, don't add a record of it to the database and return the
            list of SNAPStatus objects.
        cm_session:
            Session object to use for the CM queries. Defaults to self, but can
            be set to another session instance (useful for testing).
        redishost : str
            redis address to use. Defaults to correlator.DEFAULT_REDIS_ADDRESS.

        Returns
        -------
        Optionally returns the list of SNAPStatus and SNAPInput objects (if testing is
        True)

        """
        if snap_status_dict is None:
            self.add_corr_obj(redishost=redishost)
            snap_status_dict = corr._get_snap_status(
                corr_cm=self.corr_obj, redishost=redishost
            )
        snap_status_list = []
        snap_input_list = []
        for hostname, snap_dict in snap_status_dict.items():
            # first check if the timestamp is the string 'None'
            # if it is, skip this snap
            timestamp = snap_dict["timestamp"]
            if timestamp is None or timestamp == "None":
                continue
            else:
                time = Time(timestamp, format="datetime")

            serial_number = snap_dict["serial"]
            psu_alert = snap_dict["pmb_alert"]
            pps_count = snap_dict["pps_count"]
            fpga_temp = snap_dict["temp"]
            uptime_cycles = snap_dict["uptime"]
            is_programmed = snap_dict["is_programmed"]
            adc_is_configured = snap_dict["adc_is_configured"]
            is_initialized = snap_dict["is_initialized"]
            dest_is_configured = snap_dict["dest_is_configured"]
            version = snap_dict["version"]
            sample_rate = snap_dict["sample_rate"]

            # get attached antpols from config management
            antpol_dict = self._get_antennas_for_snap(hostname)
            if snap_dict["input"] is None:
                for snap_channel_number in range(6):
                    snap_input_list.append(
                        corr.SNAPInput.create(
                            time,
                            hostname,
                            snap_channel_number,
                            antpol_dict[snap_channel_number]["antenna"],
                            antpol_dict[snap_channel_number]["pol"],
                            None,
                        )
                    )
            else:
                for snap_channel_number, snap_input in enumerate(
                    snap_dict["input"].split(",")
                ):
                    snap_input_list.append(
                        corr.SNAPInput.create(
                            time,
                            hostname,
                            snap_channel_number,
                            antpol_dict[snap_channel_number]["antenna"],
                            antpol_dict[snap_channel_number]["pol"],
                            snap_input,
                        )
                    )
            last_programmed_datetime = snap_dict["last_programmed"]
            if last_programmed_datetime is not None:
                last_programmed_time = Time(last_programmed_datetime, format="datetime")
            else:
                last_programmed_time = None

            # get nodeID & snap location number from config management
            if serial_number is not None:
                nodeID, snap_loc_num = self._get_node_snap_from_serial(
                    serial_number, session=cm_session
                )
            else:
                nodeID = None
                snap_loc_num = None

            snap_status_list.append(
                corr.SNAPStatus.create(
                    time,
                    hostname,
                    nodeID,
                    snap_loc_num,
                    serial_number,
                    psu_alert,
                    pps_count,
                    fpga_temp,
                    uptime_cycles,
                    last_programmed_time,
                    is_programmed,
                    adc_is_configured,
                    is_initialized,
                    dest_is_configured,
                    version,
                    sample_rate,
                )
            )

        if testing:
            return snap_status_list + snap_input_list
        else:
            self._insert_ignoring_duplicates(corr.SNAPStatus, snap_status_list)
            self._insert_ignoring_duplicates(corr.SNAPInput, snap_input_list)

    def add_snap_feng_init_status(self, time, hostname, status):
        """
        Add new snap feng init status to the M&C database.

        Parameters
        ----------
        time : astropy Time object
            Astropy time object based on a timestamp reported by the correlator.
        hostname : str
            SNAP hostname.
        status : str
            Feng init status of the SNAP. Should be one of "working" (hera_corr_f
            thinks it works), "unconfig" (snap made it to arming, but weren't
            configured, so don't work), "maxout" (snap made it all the way through
            arming and configuring but was ignored because there were too many snaps).

        """
        self.add(corr.SNAPFengInitStatus.create(time, hostname, status))

    def get_snap_feng_init_status(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        hostname=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get snap feng init status record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        hostname : str
            SNAP hostname
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of SNAPFengInitStatus objects

        """
        return self._time_filter(
            corr.SNAPFengInitStatus,
            "time",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            filter_column="hostname",
            filter_value=hostname,
            write_to_file=write_to_file,
            filename=filename,
        )

    def add_snap_feng_init_status_from_redis(
        self,
        testing=False,
        redishost=corr.DEFAULT_REDIS_ADDRESS,
    ):
        """
        Get and add the current feng_init status values from redis.

        Uses the `correlator._get_snap_feng_init_status_from_redis` function

        If the current database is PostgreSQL, this function will use a
        special insertion method that will ignore records that are redundant
        with ones already in the database. This makes it convenient to sample
        the feng_init status data densely on qmaster.

        Parameters
        ----------
        testing : bool
            If true, return the list of SNAPFengInitStatus objects and don't add then
            to the database.
        redishost : str
            redis address to use. Defaults to correlator.DEFAULT_REDIS_ADDRESS.

        Returns
        -------
        list of SNAPFengInitStatus, optional
            If testing is True, returns the SNAPFengInitStatus objects rather than adding
            it to the database.

        """
        log_time, snap_feng_status = corr._get_snap_feng_init_status_from_redis(
            redishost=redishost
        )

        snap_configure_objs = []
        for hostname, state in snap_feng_status.items():
            snap_configure_objs.append(
                corr.SNAPFengInitStatus.create(log_time, hostname, state)
            )

        if testing:
            return snap_configure_objs

        self._insert_ignoring_duplicates(corr.SNAPFengInitStatus, snap_configure_objs)

    def add_antenna_status(
        self,
        time,
        antenna_number,
        antenna_feed_pol,
        snap_hostname,
        snap_channel_number,
        adc_mean,
        adc_rms,
        adc_power,
        pam_atten,
        pam_power,
        pam_voltage,
        pam_current,
        pam_id,
        fem_voltage,
        fem_current,
        fem_id,
        fem_switch,
        fem_lna_power,
        fem_imu_theta,
        fem_imu_phi,
        fem_temp,
        fft_overflow,
        eq_coeffs,
        histogram,
    ):
        """
        Add new antenna status data to the M&C database.

        Parameters
        ----------
        time : astropy Time object
            Astropy time object based on a timestamp reported by the
            correlator.
        antenna_number : int
            Antenna number.
        antenna_feed_pol : str
            Feed polarization, either 'e' or 'n'.
        snap_hostname : str
            Hostname of SNAP the antenna is connected to.
        snap_channel_number : int
            The SNAP ADC channel number (0-7) that this antenna is connected
            to.
        adc_mean : float
            Mean ADC value, in ADC units, meaning raw ADC values interpreted as
            signed integers between -128 and +127. Typically ~ -0.5.
        adc_rms : float
            RMS ADC value, in ADC units, meaning raw ADC values interpreted as
            signed integers between -128 and +127.  Should be ~ 10-20.
        adc_power : float
            Mean ADC power, in ADC units squared, meaning raw ADC values
            interpreted as signed integers between -128 and +127 and then
            squared. Since mean should be close to zero, this should just be
            adc_rms^2.
        pam_atten : int
            PAM attenuation setting for this antenna, in dB.
        pam_power : float
            PAM power sensor reading for this antenna, in dBm.
        pam_voltage : float
            PAM voltage sensor reading for this antenna, in Volts.
        pam_current : float
            PAM current sensor reading for this antenna, in Amps.
        pam_id : str
            Serial number of this PAM.
        fem_switch : {'antenna', 'load', 'noise'}
            Switch state for this FEM.
        fem_lna_power : bool
            Power state of this FEM (True if powered).
        fem_imu_theta : float
            IMU-reported theta, in degrees.
        fem_imu_phi : float
            IMU-reported phi, in degrees.
        fem_voltage : float
            FEM voltage sensor reading for this antenna, in Volts.
        fem_current : float
            FEM current sensor reading for this antenna, in Amps.
        fem_id : str
            Serial number of this FEM.
        fem_temp : float
            EM temperature sensor reading for this antenna in degrees Celsius.
        fft_overflow : bool
            Indicator of an FFT overflow, True if there was an FFT overflow.
        eq_coeffs : list of float
            Digital EQ coefficients, used for keeping the bit occupancy in the
            correct range, for this antenna, list of floats. Note this these
            are not divided out anywhere in the DSP chain (!).
        histogram : list of int
            ADC histogram counts.

        """
        self.add(
            corr.AntennaStatus.create(
                time,
                antenna_number,
                antenna_feed_pol,
                snap_hostname,
                snap_channel_number,
                adc_mean,
                adc_rms,
                adc_power,
                pam_atten,
                pam_power,
                pam_voltage,
                pam_current,
                pam_id,
                fem_voltage,
                fem_current,
                fem_id,
                fem_switch,
                fem_lna_power,
                fem_imu_theta,
                fem_imu_phi,
                fem_temp,
                fft_overflow,
                eq_coeffs,
                histogram,
            )
        )

    def get_antenna_status(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        antenna_number=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get antenna status record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        antenna_number : int
            antenna number
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of AntennaStatus objects

        """
        return self._time_filter(
            corr.AntennaStatus,
            "time",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            filter_column="antenna_number",
            filter_value=antenna_number,
            write_to_file=write_to_file,
            filename=filename,
        )

    def add_antenna_status_from_corrcm(
        self, ant_status_dict=None, testing=False, redishost=corr.DEFAULT_REDIS_ADDRESS
    ):
        """Get and add antenna status information using a HeraCorrCM object.

        This function connects to the correlator and gets the latest data using
        the `create_antenna_status` function. For testing purposes, it can
        optionally accept an input dict instead of connecting to the correlator.

        If the current database is PostgreSQL, this function will use a
        special insertion method that will ignore records that are redundant
        with ones already in the database. This makes it convenient to sample
        the data frequently on qmaster.

        Parameters
        ----------
        ant_status_dict : dict
            A dict containing info as in the return dict from
            corr._get_ant_status() for testing purposes. If None,
            _get_ant_status() is called.
        testing : bool
            If true, don't add a record of it to the database and return the
            list of AntennaStatus objects.
        redishost : str
            redis address to use. Defaults to correlator.DEFAULT_REDIS_ADDRESS.

        Returns
        -------
        list of objects, optional
            If testing is true, returns the list of AntennaStatus objects based
            on the ant_status_dict.

        """
        if ant_status_dict is None:
            self.add_corr_obj(redishost=redishost)
            corr_cm = self.corr_obj
        else:
            corr_cm = None
        antenna_status_list = corr.create_antenna_status(
            corr_cm=corr_cm, ant_status_dict=ant_status_dict
        )

        if testing:
            return antenna_status_list
        else:
            self._insert_ignoring_duplicates(corr.AntennaStatus, antenna_status_list)

    def add_ant_metric(self, obsid, ant, pol, metric, val):
        """
        Add a new antenna metric or update an existing metric.

        Parameters
        ----------
        obsid : long integer
            Observation identification number.
        ant : int
            Antenna number.
        pol : str ('x', 'y', 'n', 'e', 'jnn', or 'jee')
            Polarization name.
        metric : str
            Metric name, foreign key into `metric_list`.
        val : float
            Value of metric.

        """
        db_time = self.get_current_db_time()

        obj_list = [AntMetrics.create(obsid, ant, pol, metric, db_time, val)]
        self._insert_ignoring_duplicates(AntMetrics, obj_list, update=True)

    def get_ant_metric(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        ant=None,
        pol=None,
        metric=None,
        obsid=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get antenna metric(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        If any of obsid, ant, pol, metric are set, then all records that match
        those are returned unless most_recent or starttime is set.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        ant : int
            Antenna number to get records for. If none, all antennas will be included.
        pol : str
            Polarization to get records for, one of ['x', 'y', 'n', 'e', 'jnn', or
            'jee']. If none, all polarizations will be included.
        metric : str
            Metric name to get records for. If none, all metrics will beincluded.
        obsid : int
            obsid to get records for. If none, all obsids will be included.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of AntMetrics objects

        """
        if (
            ant is None
            and pol is None
            and metric is None
            and obsid is None
            and starttime is None
        ):
            if most_recent is None:
                most_recent = True
            elif most_recent is False:
                raise ValueError(
                    "If most_recent is set to False, at least one of ant, pol, metric, "
                    "obsid, or starttime must be specified."
                )

        if most_recent is True or starttime is not None:
            return self._time_filter(
                AntMetrics,
                "mc_time",
                most_recent=most_recent,
                starttime=starttime,
                stoptime=stoptime,
                filter_column=["ant", "pol", "metric", "obsid"],
                filter_value=[ant, pol, metric, obsid],
                write_to_file=write_to_file,
                filename=filename,
            )

        query = self.query(AntMetrics)
        if ant is not None:
            query = query.filter(AntMetrics.ant == ant)
        if pol is not None:
            query = query.filter(AntMetrics.pol == pol)
        if metric is not None:
            query = query.filter(AntMetrics.metric == metric)
        if obsid is not None:
            query = query.filter(AntMetrics.obsid == obsid)

        if write_to_file:
            self._write_query_to_file(query, AntMetrics, filename=filename)

        else:
            return query.all()

    def add_array_metric(self, obsid, metric, val):
        """
        Add a new array metric or update an existing metric.

        Parameters
        ----------
        obsid : long integer
            Observation identification number.
        metric : str
            Metric name, foreign key into `metric_list`.
        val : float
            Value of metric.

        """
        db_time = self.get_current_db_time()

        obj_list = [ArrayMetrics.create(obsid, metric, db_time, val)]
        self._insert_ignoring_duplicates(ArrayMetrics, obj_list, update=True)

    def get_array_metric(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        metric=None,
        obsid=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get array metric(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        metric : str
            Metric name to get records for. If none, all metrics will beincluded.
        obsid : int
            obsid to get records for. If none, all obsids will be included.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of ArrayMetrics objects

        """
        if metric is None and obsid is None and starttime is None:
            if most_recent is None:
                most_recent = True
            elif most_recent is False:
                raise ValueError(
                    "If most_recent is set to False, at least one of metric, obsid, or "
                    "starttime must be specified."
                )

        if most_recent is True or starttime is not None:
            return self._time_filter(
                ArrayMetrics,
                "mc_time",
                most_recent=most_recent,
                starttime=starttime,
                stoptime=stoptime,
                filter_column=["metric", "obsid"],
                filter_value=[metric, obsid],
                write_to_file=write_to_file,
                filename=filename,
            )

        query = self.query(ArrayMetrics)
        if metric is not None:
            query = query.filter(ArrayMetrics.metric == metric)
        if obsid is not None:
            query = query.filter(ArrayMetrics.obsid == obsid)

        if write_to_file:
            self._write_query_to_file(query, ArrayMetrics, filename=filename)

        else:
            return query.all()

    def add_metric_desc(self, metric, desc):
        """
        Add a new metric description to the M&C database.

        Parameters
        ----------
        metric : str
            Metric name.
        desc : str
            Description of metric.

        """
        self.add(MetricList.create(metric, desc))

    def update_metric_desc(self, metric, desc):
        """
        Update the description of a metric in the M&C database.

        This will be required when replacing an RTP auto-generated description
        for new metrics.

        Parameters
        ----------
        metric : str
            Metric name.
        desc : str
            Description of metric.

        """
        self.query(MetricList).filter(MetricList.metric == metric)[0].desc = desc
        self.commit()

    def get_metric_desc(self, metric=None, write_to_file=False, filename=None):
        """
        Get metric description(s) from the M&C database.

        Parameters
        ----------
        metric : str
            Metric name. Defaults to returning all metrics.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of MetricList objects

        """
        query = self.query(MetricList)

        if metric is not None:
            query = query.filter(MetricList.metric == metric)

        if write_to_file:
            self._write_query_to_file(query, MetricList, filename=filename)
        else:
            return query.all()

    def check_metric_desc(self, metric):
        """
        Check that metric has a description in the db, fill one in if not.

        Parameters
        ----------
        metrics : str or list of strings
            Metric name.

        """
        r = self.get_metric_desc(metric=metric)
        if len(r) == 0:
            warnings.warn(
                "Metric " + metric + " not found in db. "
                "Adding a filler description. Please update ASAP "
                "with hera_mc/scripts/update_qm_list.py."
            )
            self.add_metric_desc(
                metric,
                "Auto-generated description. Update "
                "with hera_mc/scripts/update_qm_list.py",
            )
            self.commit()

    def update_qm_list(self):
        """Update metric list according to descriptions in hera_qm."""
        from hera_qm.utils import get_metrics_dict

        metric_list = get_metrics_dict()

        for metric, descrip in metric_list.items():
            # Check if metric is already in db.
            r = self.get_metric_desc(metric=metric)
            if len(r) == 0:
                self.add_metric_desc(metric, descrip)
            else:
                self.update_metric_desc(metric, descrip)
        self.commit()

    def ingest_metrics_file(self, filename, ftype):
        """
        Add a file worth of quality metrics to the db.

        Parameters
        ----------
        filename : str
            File containing metrics to be added to db.
        ftype : {'ant', 'firstcal', 'omnical'}
            Type of metrics file.

        """
        from hera_qm.utils import metrics2mc

        try:
            obsid = self.get_lib_files(filename=os.path.basename(filename))[0].obsid
        except IndexError as err:
            raise ValueError(
                f"File {filename} has not been logged in "
                "Librarian, so we cannot add to M&C."
            ) from err
        d = metrics2mc(filename, ftype)
        for metric, dd in d["ant_metrics"].items():
            self.check_metric_desc(metric)
            for ant, pol, val in dd:
                self.add_ant_metric(obsid, ant, pol, metric, val)
        for metric, val in d["array_metrics"].items():
            self.check_metric_desc(metric)
            self.add_array_metric(obsid, metric, val)

    def add_autocorrelation(
        self, time, antenna_number, antenna_feed_pol, measurement_type, value
    ):
        """
        Add new autocorrelation column to the M&C database.

        Parameters
        ----------
        time : astropy time object
            Astropy time object based on timestamp of autocorrelation.
        antenna_number : int
            Antenna Number
        antenna_feed_pol : str
            Feed polarization, either 'e' or 'n'.
        measurement_type : str
            The type of measurement type of the autocorrelation.
            Currently supports: 'median'.
        value : float
            The median autocorrelation value as a float.
        """
        self.add(
            HeraAuto.create(
                time, antenna_number, antenna_feed_pol, measurement_type, value
            )
        )

    def add_autocorrelation_spectrum(
        self, time, antenna_number, antenna_feed_pol, spectrum
    ):
        """
        Add new autocorrelation spectrum column to the M&C database.

        Parameters
        ----------
        time : astropy time object
            Astropy time object based on timestamp of autocorrelation.
        antenna_number : int
            Antenna Number
        antenna_feed_pol : str
            Feed polarization, either 'e' or 'n'.
        spectrum : array-like of float
            The autocorrelation spectrum.

        """
        self.add(
            HeraAutoSpectrum.create(time, antenna_number, antenna_feed_pol, spectrum)
        )

    def add_autocorrelations_from_redis(
        self,
        hera_autos_dict=None,
        testing=False,
        redishost=corr.DEFAULT_REDIS_ADDRESS,
        measurement_type=None,
    ):
        """
        Get current autocorrelations from redis and insert into M&C.

        Parameters
        ----------
        hera_autos_dict : dict, optional
            A dict containing info as in the return dict from
            `_get_autos_from_redis()` for testing purposes. If None,
            `_get_autos_from_redis()` is called.
        testing : bool
            If true, do not add records to database, instead return list of HeraAuto
            and HeraAutoSpectrum objects.
        redishost : str, optional
            The hostname of the redis server to connect to if hera_autos_dict is None.
            Defaults to correlator.DEFAULT_REDIS_ADDRESS.
        measurement_type : str, optional
            The type of measurement to take from the autos.
            Available choices are: ['median']
            If None, defaults to median.

        Returns
        -------
        list of HeraAuto and HeraAutoSpectrum objects, optional
            If testing is True, returns the list of objects rather than adding
            them to the database.

        """
        if hera_autos_dict is None:
            hera_autos_dict = _get_autos_from_redis(redishost=redishost)
        if measurement_type is None:
            measurement_type = "median"

        hera_auto_list = []
        hera_auto_spectrum_list = []

        timestamp_jd = hera_autos_dict.pop("timestamp", None)

        if timestamp_jd is None:
            raise ValueError(
                "No timestamp found in hera_autos_dict. "
                "A timestamp (in JD) must be present to log autocorelations."
            )
        time = Time(timestamp_jd, format="jd")

        for antpol, auto in hera_autos_dict.items():
            ant, pol = antpol.split(":")
            ant = int(ant)
            auto_spectrum = np.asarray(auto)

            auto_val = measurement_func_dict[measurement_type](auto_spectrum).item()

            hera_auto_list.append(
                HeraAuto.create(time, ant, pol, measurement_type, auto_val)
            )

            hera_auto_spectrum_list.append(
                HeraAutoSpectrum.create(time, ant, pol, auto_spectrum)
            )

        if testing:
            return hera_auto_list + hera_auto_spectrum_list
        else:
            self._insert_ignoring_duplicates(HeraAuto, hera_auto_list)
            self._insert_ignoring_duplicates(HeraAutoSpectrum, hera_auto_spectrum_list)

    def get_autocorrelation(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        antenna_number=None,
        feed_pol=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get  autocorrelation record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        antenna_number : int
            antenna number
        feed_pol : string
            Feed polarization, either 'e' or 'n'.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of HeraAuto objects

        """
        return self._time_filter(
            HeraAuto,
            "time",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            filter_column=["antenna_number", "antenna_feed_pol"],
            filter_value=[antenna_number, feed_pol],
            write_to_file=write_to_file,
            filename=filename,
        )

    def get_autocorrelation_spectrum(
        self,
        most_recent=None,
        starttime=None,
        stoptime=None,
        antenna_number=None,
        feed_pol=None,
        write_to_file=False,
        filename=None,
    ):
        """
        Get autocorrelation spectrum record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time.
        If only starttime is set, this method will return the first record(s) after the
        starttime -- again there can be more than one if there are multiple records at
        the same time.  If both most_recent and starttime are set, this method will
        return the most recent record(s) at the starttime, meaning the record with the
        largest time <= starttime -- again there can be more than one if there are
        multiple records at the same time.  If you want a range of times you need to
        set both startime and stoptime.

        Parameters
        ----------
        most_recent : bool
            Option to get the most recent record(s). Defaults to True if starttime is
            None. If both most_recent and starttime are set, get the most recent record
            before the starttime.
        starttime : astropy Time object
            Time to look for records after or, if most_recent is True, time to get the
            get the most recent value for.
        stoptime : astropy Time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.
        antenna_number : int
            antenna number
        feed_pol : string
            Feed polarization, either 'e' or 'n'.
        write_to_file : bool
            Option to write records to a CSV file.
        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False.

        Returns
        -------
        list of HeraAutoSpectrum objects

        """
        return self._time_filter(
            HeraAutoSpectrum,
            "time",
            most_recent=most_recent,
            starttime=starttime,
            stoptime=stoptime,
            filter_column=["antenna_number", "antenna_feed_pol"],
            filter_value=[antenna_number, feed_pol],
            write_to_file=write_to_file,
            filename=filename,
        )
