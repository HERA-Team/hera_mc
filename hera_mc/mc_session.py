# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import func
from astropy.time import Time
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

    def _time_filter(self, table_object, time_column, starttime, stoptime=None,
                     filter_column=None, filter_value=None):
        '''
        A helper method to fiter entries by time. Used by most get methods
        on this object.

        Parameters:
        table_object: object
            Table object to query.

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
                result_list = self.query(table_object).filter(
                    getattr(table_object, filter_column) == filter_value,
                    getattr(table_object, time_column).between(starttime.gps, stoptime.gps)).all()
            else:
                result_list = self.query(table_object).filter(
                    getattr(table_object, time_column).between(starttime.gps, stoptime.gps)).all()
        else:
            if filter_value is not None:
                result_list = self.query(table_object).filter(
                    getattr(table_object, filter_column) == filter_value,
                    getattr(table_object, time_column) >= starttime.gps).order_by(
                        getattr(table_object, time_column)).limit(1).all()
            else:
                result_list = self.query(table_object).filter(
                    getattr(table_object, time_column) >= starttime.gps).order_by(
                        getattr(table_object, time_column)).limit(1).all()

        return result_list

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
        import geo_handling

        h = geo_handling.Handling(session=self)
        hera_cofa = h.cofa()

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

        obs_list = self._time_filter(Observation, 'obsid', starttime,
                                     stoptime=stoptime)

        return obs_list

    def add_server_status(self, subsystem, hostname, ip_address, system_time, num_cores,
                          cpu_load_pct, uptime_days, memory_used_pct, memory_size_gb,
                          disk_space_pct, disk_size_gb, network_bandwidth_mbs=None):
        """
        Add a new subsystem server_status to the M&C database.

        Parameters:
        ------------
        subsytem: string
            name of subsytem. Must be one of ['rtp', 'lib']
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
        subsytem: string
            name of subsytem. Must be one of ['rtp', 'lib']

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

        status_list = self._time_filter(ServerStatus, 'mc_time', starttime,
                                        stoptime=stoptime, filter_column='hostname',
                                        filter_value=hostname)

        return status_list

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

        status_list = self._time_filter(LibStatus, 'time', starttime,
                                        stoptime=stoptime)

        return status_list

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

        status_list = self._time_filter(LibRAIDStatus, 'time', starttime,
                                        stoptime=stoptime, filter_column='hostname',
                                        filter_value=hostname)

        return status_list

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

        error_list = self._time_filter(LibRAIDErrors, 'time', starttime,
                                       stoptime=stoptime, filter_column='hostname',
                                       filter_value=hostname)

        return error_list

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

        status_list = self._time_filter(LibRemoteStatus, 'time', starttime,
                                        stoptime=stoptime, filter_column='remote_name',
                                        filter_value=remote_name)

        return status_list

    def add_lib_file(self, filename, obsid, time, size_gb):
        """
        Add a new lib_file row.

        Parameters:
        ------------
        filename: string
            name of file created
        obsid: long
            observation obsid (Foreign key into Observation)
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
            all files for this obsid will be returned. If none, all obsid will be included.

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
            last time to get records for. If none, only the first record after starttime will be returned.

        Returns:
        --------
        list of RTPStatus objects
        """
        from .rtp import RTPStatus

        status_list = self._time_filter(RTPStatus, 'time', starttime,
                                        stoptime=stoptime)

        return status_list

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

        event_list = self._time_filter(RTPProcessEvent, 'time', starttime,
                                       stoptime=stoptime, filter_column='obsid',
                                       filter_value=obsid)

        return event_list

    def add_rtp_process_record(self, time, obsid, pipeline_list, git_version, git_hash):
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
        git_version: string
            RTP git version
        git_hash: string
            RTP git hash
        """
        from .rtp import RTPProcessRecord

        self.add(RTPProcessRecord.create(time, obsid, pipeline_list,
                                         git_version, git_hash))

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

        record_list = self._time_filter(RTPProcessRecord, 'time', starttime,
                                        stoptime=stoptime, filter_column='obsid',
                                        filter_value=obsid)

        return record_list

    def add_paper_temps(self, read_time, temp_list):
        """
        Add a new PaperTemperatures record to the M&C database.

        This list is usually parsed from the text file on tmon.

        Parameters:
        ------------
        read_time: float or astropy time object
            if float: jd time of temperature read

        temp_list: List of temperatures. See temperatures.py for details.
        """
        from .temperatures import PaperTemperatures

        self.add(PaperTemperatures.new_from_text_row(read_time, temp_list))

    def get_paper_temps(self, starttime, stoptime=None):
        """
        get sets of temperature records.

        Parameters:
        ------------
        starttime: astropy time object
            time to look for records after

        stoptime: astropy time object
            last time to get records for. If none, only the first record after
            starttime will be returned.

        """
        from .temperatures import PaperTemperatures

        ptemp_list = self._time_filter(PaperTemperatures, 'time', starttime,
                                       stoptime=stoptime)

        return ptemp_list
