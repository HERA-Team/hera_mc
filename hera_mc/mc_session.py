# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

from __future__ import absolute_import, division, print_function

from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import func
from astropy.time import Time, TimeDelta
import warnings
import six

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

    def _time_filter(self, table_class, time_column, starttime, stoptime=None,
                     filter_column=None, filter_value=None):
        '''
        A helper method to fiter entries by time. Used by most get methods
        on this object.

        Parameters:
        table_class: class
            Class specifying a table to query.

        time_column: string
            column name holding the time to filter on.

        starttime: astropy time object
            time to look for records after

        stoptime: astropy time object
            last time to get records for. If none, only the first record after
            starttime will be returned.

        filter_column: string
            column name to use as an additional filter (often a part of the primary key)

        filter_value: type coresponding to filter_column, usually a string
            value to require that the filter_column is equal to

        Returns:
        --------
        list of objects that match the filtering
        '''
        if not isinstance(starttime, Time):
            raise ValueError('starttime must be an astropy time object. '
                             'value was: {t}'.format(t=starttime))

        if stoptime is not None:
            if not isinstance(stoptime, Time):
                raise ValueError('stoptime must be an astropy time object. '
                                 'value was: {t}'.format(t=stoptime))

        if stoptime is not None:
            if filter_value is not None:
                result_list = self.query(table_class).filter(
                    getattr(table_class, filter_column) == filter_value,
                    getattr(table_class, time_column).between(
                        starttime.gps, stoptime.gps)).all()
            else:
                result_list = self.query(table_class).filter(
                    getattr(table_class, time_column).between(
                        starttime.gps, stoptime.gps)).all()
        else:
            if filter_value is not None:
                result_list = self.query(table_class).filter(
                    getattr(table_class, filter_column) == filter_value,
                    getattr(table_class, time_column) >= starttime.gps).order_by(
                        getattr(table_class, time_column)).limit(1).all()
            else:
                result_list = self.query(table_class).filter(
                    getattr(table_class, time_column) >= starttime.gps).order_by(
                        getattr(table_class, time_column)).limit(1).all()

        return result_list

    def _insert_ignoring_duplicates(self, table_class, obj_list):
        """
        If the current database is PostgreSQL, this function will use a
        special insertion method that will ignore records that are redundant
        with ones already in the database. This makes it convenient to sample
        the certain data (especially redis data) densely on qmaster.

        Parameters:
        table_class: class
            Class specifying a table to insert into.
        obj_list: list of objects
            list of objects (of class table_class) to insert into the table.
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

                # The special PostgreSQL insert statement lets us ignore
                # existing rows via `ON CONFLICT ... DO NOTHING` syntax.
                stmt = insert(table_class).values(**values).on_conflict_do_nothing(index_elements=ies)
                conn.execute(stmt)
        else:
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

    def get_obs_by_time(self, starttime, stoptime=None):
        """
        Get observation(s) from the M&C database.

        Parameters:
        ------------
        starttime: astropy time object
            time to look for records after

        stoptime: astropy time object
            last time to get records for. If none, only the first record after
            starttime will be returned.

        Returns:
        --------
        list of Observation objects
        """
        from .observations import Observation

        return self._time_filter(Observation, 'obsid', starttime, stoptime=stoptime)

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

    def get_server_status(self, subsystem, starttime, stoptime=None, hostname=None):
        """
        Get subsystem server_status record(s) from the M&C database.

        Parameters:
        ------------
        subsystem: string
            name of subsystem. Must be one of ['rtp', 'lib']

        starttime: astropy time object
            time to look for records after

        stoptime: astropy time object
            last time to get records for. If none, only the first record after
            starttime will be returned.

        hostname: string
            hostname to get records for. If none, all hostnames will be included.

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

        return self._time_filter(ServerStatus, 'mc_time', starttime,
                                 stoptime=stoptime, filter_column='hostname',
                                 filter_value=hostname)

    def add_subsystem_error(self, time, subsystem, severity, log):
        """
        Add a new subsystem subsystem_error to the M&C database.

        Parameters:
        ------------
        time: astropy time object
            time of this error report
        subsystem: string
            name of subsystem with error
        severity: integer
            integer indicating severity level, 1 is most severe
        log: string
            error message or log file name (TBD)
        """
        from .subsystem_error import SubsystemError

        db_time = self.get_current_db_time()

        self.add(SubsystemError.create(db_time, time, subsystem, severity, log))

    def get_subsystem_error(self, starttime, stoptime=None, subsystem=None):
        """
        Get subsystem server_status record(s) from the M&C database.

        Parameters:
        ------------
        subsystem: string
            name of subsystem. Must be one of ['rtp', 'lib']

        starttime: astropy time object
            time to look for records after

        stoptime: astropy time object
            last time to get records for. If none, only the first record after
            starttime will be returned.

        subsystem: string
            subsystem to get records for. If none, all subsystems will be included.

        Returns:
        --------
        list of SubsystemError objects
        """
        from .subsystem_error import SubsystemError

        return self._time_filter(SubsystemError, 'time', starttime,
                                 stoptime=stoptime, filter_column='subsystem',
                                 filter_value=subsystem)

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

    def get_lib_status(self, starttime, stoptime=None):
        """
        Get lib_status record(s) from the M&C database.

        Parameters:
        ------------
        starttime: astropy time object
            time to look for records after

        stoptime: astropy time object
            last time to get records for. If none, only the first record after
            starttime will be returned.

        Returns:
        --------
        list of LibStatus objects
        """
        from .librarian import LibStatus

        return self._time_filter(LibStatus, 'time', starttime,
                                 stoptime=stoptime)

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

    def get_lib_raid_status(self, starttime, stoptime=None, hostname=None):
        """
        Get lib_raid_status record(s) from the M&C database.

        Parameters:
        ------------
        starttime: astropy time object
            time to look for records after

        stoptime: astropy time object
            last time to get records for. If none, only the first record after
            starttime will be returned.

        hostname: string
            RAID hostname to get records for. If none, all hostnames will be included.

        Returns:
        --------
        list of LibRAIDStatus objects
        """
        from .librarian import LibRAIDStatus

        return self._time_filter(LibRAIDStatus, 'time', starttime,
                                 stoptime=stoptime, filter_column='hostname',
                                 filter_value=hostname)

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

    def get_lib_raid_error(self, starttime, stoptime=None, hostname=None):
        """
        Get lib_raid_error record(s) from the M&C database.

        Parameters:
        ------------
        starttime: astropy time object
            time to look for records after

        stoptime: astropy time object
            last time to get records for. If none, only the first record after
            starttime will be returned.

        hostname: string
            RAID hostname to get records for. If none, all hostnames will be included.

        Returns:
        --------
        list of LibRAIDErrors objects
        """
        from .librarian import LibRAIDErrors

        return self._time_filter(LibRAIDErrors, 'time', starttime,
                                 stoptime=stoptime, filter_column='hostname',
                                 filter_value=hostname)

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

    def get_lib_remote_status(self, starttime, stoptime=None, remote_name=None):
        """
        Get lib_remote_status record(s) from the M&C database.

        Parameters:
        ------------
        starttime: astropy time object
            time to look for records after

        stoptime: astropy time object
            last time to get records for. If none, only the first record after
            starttime will be returned.

        remote_name: string
            Name of remote librarian to get records for. If none, all
            remote_names will be included.

        Returns:
        --------
        list of LibRemoteStatus objects
        """
        from .librarian import LibRemoteStatus

        return self._time_filter(LibRemoteStatus, 'time', starttime,
                                 stoptime=stoptime, filter_column='remote_name',
                                 filter_value=remote_name)

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

    def get_lib_files(self, filename=None, obsid=None, starttime=None, stoptime=None):
        """
        Get lib_files record(s) from the M&C database.

        Parameters:
        ------------
        filename: string
            filename to get records for. If none, obsid, starttime and stoptime
            will be used.

        obsid: long
            obsid to get records for. If starttime and filename are none,
            all files for this obsid will be returned. If none, all obsid will
            be included.

        starttime: astropy time object
            time to look for records after. If starttime, filename and obsid
            are all none, all records will be returned

        stoptime: astropy time object
            last time to get records for. If none, only the first record after
            starttime will be returned.

        Returns:
        --------
        list of LibFiles objects
        """
        from .librarian import LibFiles

        if filename is not None:
            file_list = self.query(LibFiles).filter(
                LibFiles.filename == filename).all()
        else:
            if starttime is not None:
                file_list = self._time_filter(LibFiles, 'time', starttime,
                                              stoptime=stoptime, filter_column='obsid',
                                              filter_value=obsid)
            else:
                if obsid is not None:
                    file_list = self.query(LibFiles).filter(
                        LibFiles.obsid == obsid).all()
                else:
                    file_list = self.query(LibFiles).all()

        return file_list

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

    def get_rtp_status(self, starttime, stoptime=None):
        """
        Get rtp_status record(s) from the M&C database.

        Parameters:
        ------------
        starttime: astropy time object
            time to look for records after

        stoptime: astropy time object
            last time to get records for. If none, only the first record after
            starttime will be returned.

        Returns:
        --------
        list of RTPStatus objects
        """
        from .rtp import RTPStatus

        return self._time_filter(RTPStatus, 'time', starttime,
                                 stoptime=stoptime)

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

    def get_rtp_process_event(self, starttime, stoptime=None, obsid=None):
        """
        Get rtp_process_event record(s) from the M&C database.

        Parameters:
        ------------
        starttime: astropy time object
            time to look for records after

        stoptime: astropy time object
            last time to get records for. If none, only the first record after
            starttime will be returned.

        obsid: long
            obsid to get records for. If none, all obsid will be included.

        Returns:
        --------
        list of RTPProcessEvent objects
        """
        from .rtp import RTPProcessEvent

        return self._time_filter(RTPProcessEvent, 'time', starttime,
                                 stoptime=stoptime, filter_column='obsid',
                                 filter_value=obsid)

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

    def get_rtp_process_record(self, starttime, stoptime=None, obsid=None):
        """
        Get rtp_process_record record(s) from the M&C database.

        Parameters:
        ------------
        starttime: astropy time object
            time to look for records after

        stoptime: astropy time object
            last time to get records for. If none, only the first record after
            starttime will be returned.

        obsid: long
            obsid to get records for. If none, all obsid will be included.

        Returns:
        --------
        list of RTPProcessEvent objects
        """
        from .rtp import RTPProcessRecord

        return self._time_filter(RTPProcessRecord, 'time', starttime,
                                 stoptime=stoptime, filter_column='obsid',
                                 filter_value=obsid)

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

    def get_rtp_task_resource_record(self, starttime=None, stoptime=None, obsid=None,
                                     task_name=None):
        """
        Get rtp_task_resource_record from the M&C database.

        Parameters:
        ------------
        starttime: astropy time object
            time to look for records after; applies to start_time column.
            Ignored if both obsid and task_name are not None
        stoptime: astropy time object
            last time to get records for. If none, only the first record after
            starttime will be returned.
            Ignored if both obsid and task_name are not None
        obsid: long
            obsid to get records for. If none, all obsid will be included
        task_name: string
            task_name to get records for. If none, all tasks will be included

        Returns:
        -----------
        list of RTPTaskResourceRecord objects

        """
        from .rtp import RTPTaskResourceRecord

        if task_name is None:
            if starttime is not None:
                return self._time_filter(RTPTaskResourceRecord, 'start_time', starttime,
                                         stoptime=stoptime, filter_column='obsid',
                                         filter_value=obsid)
            elif obsid is not None:
                return self.query(RTPTaskResourceRecord).filter(
                    RTPTaskResourceRecord.obsid == obsid).all()
            else:
                raise ValueError('Starttime or obsid must be specified')
        elif obsid is None:
            if starttime is None:
                raise ValueError('Starttime or obsid must be specified')
            return self._time_filter(RTPTaskResourceRecord, 'start_time', starttime,
                                     stoptime=stoptime, filter_column='task_name',
                                     filter_value=task_name)
        else:
            return self.query(RTPTaskResourceRecord).filter(
                RTPTaskResourceRecord.obsid == obsid,
                RTPTaskResourceRecord.task_name == task_name).all()

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

    def get_weather_data(self, starttime, stoptime=None, variable=None):
        """
        Get weather_data record(s) from the M&C database.

        Parameters:
        ------------
        starttime: astropy time object
            time to look for records after

        stoptime: astropy time object
            last time to get records for. If none, only the first record after
            starttime will be returned.

        variable: string
            Name of variable to get records for, must be a key in weather.weather_sensor_dict.
            If none, all variables will be included.

        Returns:
        --------
        list of WeatherData objects
        """
        from .weather import weather_sensor_dict, WeatherData
        if variable is not None:
            if variable not in weather_sensor_dict.keys():
                raise ValueError('variable must be a key in weather_sensor_dict.')

        return self._time_filter(WeatherData, 'time', starttime,
                                 stoptime=stoptime, filter_column='variable',
                                 filter_value=variable)

    def write_weather_files(self, start_time, stop_time, variables=None):
        """Dump the weather data to text files in the current directory, to aid in
        diagnostics.

        Parameters:
        ------------
        start_time: astropy time object or None
            time to start getting history.
        stop_time: astropy time object or None
            time to stop getting history.
        variables: string or None
            A comma-separated list of names of variables to get data for, as
            named in the Python variable
            `hera_mc.weather.weather_sensor_dict`. If None, data for all
            variables will be written.

        """
        # Avoid _time_filter since it loads every row into an in-memory list, which
        # could get huge.

        from .cm_utils import listify
        from .weather import WeatherData, weather_sensor_dict

        if variables is None:
            variables = list(weather_sensor_dict.keys())
        else:
            variables = listify(variables)

            for v in variables:
                if v not in weather_sensor_dict:
                    raise ValueError('unknown weather variable name %r' % v)

        q = self.query(WeatherData).filter(WeatherData.variable.in_(variables))

        if start_time is not None:
            if stop_time is not None:
                q = q.filter(WeatherData.time.between(start_time.gps, stop_time.gps))
            else:
                q = q.filter(WeatherData.time >= start_time.gps)
        elif stop_time is not None:
            q = q.filter(WeatherData.time <= stop_time.gps)

        q = q.order_by(WeatherData.time)
        files = dict((v, open(v + '.txt', 'wt')) for v in variables)

        for item in q:
            print('{}\t{}'.format(item.astropy_time, item.value), file=files[item.variable])

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

    def get_node_sensor_readings(self, starttime, stoptime=None, nodeID=None):
        """
        Get node_sensor record(s) from the M&C database.

        Parameters:
        ------------
        starttime: astropy time object
            time to look for records after

        stoptime: astropy time object
            last time to get records for. If none, only the first record after
            starttime will be returned.

        nodeID: integer
            node number (integer running from 1 to 30)

        Returns:
        --------
        list of NodeSensor objects
        """
        from .node import NodeSensor

        return self._time_filter(NodeSensor, 'time', starttime,
                                 stoptime=stoptime, filter_column='node',
                                 filter_value=nodeID)

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

    def get_node_power_status(self, starttime, stoptime=None, nodeID=None):
        """
        Get node power status record(s) from the M&C database.

        Parameters:
        ------------
        starttime: astropy time object
            time to look for records after

        stoptime: astropy time object
            last time to get records for. If none, only the first record after
            starttime will be returned.

        nodeID: integer
            node number (integer running from 1 to 30)

        Returns:
        --------
        list of NodePowerStatus objects
        """
        from .node import NodePowerStatus

        return self._time_filter(NodePowerStatus, 'time', starttime,
                                 stoptime=stoptime, filter_column='node',
                                 filter_value=nodeID)

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
        node_powers = self.get_node_power_status(starttime, stoptime=stoptime, nodeID=nodeID)
        if len(node_powers) > 0:
            latest_powers = node_powers[-1]
            drop_part = []
            for partname in part:
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

            if not dryrun:
                import nodeControl

                node_controller = nodeControl.NodeControl(nodeID, serverAddress=nodeServerAddress)
                getattr(node_controller, power_command_part_dict[partname])(command)

                self.add(command_obj)
            else:
                command_list.append(command_obj)

        if dryrun:
            return command_list

    def get_node_power_command(self, starttime, stoptime=None, nodeID=None):
        """
        Get node power command record(s) from the M&C database.

        Parameters:
        ------------
        starttime: astropy time object
            time to look for records after

        stoptime: astropy time object
            last time to get records for. If none, only the first record after
            starttime will be returned.

        nodeID: integer
            node number (integer running from 1 to 30)

        Returns:
        --------
        list of NodePowerCommand objects
        """
        from .node import NodePowerCommand

        return self._time_filter(NodePowerCommand, 'time', starttime,
                                 stoptime=stoptime, filter_column='node',
                                 filter_value=nodeID)

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
