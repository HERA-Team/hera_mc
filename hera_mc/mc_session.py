# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

from __future__ import absolute_import, division, print_function

import os
import numpy as np
import warnings
import six
from math import floor

from sqlalchemy import desc, asc
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import func
from astropy.time import Time, TimeDelta

from .utils import get_iterable

"""
Primary session object which handles most DB queries.

See INSTALL.md in the Git repository for instructions on how to initialize
your database and configure M&C to find it.
"""


class MCSession(Session):

    def __enter__(self):
        return self

    def __exit__(self, etype, evalue, etb):
        if etype is not None:
            self.rollback()  # exception raised
        else:
            self.commit()  # success
        self.close()
        return False  # propagate exception if any occurred

    def get_current_db_time(self):
        '''
        A method to get the current time according to the database

        Returns:
        --------
        current database time as an astropy time object
        '''
        db_timestamp = self.execute(func.current_timestamp()).scalar()

        # convert to astropy time object
        db_time = Time(db_timestamp)
        return db_time

    def add_corr_obj(self):
        import hera_corr_cm

        if not hasattr(self, 'corr_obj'):
            self.corr_obj = hera_corr_cm.HeraCorrCM()

    def _write_query_to_file(self, query, table_class, filename=None):
        '''
        A helper method to write out query results to a file.

        Parameters:
        table_class: class
            Class specifying a table to query.

        query: query object
            query to write results of to filename

        filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        '''
        if filename is None:
            table_name = getattr(table_class, '__tablename__')
            filename = table_name + '.csv'

        column_names = [col.name for col in (getattr(getattr(table_class, '__table__'), '_columns'))]
        with open(filename, 'w') as the_file:
            # write header
            the_file.write(', '.join(column_names) + '\n')

            # write rows
            for item in query:
                item_vals = [str(getattr(item, col)) for col in column_names]
                the_file.write(', '.join(item_vals) + '\n')

    def _time_filter(self, table_class, time_column, most_recent=None,
                     starttime=None, stoptime=None,
                     filter_column=None, filter_value=None,
                     write_to_file=False, filename=None):
        '''
        A helper method to fiter entries by time. Used by most get methods
        on this object.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time. If starttime
        is set but stoptime is not, this method will return the first record(s)
        after the starttime -- again there can be more than one if there are
        multiple records at the same time. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        Parameters:
        table_class: class
            Class specifying a table to query.

        time_column: string
            column name holding the time to filter on.

        most_recent: boolean
            if True, get most recent record(s). Defaults to True if starttime is None.

        starttime: astropy time object
            Time to look for records after. Ignored if most_recent is True,
            required if most_recent is False.

        stoptime: astropy time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record(s) after starttime will be returned
            (can be more than one record if multiple records share the same time).
            Ignored if most_recent is True.

        filter_column: string
            column name to use as an additional filter (often a part of the primary key)

        filter_value: type coresponding to filter_column, usually a string
            value to require that the filter_column is equal to

        write_to_file: boolean
            Option to write records to a CSV file

        filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        --------
        if write_to_file is False: list of objects that match the filtering
        '''
        if starttime is None and most_recent is None:
            most_recent = True

        if not isinstance(most_recent, (type(None), bool)):
            raise TypeError('most_recent must be None or a boolean')

        if not most_recent:
            if starttime is None:
                raise ValueError('starttime must be specified if most_recent is False')
            if not isinstance(starttime, Time):
                raise ValueError('starttime must be an astropy time object. '
                                 'value was: {t}'.format(t=starttime))

        if stoptime is not None:
            if not isinstance(stoptime, Time):
                raise ValueError('stoptime must be an astropy time object. '
                                 'value was: {t}'.format(t=stoptime))

        time_attr = getattr(table_class, time_column)
        if filter_value is not None:
            filter_attr = getattr(table_class, filter_column)

        query = self.query(table_class)
        if filter_value is not None:
            query = query.filter(filter_attr == filter_value)

        if most_recent or stoptime is None:
            if most_recent:
                current_time = Time.now()
                # get most recent row
                first_query = query.filter(time_attr <= current_time.gps).order_by(desc(time_attr)).limit(1)
            else:
                # get first row after starttime
                first_query = query.filter(time_attr >= starttime.gps).order_by(asc(time_attr)).limit(1)

            # get the time of the first row
            first_result = first_query.all()
            if len(first_result) < 1:
                query = first_query
            else:
                first_time = getattr(first_result[0], time_column)
                # then get all results at that time
                query = query.filter(time_attr == first_time)
                if filter_value is not None:
                    query = query.order_by(asc(filter_attr))

        else:
            query = query.filter(time_attr.between(starttime.gps, stoptime.gps))
            query = query.order_by(time_attr)
            if filter_value is not None:
                query = query.order_by(asc(filter_attr))

        if write_to_file:
            self._write_query_to_file(query, table_class, filename=filename)
        else:
            return query.all()

    def _insert_ignoring_duplicates(self, table_class, obj_list, update=False):
        """
        If the current database is PostgreSQL, this function will use a
        special insertion method that will ignore or update records that are redundant
        with ones already in the database. This makes it convenient to sample
        the certain data (especially redis data) densely on qmaster or to
        update an existing record.

        Parameters
        ----------
        table_class : class
            Class specifying a table to insert into.
        obj_list : list of objects
            list of objects (of class table_class) to insert into the table.
        update : bool
            If true, update the existing record with the new data, otherwise do
            nothing (which is appropriate if the data is the same because of
            dense sampling).
        """
        if self.bind.dialect.name == 'postgresql':
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
                    # create dict of columns to update (everything other than the primary keys)
                    update_dict = {}
                    for col, val in six.iteritems(values):
                        if col not in ies:
                            update_dict[col] = val

                    # The special PostgreSQL insert statement lets us update
                    # existing rows via `ON CONFLICT ... DO UPDATE` syntax.
                    stmt = insert(table_class).values(**values).on_conflict_do_update(
                        index_elements=ies, set_=update_dict)
                else:
                    # The special PostgreSQL insert statement lets us ignore
                    # existing rows via `ON CONFLICT ... DO NOTHING` syntax.
                    stmt = insert(table_class).values(**values).on_conflict_do_nothing(
                        index_elements=ies)
                conn.execute(stmt)
        else:  # pragma: no cover
            # Generic approach:
            for obj in obj_list:
                self.add(obj)

    def add_obs(self, starttime, stoptime, obsid):
        """
        Add a new observation to the M&C database.

        Parameters:
        ------------
        starttime: astropy time object
            observation starttime
        stoptime: astropy time object
            observation stoptime
        obsid: long integer
            observation identification number
        """
        from .observations import Observation
        from . import geo_handling

        h = geo_handling.Handling(session=self)
        hera_cofa = h.cofa()[0]

        self.add(Observation.create(starttime, stoptime, obsid, hera_cofa))

    def get_obs(self, obsid=None):
        """
        Get observation(s) from the M&C database.

        Parameters:
        ------------
        obsid: long integer
            observation identification number, generally the gps second
            corresponding to the observation start time. If not obsid is None,
            all obsids will be returned.

        Returns:
        --------
        list of Observation objects
        """
        from .observations import Observation

        if obsid is None:
            obs_list = self.query(Observation).all()
        else:
            obs_list = self.query(Observation).filter(Observation.obsid == obsid).all()

        return obs_list

    def get_obs_by_time(self, most_recent=None, starttime=None,
                        stoptime=None, write_to_file=False, filename=None):
        """
        Get observation(s) from the M&C database.

        Default behavior is to return the most recent record. If starttime
        is set but stoptime is not, this method will return the first record
        after the starttime. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        Parameters:
        ------------
        most_recent: boolean
            if True, get most recent record. Defaults to True if starttime is None.

        starttime: astropy time object
            Time to look for records after. Ignored if most_recent is True,
            required if most_recent is False.

        stoptime: astropy time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        write_to_file: boolean
            Option to write records to a CSV file

        filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        --------
        list of Observation objects
        """
        from .observations import Observation

        return self._time_filter(Observation, 'obsid', most_recent=most_recent,
                                 starttime=starttime, stoptime=stoptime,
                                 write_to_file=write_to_file, filename=filename)

    def add_server_status(self, subsystem, hostname, ip_address, system_time, num_cores,
                          cpu_load_pct, uptime_days, memory_used_pct, memory_size_gb,
                          disk_space_pct, disk_size_gb, network_bandwidth_mbs=None):
        """
        Add a new subsystem server_status to the M&C database.

        Parameters:
        ------------
        subsystem: string
            name of subsystem. Must be one of ['rtp', 'lib']
        hostname:
            name of server
        ip_address:
            IP address of server
        system_time:
            time report sent by server
        num_cores:
            number of cores on server
        cpu_load_pct:
            CPU load percent = total load / num_cores, 5 min average
        uptime_days:
            server uptime in decimal days
        memory_used_pct:
            Percent of memory used, 5 min average
        memory_size_gb:
            Amount of memory on server in GB
        disk_space_pct:
            Percent of disk used
        disk_size_gb:
            Amount of disk space on server in GB
        network_bandwidth_mbs:
            Network bandwidth in MB/s, 5 min average. Can be null if not applicable
        """
        if subsystem == 'rtp':
            from .rtp import RTPServerStatus as ServerStatus
        elif subsystem == 'lib':
            from .librarian import LibServerStatus as ServerStatus
        else:
            raise ValueError('subsystem must be one of: ["rtp", "lib"]')

        db_time = self.get_current_db_time()

        self.add(ServerStatus.create(db_time, hostname, ip_address, system_time, num_cores,
                                     cpu_load_pct, uptime_days, memory_used_pct,
                                     memory_size_gb, disk_space_pct, disk_size_gb,
                                     network_bandwidth_mbs=network_bandwidth_mbs))

    def get_server_status(self, subsystem, most_recent=None,
                          starttime=None, stoptime=None, hostname=None,
                          write_to_file=False, filename=None):
        """
        Get subsystem server_status record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time. If starttime
        is set but stoptime is not, this method will return the first record(s)
        after the starttime -- again there can be more than one if there are
        multiple records at the same time. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        Parameters:
        ------------
        subsystem: string
            name of subsystem. Must be one of ['rtp', 'lib']

        most_recent: boolean
            if True, get most recent record. Defaults to True if starttime is None.

        starttime: astropy time object
            Time to look for records after. Ignored if most_recent is True,
            required if most_recent is False.

        stoptime: astropy time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        hostname: string
            hostname to get records for. If none, all hostnames will be included.

        write_to_file: boolean
            Option to write records to a CSV file

        filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        --------
        list of ServerStatus objects
        """
        if subsystem == 'rtp':
            from .rtp import RTPServerStatus as ServerStatus
        elif subsystem is 'lib':
            from .librarian import LibServerStatus as ServerStatus
        else:
            raise ValueError('subsystem must be one of: ["rtp", "lib"]')

        return self._time_filter(ServerStatus, 'mc_time', most_recent=most_recent,
                                 starttime=starttime, stoptime=stoptime,
                                 filter_column='hostname', filter_value=hostname,
                                 write_to_file=write_to_file, filename=filename)

    def get_rtp_server_status(self, most_recent=None, starttime=None, stoptime=None,
                              hostname=None, write_to_file=False, filename=None):
        """
        Get rtp_server_status record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time. If starttime
        is set but stoptime is not, this method will return the first record(s)
        after the starttime -- again there can be more than one if there are
        multiple records at the same time. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        Parameters:
        ------------
        most_recent: boolean
            if True, get most recent record. Defaults to True if starttime is None.

        starttime: astropy time object
            Time to look for records after. Ignored if most_recent is True,
            required if most_recent is False.

        stoptime: astropy time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        hostname: string
            hostname to get records for. If none, all hostnames will be included.

        write_to_file: boolean
            Option to write records to a CSV file

        filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        --------
        list of RTPServerStatus objects
        """
        return self.get_server_status('rtp', most_recent=None,
                                      starttime=None, stoptime=None, hostname=None,
                                      write_to_file=False, filename=None)

    def get_librarian_server_status(self, most_recent=None, starttime=None, stoptime=None,
                                    hostname=None, write_to_file=False, filename=None):
        """
        Get librarian_server_status record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time. If starttime
        is set but stoptime is not, this method will return the first record(s)
        after the starttime -- again there can be more than one if there are
        multiple records at the same time. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        Parameters:
        ------------
        most_recent: boolean
            if True, get most recent record. Defaults to True if starttime is None.

        starttime: astropy time object
            Time to look for records after. Ignored if most_recent is True,
            required if most_recent is False.

        stoptime: astropy time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        hostname: string
            hostname to get records for. If none, all hostnames will be included.

        write_to_file: boolean
            Option to write records to a CSV file

        filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        --------
        list of LibServerStatus objects
        """
        return self.get_server_status('lib', most_recent=None,
                                      starttime=None, stoptime=None, hostname=None,
                                      write_to_file=False, filename=None)

    def add_subsystem_error(self, time, subsystem, severity, log, testing=False):
        """
        Add a new subsystem_error to the M&C database.

        Parameters:
        ------------
        time : astropy time object
            time of this error report
        subsystem : str
            name of subsystem with error
        severity : int
            integer indicating severity level, 1 is most severe
        log : str
            error message or log file name (TBD)
        testing : bool
            Option to just return the objects rather than adding them to the DB.
        """
        from .subsystem_error import SubsystemError

        db_time = self.get_current_db_time()

        error_obj = SubsystemError.create(db_time, time, subsystem, severity, log)

        if testing:
            return error_obj

        self.add(error_obj)

    def get_subsystem_error(self, most_recent=None, starttime=None,
                            stoptime=None, subsystem=None,
                            write_to_file=False, filename=None):
        """
        Get subsystem server_status record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time. If starttime
        is set but stoptime is not, this method will return the first record(s)
        after the starttime -- again there can be more than one if there are
        multiple records at the same time. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        Parameters:
        ------------
        most_recent: boolean
            if True, get most recent record. Defaults to True if starttime is None.

        starttime: astropy time object
            Time to look for records after. Ignored if most_recent is True,
            required if most_recent is False.

        stoptime: astropy time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        subsystem: string
            subsystem to get records for. If none, all subsystems will be included.

        write_to_file: boolean
            Option to write records to a CSV file

        filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        --------
        list of SubsystemError objects
        """
        from .subsystem_error import SubsystemError

        return self._time_filter(SubsystemError, 'time', most_recent=most_recent,
                                 starttime=starttime, stoptime=stoptime,
                                 filter_column='subsystem', filter_value=subsystem,
                                 write_to_file=write_to_file, filename=filename)

    def add_daemon_status(self, name, hostname, time, status, testing=False):
        """
        Add a new daemon_status to the M&C database.

        If the current database is PostgreSQL, this function will use a
        special insertion method that will update records that are redundant
        with ones already in the database.

        Parameters:
        ------------
        name : str
            Name of the daemon
        hostname : str
            Name of server where daemon is running
        time : astropy time object
            Time of this status report, updated on every iteration of the daemon
        status : str
            Status, one of the values in status_list.
        testing : bool
            Option to just return the objects rather than adding them to the DB.
        """
        from .daemon_status import DaemonStatus

        daemon_status_obj = DaemonStatus.create(name, hostname, time, status)

        if testing:
            return daemon_status_obj

        self._insert_ignoring_duplicates(DaemonStatus, [daemon_status_obj],
                                         update=True)

    def get_daemon_status(self, most_recent=None, starttime=None,
                          stoptime=None, daemon_name=None,
                          write_to_file=False, filename=None):
        """
        Get daemon_status record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time. If starttime
        is set but stoptime is not, this method will return the first record(s)
        after the starttime -- again there can be more than one if there are
        multiple records at the same time. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        Parameters:
        ------------
        most_recent : bool
            if True, get most recent record. Defaults to True if starttime is None.

        starttime : astropy time object
            Time to look for records after. Ignored if most_recent is True,
            required if most_recent is False.

        stoptime : astropy time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        daemon_name : str
            Name of daemon to get records for. If none, all daemons will be included.

        write_to_file : bool
            Option to write records to a CSV file

        filename : str
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        --------
        list of SubsystemError objects
        """
        from .daemon_status import DaemonStatus

        return self._time_filter(DaemonStatus, 'time', most_recent=most_recent,
                                 starttime=starttime, stoptime=stoptime,
                                 filter_column='name', filter_value=daemon_name,
                                 write_to_file=write_to_file, filename=filename)

    def add_lib_status(self, time, num_files, data_volume_gb, free_space_gb,
                       upload_min_elapsed, num_processes, git_version, git_hash):
        """
        Add a new lib_status object.

        Parameters:
        ------------
        time: astropy time object
            time of this status
        num_files: integer
            number of files in librarian
        data_volume_gb: float
            data volume in GB
        free_space_gb: float
            free space in GB
        upload_min_elapsed: float
            minutes since last file upload
        num_processes: integer
            number of background tasks running
        git_version: string
            Librarian git version
        git_hash: string
            Librarian git hash
        """
        from .librarian import LibStatus

        self.add(LibStatus.create(time, num_files, data_volume_gb,
                                  free_space_gb, upload_min_elapsed,
                                  num_processes, git_version, git_hash))

    def get_lib_status(self, most_recent=None, starttime=None, stoptime=None,
                       write_to_file=False, filename=None):
        """
        Get lib_status record(s) from the M&C database.

        Default behavior is to return the most recent record. If starttime
        is set but stoptime is not, this method will return the first record
        after the starttime. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        Parameters:
        ------------
        most_recent: boolean
            if True, get most recent record. Defaults to True if starttime is None.

        starttime: astropy time object
            Time to look for records after. Ignored if most_recent is True,
            required if most_recent is False.

        stoptime: astropy time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        write_to_file: boolean
            Option to write records to a CSV file

        filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        --------
        list of LibStatus objects
        """
        from .librarian import LibStatus

        return self._time_filter(LibStatus, 'time', most_recent=most_recent,
                                 starttime=starttime, stoptime=stoptime,
                                 write_to_file=write_to_file, filename=filename)

    def add_lib_raid_status(self, time, hostname, num_disks, info):
        """
        Add a new lib_raid_status object.

        Parameters:
        ------------
        time: astropy time object
            time of this status
        hostname: string
            name of RAID server
        num_disks: integer
            number of disks in RAID server
        info: string
            TBD info from megaraid controller
        """
        from .librarian import LibRAIDStatus

        self.add(LibRAIDStatus.create(time, hostname, num_disks, info))

    def get_lib_raid_status(self, most_recent=None, starttime=None, stoptime=None,
                            hostname=None, write_to_file=False, filename=None):
        """
        Get lib_raid_status record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time. If starttime
        is set but stoptime is not, this method will return the first record(s)
        after the starttime -- again there can be more than one if there are
        multiple records at the same time. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        Parameters:
        ------------
        most_recent: boolean
            if True, get most recent record. Defaults to True if starttime is None.

        starttime: astropy time object
            Time to look for records after. Ignored if most_recent is True,
            required if most_recent is False.

        stoptime: astropy time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        hostname: string
            RAID hostname to get records for. If none, all hostnames will be included.

        write_to_file: boolean
            Option to write records to a CSV file

        filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        --------
        list of LibRAIDStatus objects
        """
        from .librarian import LibRAIDStatus

        return self._time_filter(LibRAIDStatus, 'time', most_recent=most_recent,
                                 starttime=starttime, stoptime=stoptime,
                                 filter_column='hostname', filter_value=hostname,
                                 write_to_file=write_to_file, filename=filename)

    def add_lib_raid_error(self, time, hostname, disk, log):
        """
        Add a new lib_raid_error object.

        Parameters:
        ------------
        time: astropy time object
            time of this error
        hostname: string
            name of RAID server with error
        disk: string
            name of disk with error
        log: string
            error message or log file name (TBD)
        """
        from .librarian import LibRAIDErrors

        self.add(LibRAIDErrors.create(time, hostname, disk, log))

    def get_lib_raid_error(self, most_recent=None, starttime=None, stoptime=None,
                           hostname=None, write_to_file=False, filename=None):
        """
        Get lib_raid_error record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time. If starttime
        is set but stoptime is not, this method will return the first record(s)
        after the starttime -- again there can be more than one if there are
        multiple records at the same time. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        Parameters:
        ------------
        most_recent: boolean
            if True, get most recent record. Defaults to True if starttime is None.

        starttime: astropy time object
            Time to look for records after. Ignored if most_recent is True,
            required if most_recent is False.

        stoptime: astropy time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        hostname: string
            RAID hostname to get records for. If none, all hostnames will be included.

        write_to_file: boolean
            Option to write records to a CSV file

        filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        --------
        list of LibRAIDErrors objects
        """
        from .librarian import LibRAIDErrors

        return self._time_filter(LibRAIDErrors, 'time', most_recent=most_recent,
                                 starttime=starttime, stoptime=stoptime,
                                 filter_column='hostname', filter_value=hostname,
                                 write_to_file=write_to_file, filename=filename)

    def add_lib_remote_status(self, time, remote_name, ping_time,
                              num_file_uploads, bandwidth_mbs):
        """
        Add a new lib_remote_status object.

        Parameters:
        ------------
        time: astropy time object
            time of this status
        remote_name: string
            name of remote server
        ping_time: float
            ping time to remote in seconds
        num_file_uploads: integer
            number of file uploads to remote in last 15 minutes
        bandwidth_mbs: float
            bandwidth to remote in Mb/s, 15 minute average
        """
        from .librarian import LibRemoteStatus

        self.add(LibRemoteStatus.create(time, remote_name, ping_time,
                                        num_file_uploads, bandwidth_mbs))

    def get_lib_remote_status(self, most_recent=None, starttime=None,
                              stoptime=None, remote_name=None,
                              write_to_file=False, filename=None):
        """
        Get lib_remote_status record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time. If starttime
        is set but stoptime is not, this method will return the first record(s)
        after the starttime -- again there can be more than one if there are
        multiple records at the same time. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        Parameters:
        ------------
        most_recent: boolean
            if True, get most recent record. Defaults to True if starttime is None.

        starttime: astropy time object
            Time to look for records after. Ignored if most_recent is True,
            required if most_recent is False.

        stoptime: astropy time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        remote_name: string
            Name of remote librarian to get records for. If none, all
            remote_names will be included.

        write_to_file: boolean
            Option to write records to a CSV file

        filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        --------
        list of LibRemoteStatus objects
        """
        from .librarian import LibRemoteStatus

        return self._time_filter(LibRemoteStatus, 'time', most_recent=most_recent,
                                 starttime=starttime, stoptime=stoptime,
                                 filter_column='remote_name', filter_value=remote_name,
                                 write_to_file=write_to_file, filename=filename)

    def add_lib_file(self, filename, obsid, time, size_gb):
        """
        Add a new lib_file row.

        Parameters:
        ------------
        filename: string
            name of file created
        obsid: long or None
            optional observation obsid (Foreign key into Observation)
        time: astropy time object
            time file was created
        size_gb: float
            file size in GB
        """
        from .librarian import LibFiles

        self.add(LibFiles.create(filename, obsid, time, size_gb))

    def get_lib_files(self, filename=None, obsid=None, most_recent=None,
                      starttime=None, stoptime=None, write_to_file=False,
                      write_filename=None):
        """
        Get lib_files record(s) from the M&C database.

        If filename is provided, all other optional keywords are ignored.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time. If starttime
        is set but stoptime is not, this method will return the first record(s)
        after the starttime -- again there can be more than one if there are
        multiple records at the same time. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        Parameters:
        ------------
        filename: string
            filename to get records for.

        obsid: long
            obsid to get records for. If starttime and most_recent are both None,
            all files for this obsid will be returned.

        most_recent: boolean
            if True, get most recent record.

        starttime: astropy time object
            Time to look for records after. Ignored if most_recent is True.

        stoptime: astropy time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        write_to_file: boolean
            Option to write records to a CSV file

        write_filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        --------
        list of LibFiles objects
        """
        from .librarian import LibFiles

        if filename is not None:
            query = self.query(LibFiles).filter(
                LibFiles.filename == filename)
        else:
            if most_recent is not None or starttime is not None:
                return self._time_filter(LibFiles, 'time', most_recent=most_recent,
                                         starttime=starttime, stoptime=stoptime,
                                         filter_column='obsid', filter_value=obsid,
                                         write_to_file=write_to_file, filename=write_filename)
            else:
                if obsid is not None:
                    query = self.query(LibFiles).filter(
                        LibFiles.obsid == obsid)
                else:
                    query = self.query(LibFiles)

        if write_to_file:
            self._write_query_to_file(query, LibFiles, filename=write_filename)
        else:
            return query.all()

    def add_rtp_status(self, time, status, event_min_elapsed, num_processes,
                       restart_hours_elapsed):
        """
        Add a new rtp_status object.

        Parameters:
        ------------
        time: astropy time object
            time of this status
        status: string
            status (options TBD)
        event_min_elapsed: float
            minutes since last event
        num_processes: integer
            number of processes running
        restart_hours_elapsed: float
            hours since last restart
        """
        from .rtp import RTPStatus

        self.add(RTPStatus.create(time, status, event_min_elapsed, num_processes,
                                  restart_hours_elapsed))

    def get_rtp_status(self, most_recent=None, starttime=None, stoptime=None,
                       write_to_file=False, filename=None):
        """
        Get rtp_status record(s) from the M&C database.

        Default behavior is to return the most recent record. If starttime
        is set but stoptime is not, this method will return the first record
        after the starttime. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        Parameters:
        ------------
        most_recent: boolean
            if True, get most recent record. Defaults to True if starttime is None.

        starttime: astropy time object
            Time to look for records after. Ignored if most_recent is True,
            required if most_recent is False.

        stoptime: astropy time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        write_to_file: boolean
            Option to write records to a CSV file

        filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        --------
        list of RTPStatus objects
        """
        from .rtp import RTPStatus

        return self._time_filter(RTPStatus, 'time', most_recent=most_recent,
                                 starttime=starttime, stoptime=stoptime,
                                 write_to_file=write_to_file, filename=filename)

    def add_rtp_process_event(self, time, obsid, event):
        """
        Add a new rtp_process_event row.

        Parameters:
        ------------
        time: astropy time object
            time of event
        obsid: long
            observation obsid (Foreign key into observation)
        event: string
            must be one of ["queued", "started", "finished", "error"]
        """
        from .rtp import RTPProcessEvent

        self.add(RTPProcessEvent.create(time, obsid, event))

    def get_rtp_process_event(self, most_recent=None, starttime=None,
                              stoptime=None, obsid=None,
                              write_to_file=False, filename=None):
        """
        Get rtp_process_event record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time. If starttime
        is set but stoptime is not, this method will return the first record(s)
        after the starttime -- again there can be more than one if there are
        multiple records at the same time. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        Parameters:
        ------------
        most_recent: boolean
            if True, get most recent record. Defaults to True if starttime is None.

        starttime: astropy time object
            Time to look for records after. Ignored if most_recent is True,
            required if most_recent is False.

        stoptime: astropy time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        obsid: long
            obsid to get records for. If none, all obsid will be included.

        write_to_file: boolean
            Option to write records to a CSV file

        filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        --------
        list of RTPProcessEvent objects
        """
        from .rtp import RTPProcessEvent

        return self._time_filter(RTPProcessEvent, 'time', most_recent=most_recent,
                                 starttime=starttime, stoptime=stoptime,
                                 filter_column='obsid', filter_value=obsid,
                                 write_to_file=write_to_file, filename=filename)

    def add_rtp_process_record(self, time, obsid, pipeline_list, rtp_git_version,
                               rtp_git_hash, hera_qm_git_version, hera_qm_git_hash,
                               hera_cal_git_version, hera_cal_git_hash,
                               pyuvdata_git_version, pyuvdata_git_hash):
        """
        Add a new rtp_process_record row.

        Parameters:
        ------------
        time: astropy time object
            time of event
        obsid: long
            observation obsid (Foreign key into observation)
        pipeline_list: string
            concatentated list of RTP tasks
        rtp_git_version: string
            RTP git version
        rtp_git_hash: string
            RTP git hash
        hera_qm_git_version: string
            hera_qm git version
        hera_qm_git_hash: string
            hera_qm git hash
        hera_cal_git_version: string
            hera_cal git version
        hera_cal_git_hash: string
            hera_cal git hash
        pyuvdata_git_version: string
            pyuvdata git version
        pyuvdata_git_hash: string
            pyuvdata git hash
        """
        from .rtp import RTPProcessRecord

        self.add(RTPProcessRecord.create(time, obsid, pipeline_list,
                                         rtp_git_version, rtp_git_hash,
                                         hera_qm_git_version, hera_qm_git_hash,
                                         hera_cal_git_version, hera_cal_git_hash,
                                         pyuvdata_git_version, pyuvdata_git_hash))

    def get_rtp_process_record(self, most_recent=None, starttime=None,
                               stoptime=None, obsid=None, write_to_file=False,
                               filename=None):
        """
        Get rtp_process_record record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time. If starttime
        is set but stoptime is not, this method will return the first record(s)
        after the starttime -- again there can be more than one if there are
        multiple records at the same time. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        Parameters:
        ------------
        most_recent: boolean
            if True, get most recent record. Defaults to True if starttime is None.

        starttime: astropy time object
            Time to look for records after. Ignored if most_recent is True,
            required if most_recent is False.

        stoptime: astropy time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        obsid: long
            obsid to get records for. If none, all obsid will be included.

        write_to_file: boolean
            Option to write records to a CSV file

        filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        --------
        list of RTPProcessEvent objects
        """
        from .rtp import RTPProcessRecord

        return self._time_filter(RTPProcessRecord, 'time', most_recent=most_recent,
                                 starttime=starttime, stoptime=stoptime,
                                 filter_column='obsid', filter_value=obsid,
                                 write_to_file=write_to_file, filename=filename)

    def add_rtp_task_resource_record(self, obsid, task_name, start_time, stop_time,
                                     max_memory=None, avg_cpu_load=None):
        """
        Add a new rtp_task_resource_record row

        Parameters:
        ------------
        obsid: long
            observation obsid (Foreign key into observation)
        task_name: string
            name of the task (e.g., OMNICAL)
        start_time: astropy time object
            time of task start
        stop_time: astropy time object
            time of task end
        max_memory: float
            maximum amount of memory used by the task, in MB
        avg_cpu_load: float
            average number of CPUs used by task
        """
        from .rtp import RTPTaskResourceRecord

        self.add(RTPTaskResourceRecord.create(obsid, task_name, start_time, stop_time,
                                              max_memory, avg_cpu_load))

    def get_rtp_task_resource_record(self, most_recent=None, starttime=None,
                                     stoptime=None, obsid=None, task_name=None,
                                     write_to_file=False, filename=None):
        """
        Get rtp_task_resource_record from the M&C database.

        If both obsid and task_name are set, all other keywords are ignored.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time. If starttime
        is set but stoptime is not, this method will return the first record(s)
        after the starttime -- again there can be more than one if there are
        multiple records at the same time. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        At least one of obsid, starttime or most_recent must be specified.

        Parameters:
        ------------
        most_recent: boolean
            if True, get most recent record. Defaults to True if starttime,
            obsid and task_name are all None.

        starttime: astropy time object
            Time to look for records after; applies to start_time column.
            Ignored if both obsid and task_name are set or if most_recent is True.

        stoptime: astropy time object
            last time to get records for, only used if starttime is used.
            If none, only the first record after starttime will be returned.

        obsid: long
            obsid to get records for. If none, all obsids will be included.

        task_name: string
            task_name to get records for. If none, all tasks will be included.

        write_to_file: boolean
            Option to write records to a CSV file

        filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        -----------
        list of RTPTaskResourceRecord objects

        """
        from .rtp import RTPTaskResourceRecord

        if obsid is None and starttime is None:
            if most_recent is None:
                most_recent = True
            elif most_recent is False:
                raise ValueError('At least one of obsid, starttime or '
                                 'most_recent must be specified.')

        if task_name is None:
            if most_recent is True or starttime is not None:
                return self._time_filter(RTPTaskResourceRecord, 'start_time',
                                         most_recent=most_recent, starttime=starttime,
                                         stoptime=stoptime, filter_column='obsid',
                                         filter_value=obsid,
                                         write_to_file=write_to_file, filename=filename)
            elif obsid is not None:
                return self.query(RTPTaskResourceRecord).filter(
                    RTPTaskResourceRecord.obsid == obsid).all()

        elif obsid is None:
            return self._time_filter(RTPTaskResourceRecord, 'start_time',
                                     most_recent=most_recent, starttime=starttime,
                                     stoptime=stoptime, filter_column='task_name',
                                     filter_value=task_name,
                                     write_to_file=write_to_file, filename=filename)
        else:
            query = self.query(RTPTaskResourceRecord).filter(
                RTPTaskResourceRecord.obsid == obsid,
                RTPTaskResourceRecord.task_name == task_name)

            if write_to_file:
                self._write_query_to_file(query, RTPTaskResourceRecord, filename=filename)

            else:
                return query.all()

    def add_weather_data(self, time, variable, value):
        """
        Add new weather data to the M&C database.

        Parameters:
        ------------
        time: astropy time object
            astropy time object based on a timestamp from the katportal sensor.
        variable: string
            must be a key in weather.weather_sensor_dict
        value: float
            value from the sensor associated with the variable
        """
        from .weather import WeatherData

        self.add(WeatherData.create(time, variable, value))

    def add_weather_data_from_sensors(self, starttime, stoptime, variables=None):
        """
        Add weather data for a given variable and timespan from KAT sensors.
        This function connects to the meerkat db and grabs the latest data
        using the "create_from_sensors" function.

        Parameters:
        ------------
        starttime: astropy time object
            time to start getting history.
        stoptime: astropy time object
            time to stop getting history.
        variable: string
            variable to get history for. Must be a key in weather.weather_sensor_dict,
            defaults to all keys in weather.weather_sensor_dict
        """
        from .weather import weather_sensor_dict, create_from_sensors
        if variables is not None:
            if isinstance(variables, (list, tuple)):
                for var in variables:
                    if var not in weather_sensor_dict.keys():
                        raise ValueError('variables must be a key in weather_sensor_dict.')
            else:
                if variables not in weather_sensor_dict.keys():
                    raise ValueError('variables must be a key in weather_sensor_dict.')

        weather_data_list = create_from_sensors(starttime, stoptime, variables=variables)
        for obj in weather_data_list:
            self.add(obj)

    def get_weather_data(self, most_recent=None, starttime=None, stoptime=None,
                         variable=None, write_to_file=False, filename=None):
        """
        Get weather_data record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time. If starttime
        is set but stoptime is not, this method will return the first record(s)
        after the starttime -- again there can be more than one if there are
        multiple records at the same time. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        Parameters:
        ------------
        most_recent: boolean
            if True, get most recent record. Defaults to True if starttime is None.

        starttime: astropy time object
            Time to look for records after. Ignored if most_recent is True,
            required if most_recent is False.

        stoptime: astropy time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        variable: string
            Name of variable to get records for, must be a key in weather.weather_sensor_dict.
            If none, all variables will be included.

        write_to_file: boolean
            Option to write records to a CSV file

        filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        --------
        if write_to_file is False: list of WeatherData objects
        """
        from .weather import weather_sensor_dict, WeatherData
        if variable is not None:
            if variable not in weather_sensor_dict.keys():
                raise ValueError('variable must be a key in weather_sensor_dict.')

        return self._time_filter(WeatherData, 'time', most_recent=most_recent,
                                 starttime=starttime, stoptime=stoptime,
                                 filter_column='variable', filter_value=variable,
                                 write_to_file=write_to_file, filename=filename)

    def add_node_sensor_readings(self, time, nodeID, top_sensor_temp, middle_sensor_temp,
                                 bottom_sensor_temp, humidity_sensor_temp, humidity):
        """
        Add new node sensor data to the M&C database.

        Parameters:
        ------------
        time: astropy time object
            astropy time object based on a timestamp reported by node
        nodeID: integer
            node number (integer running from 1 to 30)
        top_sensor_temp: float
            temperature of top sensor reported by node in Celsius
        middle_sensor_temp: float
            temperature of middle sensor reported by node in Celsius
        bottom_sensor_temp: float
            temperature of bottom sensor reported by node in Celsius
        humidity_sensor_temp: float
            temperature of the humidity sensor reported by node in Celsius
        humidity: float
            percent humidity measurement reported by node
        """
        from .node import NodeSensor

        self.add(NodeSensor.create(time, nodeID, top_sensor_temp, middle_sensor_temp,
                                   bottom_sensor_temp, humidity_sensor_temp, humidity))

    def add_node_sensor_readings_from_nodecontrol(self):
        """Get and add node sensor information using a nodeControl object.
        This function connects to the node and gets the latest data using the
        `create_sensor_readings` function.

        If the current database is PostgreSQL, this function will use a
        special insertion method that will ignore records that are redundant
        with ones already in the database. This makes it convenient to sample
        the node sensor data densely on qmaster.

        """
        from .node import create_sensor_readings, NodeSensor

        node_sensor_list = create_sensor_readings()

        self._insert_ignoring_duplicates(NodeSensor, node_sensor_list)

    def get_node_sensor_readings(self, most_recent=None, starttime=None,
                                 stoptime=None, nodeID=None, write_to_file=False,
                                 filename=None):
        """
        Get node_sensor record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time. If starttime
        is set but stoptime is not, this method will return the first record(s)
        after the starttime -- again there can be more than one if there are
        multiple records at the same time. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        Parameters:
        ------------
        most_recent: boolean
            if True, get most recent record. Defaults to True if starttime is None.

        starttime: astropy time object
            Time to look for records after. Ignored if most_recent is True,
            required if most_recent is False.

        stoptime: astropy time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        nodeID: integer
            node number (integer running from 1 to 30)

        write_to_file: boolean
            Option to write records to a CSV file

        filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        --------
        if write_to_file is False: list of NodeSensor objects
        """
        from .node import NodeSensor

        return self._time_filter(NodeSensor, 'time', most_recent=most_recent,
                                 starttime=starttime, stoptime=stoptime,
                                 filter_column='node', filter_value=nodeID,
                                 write_to_file=write_to_file, filename=filename)

    def add_node_power_status(self, time, nodeID, snap_relay_powered, snap0_powered,
                              snap1_powered, snap2_powered, snap3_powered,
                              fem_powered, pam_powered):
        """
        Add new node power status data to the M&C database.

        Parameters:
        ------------
        time: astropy time object
            astropy time object based on a timestamp reported by node
        nodeID: integer
            node number (integer running from 1 to 30)
        snap_relay_powered: boolean
            power status of the snap relay, True=powered
        snap0_powered: boolean
            power status of the SNAP 0 board, True=powered
        snap1_powered: boolean
            power status of the SNAP 1 board, True=powered
        snap2_powered: boolean
            power status of the SNAP 2 board, True=powered
        snap3_powered: boolean
            power status of the SNAP 3 board, True=powered
        fem_powered: boolean
            power status of the FEM, True=powered
        pam_powered: boolean
            power status of the PAM, True=powered
        """
        from .node import NodePowerStatus

        self.add(NodePowerStatus.create(time, nodeID, snap_relay_powered, snap0_powered,
                                        snap1_powered, snap2_powered, snap3_powered,
                                        fem_powered, pam_powered))

    def add_node_power_status_from_nodecontrol(self):
        """Get and add node power status information using a nodeControl object.
        This function connects to the node and gets the latest data using the
        `create_power_status` function.

        If the current database is PostgreSQL, this function will use a
        special insertion method that will ignore records that are redundant
        with ones already in the database. This makes it convenient to sample
        the node power status data densely on qmaster.
        """
        from .node import create_power_status, NodePowerStatus

        node_power_list = create_power_status()

        self._insert_ignoring_duplicates(NodePowerStatus, node_power_list)

    def get_node_power_status(self, most_recent=None, starttime=None, stoptime=None,
                              nodeID=None, write_to_file=False, filename=None):
        """
        Get node power status record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time. If starttime
        is set but stoptime is not, this method will return the first record(s)
        after the starttime -- again there can be more than one if there are
        multiple records at the same time. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        Parameters:
        ------------
        most_recent: boolean
            if True, get most recent record. Defaults to True if starttime is None.

        starttime: astropy time object
            Time to look for records after. Ignored if most_recent is True,
            required if most_recent is False.

        stoptime: astropy time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        nodeID: integer
            node number (integer running from 1 to 30)

        write_to_file: boolean
            Option to write records to a CSV file

        filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        --------
        list of NodePowerStatus objects
        """
        from .node import NodePowerStatus

        return self._time_filter(NodePowerStatus, 'time', most_recent=most_recent,
                                 starttime=starttime, stoptime=stoptime,
                                 filter_column='node', filter_value=nodeID,
                                 write_to_file=write_to_file, filename=filename)

    def node_power_command(self, nodeID, part, command, nodeServerAddress=None,
                           dryrun=False, testing=False):
        """
        Issue a power command (on/off) to a particular node & part.

        Parameters:
        ------------
        nodeID: integer
            node number (integer running from 1 to 30). If the testing keyword is False,
            specifying a node which is not in the array will give a ValueError
        part: string or list of strings
            part name(s) (e.g. fem, snap0) or 'all', allowed values are keys to
            node.power_command_part_dict
        command: string
            'on' or 'off'
        nodeServerAddress: string
            address for node server. Defaults to node.defaultServerAddress
        dryrun: boolean
            if true, just return the list of NodePowerCommand objects, do not
            issue the power commands or log them to the database
        testing: boolean
            if true, do not use anything that requires connection to nodes (implies dry run)
        """
        from .node import NodePowerCommand, power_command_part_dict, get_node_list, defaultServerAddress

        if nodeServerAddress is None:
            nodeServerAddress = defaultServerAddress

        if testing:
            node_list = list(range(1, 31))
            dryrun = True
        else:
            node_list = get_node_list(nodeServerAddress=nodeServerAddress)
        if nodeID not in node_list:
            raise ValueError('node not in list of active nodes: ', node_list)

        if isinstance(part, six.string_types):
            part = [part]
        else:
            # ensure no duplicates
            part = list(set(part))

        if part[0] == 'all':
            part = list(power_command_part_dict.keys())

        if 'snap_relay' in part:
            if command == 'on':
                # move snap_relay to the start of the list (it needs to be powered before the snaps)
                part.remove('snap_relay')
                part.insert(0, 'snap_relay')
            else:
                # make sure all snaps are powered down first
                for partname in list(power_command_part_dict.keys()):
                    if partname.startswith('snap') and partname not in part:
                        part.insert(0, partname)
                # move snap_relay to the end of the list.
                part.remove('snap_relay')
                part.append('snap_relay')
        elif command == 'on':
            # check if any snaps in part. If so, need to power snap_relay first
            for partname in part:
                if partname.startswith('snap'):
                    part.insert(0, 'snap_relay')
                    break

        # Check whether parts are already in desired state. If so, omit them from command.
        # make sure we have most recent power status info
        if not testing:
            self.add_node_power_status_from_nodecontrol()
        # Get recent power status
        starttime = Time.now() - TimeDelta(120, format='sec')
        stoptime = Time.now() + TimeDelta(60, format='sec')
        node_powers = self.get_node_power_status(starttime=starttime, stoptime=stoptime, nodeID=nodeID)
        if len(node_powers) > 0:
            latest_powers = node_powers[-1]
            drop_part = []
            for partname in part:
                if partname not in list(power_command_part_dict.keys()):
                    raise ValueError('part must be one of: ' + ', '.join(list(power_command_part_dict.keys()))
                                     + '. part is actually {}'.format(partname))
                power_status = getattr(latest_powers, partname + '_powered')
                if command == 'on':
                    if power_status:
                        # already on, take it out of the list
                        drop_part.append(partname)
                else:
                    if not power_status:
                        # already off, take it out of the list
                        drop_part.append(partname)
            for partname in drop_part:
                # do this after earlier loop so the list doesn't change during iteration
                part.remove(partname)

        if dryrun:
            command_list = []

        for partname in part:
            command_time = Time.now()
            # create object first: catch any mistakes
            command_obj = NodePowerCommand.create(command_time, nodeID, partname, command)

            if not dryrun:  # pragma: no cover
                import nodeControl

                node_controller = nodeControl.NodeControl(nodeID, serverAddress=nodeServerAddress)
                getattr(node_controller, power_command_part_dict[partname])(command)

                self.add(command_obj)
            else:
                command_list.append(command_obj)

        if dryrun:
            return command_list

    def get_node_power_command(self, most_recent=None, starttime=None,
                               stoptime=None, nodeID=None,
                               write_to_file=False, filename=None):
        """
        Get node power command record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time. If starttime
        is set but stoptime is not, this method will return the first record(s)
        after the starttime -- again there can be more than one if there are
        multiple records at the same time. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        Parameters:
        ------------
        most_recent: boolean
            if True, get most recent record. Defaults to True if starttime is None.

        starttime: astropy time object
            Time to look for records after. Ignored if most_recent is True,
            required if most_recent is False.

        stoptime: astropy time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        nodeID: integer
            node number (integer running from 1 to 30)

        write_to_file: boolean
            Option to write records to a CSV file

        filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        --------
        list of NodePowerCommand objects
        """
        from .node import NodePowerCommand

        return self._time_filter(NodePowerCommand, 'time', most_recent=most_recent,
                                 starttime=starttime, stoptime=stoptime,
                                 filter_column='node', filter_value=nodeID,
                                 write_to_file=write_to_file, filename=filename)

    def add_correlator_control_state(self, time, state_type, state):
        """
        Add new correlator control state data to the M&C database.

        Parameters:
        ------------
        time: astropy time object
            astropy time object based on a timestamp reported by the correlator
        state_type: string
            must be a key in state_dict (e.g. 'taking_data', 'phase_switching', 'noise_diode')
        state: boolean
            is the state_type true or false
        """
        from .correlator import CorrelatorControlState

        self.add(CorrelatorControlState.create(time, state_type, state))

    def get_correlator_control_state(self, most_recent=None, starttime=None,
                                     stoptime=None, state_type=None,
                                     write_to_file=False, filename=None):
        """
        Get correlator control state record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time. If starttime
        is set but stoptime is not, this method will return the first record(s)
        after the starttime -- again there can be more than one if there are
        multiple records at the same time. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        Parameters:
        ------------
        most_recent: boolean
            if True, get most recent record. Defaults to True if starttime is None.

        starttime: astropy time object
            Time to look for records after. Ignored if most_recent is True,
            required if most_recent is False.

        stoptime: astropy time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        state_type: string
            must be a key in correlator.state_dict (e.g. 'taking_data', 'phase_switching', 'noise_diode')

        write_to_file: boolean
            Option to write records to a CSV file

        filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        --------
        list of CorrelatorControlState objects
        """
        from .correlator import CorrelatorControlState

        return self._time_filter(CorrelatorControlState, 'time', most_recent=most_recent,
                                 starttime=starttime, stoptime=stoptime,
                                 filter_column='state_type', filter_value=state_type,
                                 write_to_file=write_to_file, filename=filename)

    def add_correlator_control_state_from_corrcm(self, corr_state_dict=None,
                                                 testing=False):
        """Get and add correlator control state information using a HeraCorrCM object.

        This function connects to the correlator and gets the latest data using the
        `_get_control_state` function. For testing purposes, it can
        optionally accept an input dict instead of connecting to the correlator.

        If the current database is PostgreSQL, this function will use a
        special insertion method that will ignore records that are redundant
        with ones already in the database. This makes it convenient to sample
        the data frequently on qmaster.

        Parameters:
        ------------
        corr_state_dict: dict
            A dict containing info as in the return dict from _get_control_state() for
            testing purposes. If None, _get_control_state() is called. Default: None
        testing: boolean
            If true, don't add a record of it to the database and return the list of
            CorrelatorControlState objects. Default False.

        Returns:
        --------
        Optionally returns the list of CorrelatorControlState objects (if testing is True)

        """
        from .correlator import _get_control_state, CorrelatorControlState

        if corr_state_dict is None:
            self.add_corr_obj()
            corr_state_dict = _get_control_state(corr_cm=self.corr_obj)

        corr_state_list = []
        for state_type, dict in six.iteritems(corr_state_dict):
            unix_timestamp = dict['timestamp']
            state = dict['state']
            if unix_timestamp is not None:
                time = Time(unix_timestamp, format='unix')
            else:
                # None should only happen for `taking_data` = False and it indicates
                # that the correlator shut down badly. Get the most recent state
                # information. If it is True, set it to False with the current time,
                # if it's false use the existing time.
                if state_type == 'taking_data' and state is False:
                    most_recent_state = self.get_correlator_control_state(
                        most_recent=True, state_type=state_type)
                    if len(most_recent_state) == 0:
                        time = Time.now()
                    elif most_recent_state[0].state is True:
                        time = Time.now()
                    else:
                        time = Time(most_recent_state[0].time, format='gps')
                else:
                    raise ValueError('got None timestamp for {type} = {state}'.format(
                        type=state_type, state=state))

            corr_state_list.append(CorrelatorControlState.create(time, state_type, state))

        if testing:
            return corr_state_list
        else:
            self._insert_ignoring_duplicates(CorrelatorControlState, corr_state_list)

    def add_correlator_config_file(self, config_hash, config_file):
        """
        Add new correlator config file to the M&C database.

        Parameters:
        ------------
        config_hash: string
            unique hash of the config
        config_file: string
            name of the config file in the Librarian
        """
        from .correlator import CorrelatorConfigFile

        self.add(CorrelatorConfigFile.create(config_hash, config_file))

    def get_correlator_config_file(self, config_hash):
        """
        Get a correlator config file record from the M&C database.

        Parameters:
        ------------
        config_hash: string
            unique hash for config file

        Returns:
        --------
        list of CorrelatorConfigFile objects
        """
        from .correlator import CorrelatorConfigFile

        query = self.query(CorrelatorConfigFile).filter(CorrelatorConfigFile.config_hash == config_hash)

        return query.all()

    def add_correlator_config_status(self, time, config_hash):
        """
        Add new correlator config status to the M&C database.

        Parameters:
        ------------
        time: astropy time object
            astropy time object based on a timestamp reported by the correlator
        config_hash: string
            unique hash of the config
        """
        from .correlator import CorrelatorConfigStatus

        self.add(CorrelatorConfigStatus.create(time, config_hash))

    def get_correlator_config_status(self, most_recent=None, starttime=None,
                                     config_hash=None, stoptime=None,
                                     write_to_file=False, filename=None):
        """
        Get correlator config status record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time. If starttime
        is set but stoptime is not, this method will return the first record(s)
        after the starttime -- again there can be more than one if there are
        multiple records at the same time. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        Parameters:
        ------------
        most_recent: boolean
            if True, get most recent record. Defaults to True if starttime is None.

        starttime: astropy time object
            Time to look for records after. Ignored if most_recent is True,
            required if most_recent is False.

        stoptime: astropy time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        config_hash: string
            unique hash for config file

        write_to_file: boolean
            Option to write records to a CSV file

        filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        --------
        list of CorrelatorConfigStatus objects
        """
        from .correlator import CorrelatorConfigStatus

        return self._time_filter(CorrelatorConfigStatus, 'time', most_recent=most_recent,
                                 starttime=starttime, stoptime=stoptime,
                                 filter_column='config_hash', filter_value=config_hash,
                                 write_to_file=write_to_file, filename=filename)

    def _add_config_file_to_librarian(self, config, config_hash,
                                      librarian_filename):  # pragma: no cover
        """
        Helper function to save a new config file in the Librarian

        Parameters:
        -----------
        config: string
            decoded yaml string (i.e. result of yaml.safe_load(config_file))
        config_hash: string
            unique hash of the config
        librarian_filename: string
            name of the file in the librarian
        """
        import yaml
        from hera_librarian import LibrarianClient

        # write config out to a file
        lib_store_path = 'correlator_yaml/' + librarian_filename
        librarian_filename_full = os.path.join('/tmp', librarian_filename)
        with open(librarian_filename_full, 'w') as outfile:
            yaml.dump(config, outfile, default_flow_style=False)

        # add config file to librarian
        lib_client = LibrarianClient('local-maint')

        lib_client.upload_file(librarian_filename_full, lib_store_path, 'infer',
                               deletion_policy='disallowed', null_obsid=True)

        # delete the file
        os.remove(librarian_filename_full)

    def add_correlator_config_from_corrcm(self, config_state_dict=None,
                                          testing=False):
        """Get and add correlator config information using a HeraCorrCM object.

        This function connects to the correlator and gets the latest config using
        the `corr._get_config` function. If it is a new config file, it connects
        to the Librarian to upload the config file. For testing purposes, it can
        optionally accept an input dict instead of connecting to the correlator.


        Parameters:
        ------------
        config_state_dict: dict
            A dict containing info as in the return dict from _get_config() for
            testing purposes. If None, _get_config() is called. Default: None
        testing: boolean
            If true, don't add config file to the Librarian or add a record of
            it to the database and return the CorrelatorConfigFile and
            CorrelatorConfigStatus objects. Default False.

        Returns:
        --------
        Optionally returns list of CorrelatorConfigFile and CorrelatorConfigStatus objects (if testing is True)
        """
        from .correlator import _get_config, CorrelatorConfigFile, CorrelatorConfigStatus

        if config_state_dict is None:
            self.add_corr_obj()
            config_state_dict = _get_config(corr_cm=self.corr_obj)

        time = config_state_dict['time']
        config = config_state_dict['config']
        config_hash = config_state_dict['hash']

        config_obj_list = []
        # first check to see if a status with this hash (so identical) already exists
        same_config_status = self.get_correlator_config_status(most_recent=True, config_hash=config_hash)
        if len(same_config_status) == 0:
            # now check to see if a file with this hash (so identical) already exists
            same_config_file = self.get_correlator_config_file(config_hash=config_hash)

            if len(same_config_file) == 0:
                librarian_filename = 'correlator_config_' + str(int(floor(time.gps))) + '.yaml'
                config_file_obj = CorrelatorConfigFile.create(config_hash,
                                                              librarian_filename)

                if not testing:  # pragma: no cover
                    # This config is new.
                    # save it to the Librarian
                    self._add_config_file_to_librarian(config, config_hash,
                                                       librarian_filename)

                    # add it to the config file table
                    self.add(config_file_obj)
                    self.commit()
                else:
                    config_obj_list.append(config_file_obj)

            # make the config status object
            config_status_obj = CorrelatorConfigStatus.create(time, config_hash)
            if not testing:  # pragma: no cover
                self.add(config_status_obj)
                self.commit()
            else:
                config_obj_list.append(config_status_obj)
        else:
            if same_config_status[0].time != floor(time.gps):
                # time is different, so need a new row
                config_status_obj = CorrelatorConfigStatus.create(time, config_hash)

                if not testing:  # pragma: no cover
                    self.add(config_status_obj)
                    self.commit()
                else:
                    config_obj_list.append(config_status_obj)

        if testing:
            return config_obj_list

    def get_correlator_control_command(self, most_recent=None, starttime=None,
                                       stoptime=None, command=None,
                                       write_to_file=False, filename=None):
        """
        Get correlator control command record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time. If starttime
        is set but stoptime is not, this method will return the first record(s)
        after the starttime -- again there can be more than one if there are
        multiple records at the same time. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        Parameters:
        ------------
        most_recent: boolean
            if True, get most recent record. Defaults to True if starttime is None.

        starttime: astropy time object
            Time to look for records after. Ignored if most_recent is True,
            required if most_recent is False.

        stoptime: astropy time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        command: string
            must be a key in correlator.command_dict (e.g. 'take_data',
            'phase_switching_on', 'phase_switching_off', 'restart')

        write_to_file: boolean
            Option to write records to a CSV file

        filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        --------
        list of CorrelatorControlCommand objects
        """
        from .correlator import CorrelatorControlCommand

        return self._time_filter(CorrelatorControlCommand, 'time', most_recent=most_recent,
                                 starttime=starttime, stoptime=stoptime,
                                 filter_column='command', filter_value=command,
                                 write_to_file=write_to_file, filename=filename)

    def get_correlator_take_data_arguments(self, use_command_time=False,
                                           most_recent=None, starttime=None,
                                           stoptime=None, write_to_file=False,
                                           filename=None):
        """
        Get correlator take_data arguments record(s) from the M&C database.

        Default behavior is to return the most recent record. If starttime
        is set but stoptime is not, this method will return the first record
        after the starttime. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        Parameters:
        ------------
        use_command_time: boolean
            Controls whether the query uses the time the command is sent to the
            correlator or the starttime for the take_data command to filter on.
            This affects the interpretation of the all the other keywords.

        most_recent: boolean
            if True, get most recent record. Defaults to True if starttime is None.

        starttime: astropy time object
            Time to look for records after. Note that this refers to the time
            the command was issued, NOT the time the correlator was commanded
            to start taking data. Ignored if most_recent is True,
            required if most_recent is False.

        stoptime: astropy time object
            Last time to get records for, only used if starttime is not None.
            Note that this refers to the time the command was issued, NOT the
            time the correlator was commanded to start taking data.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        write_to_file: boolean
            Option to write records to a CSV file

        filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        --------
        list of CorrelatorTakeDataArguments objects
        """
        from .correlator import CorrelatorTakeDataArguments

        if use_command_time:
            time_column = 'time'
        else:
            time_column = 'starttime_sec'

        return self._time_filter(CorrelatorTakeDataArguments, time_column,
                                 most_recent=most_recent, starttime=starttime,
                                 stoptime=stoptime, write_to_file=write_to_file,
                                 filename=filename)

    def get_correlator_config_command(self, most_recent=None, starttime=None,
                                      config_hash=None, stoptime=None, state_type=None,
                                      write_to_file=False, filename=None):
        """
        Get correlator config command record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time. If starttime
        is set but stoptime is not, this method will return the first record(s)
        after the starttime -- again there can be more than one if there are
        multiple records at the same time. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        Parameters:
        ------------
        most_recent: boolean
            if True, get most recent record. Defaults to True if starttime is None.

        starttime: astropy time object
            Time to look for records after. Ignored if most_recent is True,
            required if most_recent is False.

        stoptime: astropy time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        config_hash: string
            unique hash for config file

        write_to_file: boolean
            Option to write records to a CSV file

        filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        --------
        list of CorrelatorConfigCommand objects
        """
        from .correlator import CorrelatorConfigCommand

        return self._time_filter(CorrelatorConfigCommand, 'time', most_recent=most_recent,
                                 starttime=starttime, stoptime=stoptime,
                                 filter_column='config_hash', filter_value=config_hash,
                                 write_to_file=write_to_file, filename=filename)

    def correlator_control_command(self, command, starttime=None, duration=None,
                                   acclen_spectra=None, tag=None,
                                   overwrite_take_data=False, config_file=None,
                                   dryrun=False, testing=False):
        """
        Issue a correlator control command.

        Parameters:
        ------------
        command: string
            one of the keys in correlator.command_dict (e.g. 'take_data',
            'phase_switching_on', 'phase_switching_off', 'restart')
        starttime: astropy Time object
            only applies if command is 'take_data': time to start taking data
        duration: integer
            only applies if command is 'take_data': Length of time to take data for, in seconds
        acclen_spectra: integer
            only applies if command is 'take_data': Accumulation length in spectra.
            Must be an integer divisible by 2048.
            Default is correlator.DEFAULT_ACCLEN_SPECTRA
        tag: string
            only applies if command is 'take_data': Tag which will end up in data
            files as a header entry, must be from correlator.tag_list (e.g. 'science', 'engineering')
        overwrite_take_data: boolean
            only applies if command is 'take_data': If there is already a take data starttime
            in the future, overwrite it with this command.
        config_file: string
            only applies if command is 'update_config': full path to the config file
                to command the correlator to use. Must exist in a location the
                correlator can access (this name is passed directly to the correlator).
        dryrun: boolean
            if true, just return the list of CorrelatorControlCommand objects, do not
            issue the commands or log them to the database
        testing: boolean
            if true, do not use anything that requires connection to correlator (implies dry run)
        """
        from . import correlator as corr
        import hera_corr_cm
        
        if testing:
            dryrun = True

        if dryrun:
            command_list = []

        command_time = Time.now()

        if not testing:
            if command == 'update_config':
                # Check the current config
                # make sure we have most recent config
                self.add_correlator_config_from_corrcm()
            else:
                # Check state of controls
                # make sure we have most recent state info
                self.add_correlator_control_state_from_corrcm()

        # Get most recent relevant control state
        control_state = []
        if (command in corr.command_state_map.keys()
                and 'state_type' in corr.command_state_map[command]):
            state_type = corr.command_state_map[command]['state_type']
            control_state = self.get_correlator_control_state(most_recent=True,
                                                              state_type=state_type)

        # Check if the correlator is taking data
        taking_data_states = self.get_correlator_control_state(most_recent=True,
                                                               state_type='taking_data')
        if len(taking_data_states) > 0:
            taking_data = taking_data_states[0].state
        else:
            taking_data = False

        if command == 'take_data':
            if taking_data:
                raise RuntimeError('Correlator is already taking data.')

            # Note: correlator can only store one future starttime,
            # if a new command is issued it will overwrite the starttime in the correlator.
            # So we check for that case and only allow overwriting if the
            # overwrite_take_data keyword is True (and then issue a warning)
            if testing:
                # get next start time from the database instead
                next_start_time = None
                take_data_args_objs = self.get_correlator_take_data_arguments(starttime=Time.now())
                if len(take_data_args_objs) > 0:
                    starttimes = []
                    for obj in take_data_args_objs:
                        starttimes.append(obj.starttime_sec + obj.starttime_ms / 1000.)
                    next_start_time = np.min(np.array(starttimes))
            else:
                self.add_corr_obj()
                next_start_time = corr._get_next_start_time(corr_cm=self.corr_obj)

            if next_start_time is not None:
                if not overwrite_take_data:
                    raise RuntimeError('Correlator is already commanded to take data starting at: ',
                                       Time(next_start_time, format='gps').isot,
                                       '. Use the overwrite_take_data keyword to overwrite.')
                else:
                    warnings.warn('Correlator was commanded to take data starting at: '
                                  + Time(next_start_time, format='gps').isot
                                  + '. Overwriting with ' + starttime.isot)

        else:
            if taking_data and not corr.command_state_map[command]['allowed_when_recording']:
                raise RuntimeError('Correlator is taking data. ' + command + ' is not allowed.')

            if len(control_state) > 0:
                if control_state[0].state == corr.command_state_map[command]['state']:
                    # Already in desired state. Return
                    print('Correlator is already in the desired state.')
                    if dryrun:
                        return []
                    else:  # pragma: no cover
                        return

        # create object(s) first: catch any mistakes
        command_obj = corr.CorrelatorControlCommand.create(command_time, command)
        if command == 'take_data':
            if starttime is None:
                raise ValueError('starttime must be specified if command is "take_data"')
            if duration is None:
                raise ValueError('duration must be specified if command is "take_data"')
            if acclen_spectra is None:
                acclen_spectra = corr.DEFAULT_ACCLEN_SPECTRA

            if (not isinstance(acclen_spectra, (int, np.integer))
                    or (acclen_spectra % 2048 != 0)):
                raise ValueError('acclen_spectra must be an integer type and must be a multiple of 2048.')

            if acclen_spectra != corr.DEFAULT_ACCLEN_SPECTRA:
                warnings.warn('Using a non-standard acclen_spectra!')

            if tag is None:
                raise ValueError('tag must be specified if command is "take_data"')

            if config_file is not None:
                raise ValueError('config_file cannot be specified if command is not "update_config"')

            if not testing:
                self.add_corr_obj()
                integration_time = corr._get_integration_time(acclen_spectra, corr_cm=self.corr_obj)
            else:
                # based on default values in hera_corr_cm
                integration_time = acclen_spectra * ((2.0 * 16384) / 500e6)

            take_data_args_obj = \
                corr.CorrelatorTakeDataArguments.create(command_time, starttime,
                                                        duration, acclen_spectra,
                                                        integration_time, tag)
        elif command == 'update_config':
            import hashlib

            if config_file is None:
                raise ValueError('config_file must be specified if command is "update_config"')

            # construct the file hash in the same way as the correlator does
            with open(config_file, 'r') as fh:
                config_string = fh.read().encode('utf-8')
                config_hash = hashlib.md5(config_string).hexdigest()

            # Get most recent config
            current_config_status = self.get_correlator_config_status(most_recent=True)
            if len(current_config_status) > 0:
                different_hash = config_hash != current_config_status[0].config_hash
            else:
                different_hash = True

            if different_hash:
                # now check to see if a file with this hash (so identical) already exists
                same_config_file = self.get_correlator_config_file(config_hash=config_hash)

                if len(same_config_file) == 0:
                    # This is a new config
                    # Name it using the existing name. Adding it to the Librarian
                    # will fail if a file with that name already exists in the Librarian.
                    librarian_filename = config_file
                    config_file_obj = corr.CorrelatorConfigFile.create(config_hash,
                                                                       librarian_filename)

                    if not dryrun:  # pragma: no cover
                        # This config is new.
                        # save it to the Librarian
                        with open(config_file, 'r') as stream:
                            config = yaml.safe_load(stream)
                        self._add_config_file_to_librarian(config, config_hash,
                                                           librarian_filename)

                        # add it to the config file table
                        self.add(config_file_obj)
                        self.commit()
                    else:
                        command_list.append(config_file_obj)

                # make the config command object
                config_command_obj = corr.CorrelatorConfigCommand.create(command_time, config_hash)
            else:
                # config is unchanged. Return
                print('Correlator already has the desired config.')
                if dryrun:
                    return []
                else:  # pragma: no cover
                    return
        else:
            if starttime is not None:
                raise ValueError('starttime cannot be specified if command is not "take_data"')
            if duration is not None:
                raise ValueError('duration cannot be specified if command is not "take_data"')
            if acclen_spectra is not None:
                raise ValueError('acclen_spectra cannot be specified if command is not "take_data"')
            if tag is not None:
                raise ValueError('tag cannot be specified if command is not "take_data"')
            if config_file is not None:
                raise ValueError('config_file cannot be specified if command is not "update_config"')

        if not dryrun:  # pragma: no cover
            self.add_corr_obj()

            if command == 'take_data':
                # the correlator starttime can be different from the commanded
                # time by as much as 134 ms
                # the call to hera_corr_cm returns the actual start time (in unix format)
                # input time needs to be unix epoch in ms
                starttime_used_unix = \
                    getattr(self.corr_obj, corr.command_dict[command])(np.round(starttime.unix*1000), duration, acclen_spectra, tag=tag)
                                            int(np.round(starttime.unix*1000)), duration, acclen_spectra, tag=tag)
                if starttime_used_unix is hera_corr_cm.ERROR:
                    warnings.warn('take_data returned ERROR on inputs: {t}, {d}, {acc},{tag}'.format(
                        t=int(np.round(starttime.unix * 1000)),
                        d=duration,
                        acc=acclen_spectra,
                        tag=tag))
                starttime_used = Time(starttime_used_unix, format='unix')

                starttime_diff_sec = starttime.gps - starttime_used.gps
                if np.abs(starttime_diff_sec) > .1:
                    warnings.warn('Time difference between commanded and accepted '
                                  'start time is: {tdiff} sec'.format(tdiff=starttime_diff_sec))
            elif command == 'update_config':
                getattr(self.corr_obj, corr.command_dict[command])(config_file)
            else:
                getattr(self.corr_obj, corr.command_dict[command])()

            self.add(command_obj)
            self.commit()
            if command == 'take_data':
                # update the starttime with the actual starttime of the correlator
                take_data_args_obj = \
                    corr.CorrelatorTakeDataArguments.create(command_time, starttime_used,
                                                            duration, acclen_spectra,
                                                            integration_time, tag)
                self.add(take_data_args_obj)
                self.commit()
            elif command == 'update_config':
                self.add(config_command_obj)
                self.commit()

        else:
            command_list.append(command_obj)
            if command == 'take_data':
                command_list.append(take_data_args_obj)
            elif command == 'update_config':
                command_list.append(config_command_obj)

        if dryrun:
            return command_list

    def add_correlator_software_versions(self, time, package, version):
        """
        Add new correlator software versions to the M&C database.

        Parameters:
        ------------
        time: astropy time object
            astropy time object based on the version report timestamp
        package: string
            name of the correlator software module or <package>:<script> for
                daemonized processes(e.g. 'hera_corr_cm', 'udpSender:hera_node_keep_alive.py')
        version: string
            version string for this package or script
        """
        from .correlator import CorrelatorSoftwareVersions

        self.add(CorrelatorSoftwareVersions.create(time, package, version))

    def get_correlator_software_versions(self, most_recent=None, starttime=None,
                                         stoptime=None, package=None,
                                         write_to_file=False, filename=None):
        """
        Get correlator software versions record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time. If starttime
        is set but stoptime is not, this method will return the first record(s)
        after the starttime -- again there can be more than one if there are
        multiple records at the same time. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        Parameters:
        ------------
        most_recent: boolean
            if True, get most recent record. Defaults to True if starttime is None.

        starttime: astropy time object
            Time to look for records after. Ignored if most_recent is True,
            required if most_recent is False.

        stoptime: astropy time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        package: string
            name of the correlator software module (e.g. "hera_corr_f")

        write_to_file: boolean
            Option to write records to a CSV file

        filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        --------
        list of CorrelatorSoftwareVersions objects
        """
        from .correlator import CorrelatorSoftwareVersions

        return self._time_filter(CorrelatorSoftwareVersions, 'time', most_recent=most_recent,
                                 starttime=starttime, stoptime=stoptime,
                                 filter_column='package', filter_value=package,
                                 write_to_file=write_to_file, filename=filename)

    def add_snap_config_version(self, init_time, version, init_args, config_hash):
        """
        Add new SNAP configuration and version to the M&C database.

        Parameters:
        ------------
        init_time: astropy time object
            astropy time object for when the SNAPs were last initialized with the
                `hera_snap_feng_init.py` script
        version: string
            version string for the hera_corr_f package
        init_args: string
            arguments passed to the initialization script at runtime
        config_hash: string
            unique hash of the config, foreign key into correlator_config_file table
        """
        from .correlator import SNAPConfigVersion

        self.add(SNAPConfigVersion.create(init_time, version, init_args, config_hash))

    def get_snap_config_version(self, most_recent=None, starttime=None, stoptime=None,
                                write_to_file=False, filename=None):
        """
        Get SNAP configuration and version record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time. If starttime
        is set but stoptime is not, this method will return the first record(s)
        after the starttime -- again there can be more than one if there are
        multiple records at the same time. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        Parameters:
        ------------
        most_recent: boolean
            if True, get most recent record. Defaults to True if starttime is None.

        starttime: astropy time object
            Time to look for records after. Ignored if most_recent is True,
            required if most_recent is False.

        stoptime: astropy time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        write_to_file: boolean
            Option to write records to a CSV file

        filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        --------
        list of SNAPConfigVersion objects
        """
        from .correlator import SNAPConfigVersion

        return self._time_filter(SNAPConfigVersion, 'init_time', most_recent=most_recent,
                                 starttime=starttime, stoptime=stoptime,
                                 write_to_file=write_to_file, filename=filename)

    def add_corr_snap_versions_from_corrcm(self, corr_snap_version_dict=None,
                                           testing=False):
        """Get and add correlator and snap configuration and version information using a HeraCorrCM object.

        This function connects to the correlator and gets the latest data using the
        `_get_corr_versions` function. For testing purposes, it can
        optionally accept an input dict instead of connecting to the correlator.

        If the current database is PostgreSQL, this function will use a
        special insertion method that will ignore records that are redundant
        with ones already in the database. This makes it convenient to sample
        the data frequently on qmaster.

        Parameters:
        ------------
        corr_snap_version_dict: dict
            A dict containing info as in the return dict from corr._get_corr_versions() for
            testing purposes. If None, _get_corr_versions() is called.
        testing: boolean
            If true, don't add a record of it to the database and return the list of
            CorrelatorSoftwareVersions, CorrelatorConfigFile, CorrelatorConfigStatus and
            SNAPConfigVersion objects.

        Returns:
        --------
        list of objects, optional
            Optionally returns the list of CorrelatorSoftwareVersions,
            CorrelatorConfigFile, CorrelatorConfigStatus and
            SNAPConfigVersion objects (if testing is True)

        """
        from .correlator import (_get_corr_versions, CorrelatorSoftwareVersions,
                                 SNAPConfigVersion)

        if corr_snap_version_dict is None:
            self.add_corr_obj()
            corr_snap_version_dict = _get_corr_versions(corr_cm=self.corr_obj)

        corr_version_list = []
        snap_version_list = []
        for package, version_dict in six.iteritems(corr_snap_version_dict):
            time = Time(version_dict['timestamp'], format='datetime')
            version = version_dict['version']

            if package == 'hera_corr_cm':
                # we get a new timestamp every time we call hera_corr_cm.
                # Don't make a new row unless it's a new version.
                # First, get most recent version in table
                last_hera_corr_cm_entry = self.get_correlator_software_versions(
                    package='hera_corr_cm')
                if len(last_hera_corr_cm_entry) == 0:
                    last_version = ''
                else:
                    last_version = last_hera_corr_cm_entry[0].version
                if last_version != version:
                    # this is a new version, make a new object
                    corr_version_list.append(
                        CorrelatorSoftwareVersions.create(time, package, version))
            elif package != 'snap':
                corr_version_list.append(
                    CorrelatorSoftwareVersions.create(time, package, version))
            else:
                init_args = version_dict['init_args']
                config_hash = version_dict['config_md5']
                snap_version_list.append(SNAPConfigVersion.create(time, version,
                                                                  init_args,
                                                                  config_hash))

                config_time = Time(version_dict['config_timestamp'],
                                   format='datetime')
                config = version_dict['config']
                snap_config_dict = {'time': config_time, 'hash': config_hash,
                                    'config': config}

        # make sure this config is in the correlator config status table
        # (really should be, but this will add it if it was somehow missed)
        config_obj_list = self.add_correlator_config_from_corrcm(config_state_dict=snap_config_dict,
                                                                 testing=testing)

        if testing:
            return corr_version_list + config_obj_list + snap_version_list
        else:
            self._insert_ignoring_duplicates(CorrelatorSoftwareVersions, corr_version_list)
            self._insert_ignoring_duplicates(SNAPConfigVersion, snap_version_list)

    def _get_node_snap_from_serial(self, snap_serial, session=None):
        from hera_mc import cm_handling, cm_utils
        if session is None:
            session = self

        cmh = cm_handling.Handling(session)
        conn_dossier = cmh.get_part_connection_dossier(snap_serial, rev='active',
                                                       port='all', at_date='now')

        if len(conn_dossier.keys()) == 0:
            warnings.warn('No active dossiers returned for snap serial '
                          '{snn}. Setting node and snap location numbers to None'.format(snn=snap_serial))
            return None, None

        if len(conn_dossier.keys()) > 1:
            warnings.warn('Multiple active dossiers returned for snap serial '
                          '{snn}. Setting node and snap location numbers to None'.format(snn=snap_serial))
            return None, None

        snap_num_rev = list(conn_dossier.keys())[0]
        node_conn = [conn for conn in conn_dossier[snap_num_rev].keys_down if conn is not None]

        node_part = set()
        node_rev = set()
        snap_loc = set()
        for conn in node_conn:
            conn_tuple = cm_utils.split_connection_key(conn)
            node_part.add(conn_tuple[0])
            node_rev.add(conn_tuple[1])
            snap_loc.add(conn_tuple[2])

        node_part = list(node_part)
        node_rev = list(node_rev)
        snap_loc = list(snap_loc)
        if len(node_part) > 1 or len(node_rev) > 1:
            warnings.warn('Multiple node connections returned for snap serial '
                          '{snn}. Setting node and snap location number to None'.format(snn=snap_serial))
            return None, None

        node_part = node_part[0]
        try:
            assert node_part.startswith('N')
            nodeID = int(node_part[1:])
        except(ValueError, AssertionError):
            nodeID = None

        if len(snap_loc) > 1:
            warnings.warn('Multiple snap location numbers returned for snap serial '
                          '{snn}. Setting snap location number to None'.format(snn=snap_serial))
            snap_loc_num = None
        else:
            snap_loc = snap_loc[0]
            try:
                assert snap_loc.startswith('loc')
                snap_loc_num = int(snap_loc[3:])
            except(ValueError, AssertionError):
                snap_loc_num = None

        return nodeID, snap_loc_num

    def add_snap_status(self, time, hostname, serial_number, psu_alert, pps_count,
                        fpga_temp, uptime_cycles, last_programmed_time):
        """
        Add new snap status data to the M&C database.

        Parameters:
        ------------
        time: astropy time object
            astropy time object based on a timestamp reported by the correlator
        hostname: string
            snap hostname
        serial_number: string
            Serial number of the SNAP board
        psu_alert: boolean
            True if SNAP PSU (aka PMB) controllers have issued an alert. False otherwise.
        pps_count: integer
            Number of PPS pulses received since last programming cycle
        fpga_temp: float
            Reported FPGA temperature in degrees Celsius
        uptime_cycles: integer
            Multiples of 500e6 ADC clocks since last programming cycle
        last_programmed_time: astropy time object
            astropy time object based on the last time this FPGA was programmed
        """
        from .correlator import SNAPStatus

        # get node & snap location number from config management
        nodeID, snap_loc_num = self._get_node_snap_from_serial(serial_number)

        self.add(SNAPStatus.create(time, hostname, nodeID, snap_loc_num, serial_number,
                                   psu_alert, pps_count, fpga_temp, uptime_cycles,
                                   last_programmed_time))

    def get_snap_status(self, most_recent=None, starttime=None, stoptime=None,
                        nodeID=None, write_to_file=False, filename=None):
        """
        Get snap status record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time. If starttime
        is set but stoptime is not, this method will return the first record(s)
        after the starttime -- again there can be more than one if there are
        multiple records at the same time. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        Parameters:
        ------------
        most_recent: boolean
            if True, get most recent record. Defaults to True if starttime is None.

        starttime: astropy time object
            Time to look for records after. Ignored if most_recent is True,
            required if most_recent is False.

        stoptime: astropy time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        nodeID: integer
            node number (integer running from 1 to 30)

        write_to_file: boolean
            Option to write records to a CSV file

        filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        --------
        list of SNAPStatus objects
        """
        from .correlator import SNAPStatus

        return self._time_filter(SNAPStatus, 'time', most_recent=most_recent,
                                 starttime=starttime, stoptime=stoptime,
                                 filter_column='node', filter_value=nodeID,
                                 write_to_file=write_to_file, filename=filename)

    def add_snap_status_from_corrcm(self, snap_status_dict=None, testing=False,
                                    cm_session=None):
        """Get and add snap status information using a HeraCorrCM object.

        This function connects to the correlator and gets the latest data using the
        `_get_snap_status` function. For testing purposes, it can
        optionally accept an input dict instead of connecting to the correlator.
        It can use a different session for the cm info (this is useful for testing onsite).

        If the current database is PostgreSQL, this function will use a
        special insertion method that will ignore records that are redundant
        with ones already in the database. This makes it convenient to sample
        the data frequently on qmaster.

        Parameters:
        ------------
        snap_status_dict: dict
            A dict containing info as in the return dict from _get_snap_status() for
            testing purposes. If None, _get_snap_status() is called. Default: None
        testing: boolean
            If true, don't add a record of it to the database and return the list of
            SNAPStatus objects. Default False.
        cm_session:
            Session object to use for the CM queries. Defaults to self, but can
            be set to another session instance (useful for testing).

        Returns:
        --------
        Optionally returns the list of SNAPStatus objects (if testing is True)

        """
        from .correlator import _get_snap_status, SNAPStatus

        if snap_status_dict is None:
            self.add_corr_obj()
            snap_status_dict = _get_snap_status(corr_cm=self.corr_obj)

        snap_status_list = []
        for hostname, snap_dict in six.iteritems(snap_status_dict):

            # first check if the timestamp is the string 'None'
            # if it is, skip this snap
            timestamp = snap_dict['timestamp']
            if timestamp == 'None':
                continue
            else:
                time = Time(timestamp, format='datetime')

            # any entry other than timestamp can be the string 'None'
            # need to convert those to a None type
            for key, val in six.iteritems(snap_dict):
                if val == 'None':
                    snap_dict[key] = None

            serial_number = snap_dict['serial']
            psu_alert = snap_dict['pmb_alert']
            pps_count = snap_dict['pps_count']
            fpga_temp = snap_dict['temp']
            uptime_cycles = snap_dict['uptime']

            last_programmed_datetime = snap_dict['last_programmed']
            if last_programmed_datetime is not None:
                last_programmed_time = Time(last_programmed_datetime, format='datetime')
            else:
                last_programmed_time = None

            # get nodeID & snap location number from config management
            if serial_number is not None:
                nodeID, snap_loc_num = self._get_node_snap_from_serial(serial_number,
                                                                       session=cm_session)
            else:
                nodeID = None
                snap_loc_num = None

            snap_status_list.append(SNAPStatus.create(time, hostname, nodeID, snap_loc_num,
                                                      serial_number, psu_alert,
                                                      pps_count, fpga_temp,
                                                      uptime_cycles,
                                                      last_programmed_time))

        if testing:
            return snap_status_list
        else:
            self._insert_ignoring_duplicates(SNAPStatus, snap_status_list)

    def add_antenna_status(self, time, antenna_number, antenna_feed_pol,
                           snap_hostname, snap_channel_number, adc_mean, adc_rms,
                           adc_power, pam_atten, pam_power, pam_voltage,
                           pam_current, pam_id, fem_voltage, fem_current, fem_id,
                           fem_temp, eq_coeffs, histogram_bin_centers,
                           histogram):
        """
        Add new antenna status data to the M&C database.

        Parameters:
        ------------
        time: astropy time object
            astropy time object based on a timestamp reported by the correlator
        antenna_number: integer
            antenna number
        antenna_feed_pol: string
            Feed polarization, either 'e' or 'n'
        snap_hostname: string
            hostname of snap the antenna is connected to
        snap_channel_number: integer
            The SNAP ADC channel number (0-7) to which this antenna is connected
        adc_mean: float
            Mean ADC value, in ADC units, meaning raw ADC values interpreted as
            signed integers between -128 and +127. Typically ~ -0.5.
        adc_rms: float
            RMS ADC value, in ADC units, meaning raw ADC values interpreted as
            signed integers between -128 and +127.  Should be ~ 10-20.
        adc_power: float
            Mean ADC power, in ADC units squared, meaning raw ADC values
            interpreted as signed integers between -128 and +127 and then squared.
            Since mean should be close to zero, this should just be adc_rms^2.
        pam_atten: integer
            PAM attenuation setting for this antenna, in dB
        pam_power: float
            PAM power sensor reading for this antenna, in dBm
        pam_voltage : float
            PAM voltage sensor reading for this antenna, in Volts
        pam_current : float
            PAM current sensor reading for this antenna, in Amps
        pam_id : str
            serial number of this PAM
        fem_voltage : float
            FEM voltage sensor reading for this antenna, in Volts
        fem_current : float
            FEM current sensor reading for this antenna, in Amps
        fem_id : str
            serial number of this FEM
        fem_temp : float
            EM temperature sensor reading for this antenna in degrees Celsius
        eq_coeffs : list of float
            Digital EQ coefficients, used for keeping the bit occupancy in the
            correct range, for this antenna, list of floats. Note this these are
            not divided out anywhere in the DSP chain (!).
        histogram_bin_centers : list of int
            ADC histogram bin centers
        histogram : list of int
            ADC histogram counts
        """
        from .correlator import AntennaStatus

        self.add(AntennaStatus.create(time, antenna_number, antenna_feed_pol,
                                      snap_hostname, snap_channel_number, adc_mean,
                                      adc_rms, adc_power, pam_atten, pam_power,
                                      pam_voltage, pam_current, pam_id, fem_voltage,
                                      fem_current, fem_id, fem_temp, eq_coeffs,
                                      histogram_bin_centers, histogram))

    def get_antenna_status(self, most_recent=None, starttime=None, stoptime=None,
                           antenna_number=None, write_to_file=False, filename=None):
        """
        Get antenna status record(s) from the M&C database.

        Default behavior is to return the most recent record(s) -- there can be
        more than one if there are multiple records at the same time. If starttime
        is set but stoptime is not, this method will return the first record(s)
        after the starttime -- again there can be more than one if there are
        multiple records at the same time. If you want a range of times you need
        to set both startime and stoptime. If most_recent is set, startime and
        stoptime are ignored.

        Parameters:
        ------------
        most_recent: boolean
            if True, get most recent record. Defaults to True if starttime is None.

        starttime: astropy time object
            Time to look for records after. Ignored if most_recent is True,
            required if most_recent is False.

        stoptime: astropy time object
            Last time to get records for, only used if starttime is not None.
            If none, only the first record after starttime will be returned.
            Ignored if most_recent is True.

        antenna_number: integer
            antenna number

        write_to_file: boolean
            Option to write records to a CSV file

        filename: string
            Name of file to write to. If not provided, defaults to a file in the
            current directory named based on the table name.
            Ignored if write_to_file is False

        Returns:
        --------
        list of AntennaStatus objects
        """
        from .correlator import AntennaStatus

        return self._time_filter(AntennaStatus, 'time', most_recent=most_recent,
                                 starttime=starttime, stoptime=stoptime,
                                 filter_column='antenna_number', filter_value=antenna_number,
                                 write_to_file=write_to_file, filename=filename)

    def add_antenna_status_from_corrcm(self, ant_status_dict=None, testing=False):
        """Get and add antenna status information using a HeraCorrCM object.

        This function connects to the correlator and gets the latest data using the
        `create_antenna_status` function. For testing purposes, it can
        optionally accept an input dict instead of connecting to the correlator.

        If the current database is PostgreSQL, this function will use a
        special insertion method that will ignore records that are redundant
        with ones already in the database. This makes it convenient to sample
        the data frequently on qmaster.

        Parameters:
        ------------
        ant_status_dict: dict
            A dict containing info as in the return dict from corr._get_ant_status() for
            testing purposes. If None, _get_ant_status() is called. Default: None
        testing: boolean
            If true, don't add a record of it to the database and return the list of
            AntennaStatus objects. Default False.

        Returns:
        --------
        Optionally returns the list of AntennaStatus objects (if testing is True)

        """
        from .correlator import create_antenna_status, AntennaStatus

        if ant_status_dict is None:
            self.add_corr_obj()
            corr_cm = self.corr_obj
        else:
            corr_cm = None
        antenna_status_list = create_antenna_status(corr_cm=corr_cm,
                                                    ant_status_dict=ant_status_dict)

        if testing:
            return antenna_status_list
        else:
            self._insert_ignoring_duplicates(AntennaStatus, antenna_status_list)

    def add_ant_metric(self, obsid, ant, pol, metric, val):
        """
        Add a new antenna metric to the M&C database.

        Parameters:
        ------------
        obsid: long integer
            observation identification number
        ant: integer
            antenna number
        pol: string ('x' or 'y')
            polarization
        metric: string
            metric name
        val: float
            value of metric
        """
        from .qm import AntMetrics

        db_time = self.get_current_db_time()

        self.add(AntMetrics.create(obsid, ant, pol, metric, db_time, val))

    def get_ant_metric(self, ant=None, pol=None, metric=None, starttime=None,
                       stoptime=None):
        """
        Get antenna metric(s) from the M&C database.

        Parameters:
        ------------
        ant: integer or list of integers
            antenna number. Defaults to returning all antennas.
        pol: string ('x' or 'y'), or list
            polarization. Defaults to returning all pols.
        metric: string or list of strings
            metric name. Defaults to returning all metrics.
        starttime: astropy time object OR gps second.
            beginning of query time interval. Defaults to gps=0 (6 Jan, 1980)
        stoptime: astropy time object OR gps second.
            end of query time interval. Defaults to now.

        Returns:
        --------
        list of AntMetrics objects
        """
        from .qm import AntMetrics

        args = []
        if ant is not None:
            args.append(AntMetrics.ant.in_(get_iterable(ant)))
        if pol is not None:
            args.append(AntMetrics.pol.in_(get_iterable(pol)))
        if metric is not None:
            args.append(AntMetrics.metric.in_(get_iterable(metric)))
        if starttime is None:
            starttime = 0
        elif isinstance(starttime, Time):
            starttime = starttime.gps
        if stoptime is None:
            stoptime = Time.now().gps
        elif isinstance(stoptime, Time):
            stoptime = stoptime.gps
        args.append(AntMetrics.obsid.between(starttime, stoptime))
        return self.query(AntMetrics).filter(*args).all()

    def add_array_metric(self, obsid, metric, val):
        """
        Add a new array metric to the M&C database.

        Parameters:
        ------------
        obsid: long integer
            observation identification number
        metric: string
            metric name
        val: float
            value of metric
        """
        from .qm import ArrayMetrics

        db_time = self.get_current_db_time()

        self.add(ArrayMetrics.create(obsid, metric, db_time, val))

    def get_array_metric(self, metric=None, starttime=None, stoptime=None):
        """
        Get array metric(s) from the M&C database.

        Parameters:
        ------------
        metric: string or list of strings
            metric name. Defaults to returning all metrics.
        starttime: astropy time object OR gps second.
            beginning of query time interval. Defaults to gps=0 (6 Jan, 1980)
        stoptime: astropy time object OR gps second.
            end of query time interval. Defaults to now.

        Returns:
        --------
        list of ArrayMetrics objects
        """
        from .qm import ArrayMetrics

        args = []
        if metric is not None:
            args.append(ArrayMetrics.metric.in_(get_iterable(metric)))
        if starttime is None:
            starttime = 0
        elif isinstance(starttime, Time):
            starttime = starttime.gps
        if stoptime is None:
            stoptime = Time.now().gps
        elif isinstance(stoptime, Time):
            stoptime = stoptime.gps
        args.append(ArrayMetrics.obsid.between(starttime, stoptime))
        return self.query(ArrayMetrics).filter(*args).all()

    def add_metric_desc(self, metric, desc):
        """
        Add a new metric description to the M&C database.

        Parameters:
        ------------
        metric: string
            metric name
        desc: string
            description of metric
        """
        from .qm import MetricList

        self.add(MetricList.create(metric, desc))

    def update_metric_desc(self, metric, desc):
        """
        Update the description of a metric in the M&C database.
        This will be required when replacing an RTP auto-generated description for
        new metrics.

        Parameters:
        ------------
        metric: string
            metric name
        desc: string
            description of metric
        """
        from .qm import MetricList

        self.query(MetricList).filter(MetricList.metric == metric)[0].desc = desc
        self.commit()

    def get_metric_desc(self, metric=None):
        """
        Get metric description(s) from the M&C database.

        Parameters:
        ------------
        metric: string or list of strings
            metric name. Defaults to returning all metrics.

        Returns:
        --------
        list of MetricList objects
        """
        from .qm import MetricList

        args = []
        if metric is not None:
            args.append(MetricList.metric.in_(get_iterable(metric)))

        return self.query(MetricList).filter(*args).all()

    def check_metric_desc(self, metric):
        """
        Check that metric has a description in the db. If not, fill in and issue warning.

        Parameters:
        -----------
        metrics: string or list of strings
            metric name.
        """
        r = self.get_metric_desc(metric=metric)
        if len(r) == 0:
            warnings.warn('Metric ' + metric + ' not found in db. Adding a filler description.'
                          'Please update ASAP with hera_mc/scripts/update_qm_list.py.')
            self.add_metric_desc(metric, 'Auto-generated description. Update with '
                                 'hera_mc/scripts/update_qm_list.py')
            self.commit()

    def update_qm_list(self):
        """
        Updates metric list according to descriptions in hera_qm.
        """
        from hera_qm.utils import get_metrics_dict

        metric_list = get_metrics_dict()

        for metric, desc in metric_list.items():
            # Check if metric is already in db.
            r = self.get_metric_desc(metric=metric)
            if len(r) == 0:
                self.add_metric_desc(metric, desc)
            else:
                self.update_metric_desc(metric, desc)
        self.commit()

    def ingest_metrics_file(self, filename, ftype):
        """
        Adds a file worth of quality metrics to the db.

        Parameters:
        -----------
        filename: string
            file containing metrics to be added to db.
        ftype: string
            Type of metrics file. Options are ['ant', 'firstcal', 'omnical']
        """
        from hera_qm.utils import metrics2mc
        import os

        try:
            obsid = self.get_lib_files(filename=os.path.basename(filename))[0].obsid
        except IndexError:
            raise ValueError('File ' + filename + ' has not been logged in '
                             'Librarian, so we cannot add to M&C.')
        d = metrics2mc(filename, ftype)
        for metric, dd in d['ant_metrics'].items():
            self.check_metric_desc(metric)
            for ant, pol, val in dd:
                self.add_ant_metric(obsid, ant, pol, metric, val)
        for metric, val in d['array_metrics'].items():
            self.check_metric_desc(metric)
            self.add_array_metric(obsid, metric, val)
