# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

from sqlalchemy.orm import Session
from astropy.time import Time
import datetime
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

    def add_obs(self, starttime, stoptime, obsid=None):
        """
        Add a new observation to the M&C database.

        Parameters:
        ------------
        starttime: astropy time object
            observation starttime
        stoptime: astropy time object
            observation stoptime
        obsid: long integer
            observation identification number. If not provided, will be set
            to the gps second corresponding to the starttime using floor.
        """
        from .observations import Observation

        self.add(Observation.new_observation(starttime, stoptime, obsid=obsid))

    def get_obs(self, obsid=None):
        """
        Get observation(s) from the M&C database.

        Parameters:
        ------------
        obsid: long integer
            observation identification number, generally the gps second
            corresponding to the observation start time.
            if not set, all obsids will be returned.

        Returns:
        --------
        list of Observation objects
        """
        from .observations import Observation

        if obsid is None:
            obs_list = self.query(Observation).all()
        else:
            obs_list = self.query(Observation).filter_by(obsid=obsid).all()

        return obs_list

    def add_server_status(self, hostname, ip_address, system_time, num_cores,
                          cpu_load_pct, uptime_days, memory_used_pct, memory_size_gb,
                          disk_space_pct, disk_size_gb, network_bandwidth_mbs=None):
        """
        Add a new server_status to the M&C database.

        Parameters:
        ------------
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
            Network bandwidth in MB/s. Can be null if not applicable
        """
        from .server_status import ServerStatus

        self.add(ServerStatus.new_status(hostname, ip_address, system_time, num_cores,
                                         cpu_load_pct, uptime_days, memory_used_pct,
                                         memory_size_gb, disk_space_pct, disk_size_gb,
                                         network_bandwidth_mbs=network_bandwidth_mbs))

    def get_server_status(self, starttime, stoptime=None, hostname=None):
        """
        Get server_status record(s) from the M&C database.

        Parameters:
        ------------
        starttime: datetime
            time to look for records after

        stoptime: datetime
            last time to get records for. If none, only the first record after starttime will be returned.

        hostname: string
            hostname to get records for. If none, all hostnames will be included.

        Returns:
        --------
        list of ServerStatus objects
        """
        from .server_status import ServerStatus

        if not isinstance(starttime, datetime.datetime):
            raise ValueError('unrecognized "starttime" value: %r' % (starttime,))

        if stoptime is not None:
            if not isinstance(stoptime, datetime.datetime):
                raise ValueError('unrecognized "stoptime" value: %r' % (stoptime,))

        if stoptime is not None:
            if hostname is not None:
                status_list = self.query(ServerStatus).filter(
                    ServerStatus.hostname == hostname,
                    ServerStatus.mc_time.between(starttime, stoptime)).all()
            else:
                status_list = self.query(ServerStatus).filter(
                    ServerStatus.mc_time.between(starttime, stoptime)).all()
        else:
            if hostname is not None:
                status_list = self.query(ServerStatus).filter(
                    ServerStatus.hostname == hostname,
                    ServerStatus.mc_time >= starttime).order_by(
                        ServerStatus.mc_time).limit(1).all()
            else:
                status_list = self.query(ServerStatus).filter(
                    ServerStatus.mc_time >= starttime).order_by(
                        ServerStatus.mc_time).limit(1).all()

        return status_list

    def add_rtp_status(self, time, status, event_min_elapsed, num_processes,
                       restart_hours_elapsed):
        """
        Add a new rtp_status object.

        Parameters:
        ------------
        time: datetime
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

        self.add(RTPStatus.new_status(time, status, event_min_elapsed, num_processes,
                                      restart_hours_elapsed))

    def get_rtp_status(self, starttime, stoptime=None):
        """
        Get server_status record(s) from the M&C database.

        Parameters:
        ------------
        starttime: datetime
            time to look for records after

        stoptime: datetime
            last time to get records for. If none, only the first record after starttime will be returned.

        Returns:
        --------
        list of RTPStatus objects
        """
        from .rtp import RTPStatus

        if not isinstance(starttime, datetime.datetime):
            raise ValueError('unrecognized "starttime" value: %r' % (starttime,))

        if stoptime is not None:
            if not isinstance(stoptime, datetime.datetime):
                raise ValueError('unrecognized "stoptime" value: %r' % (stoptime,))

        if stoptime is not None:
            status_list = self.query(RTPStatus).filter(
                RTPStatus.time.between(starttime, stoptime)).all()
        else:
            status_list = self.query(RTPStatus).filter(
                RTPStatus.time >= starttime).order_by(
                    RTPStatus.time).limit(1).all()

        return status_list

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

        If only starttime is specified, get first record after starttime,
           if both starttime and stoptime are specified, get records between
           starttime and stoptime.

        Parameters:
        ------------
        starttime: float or astropy time object
            if float: jd time of starttime

        stoptime: float or astropy time object
            if float: jd time of temperature read

        """
        from .temperatures import PaperTemperatures

        if isinstance(starttime, Time):
            t_start = starttime.utc
        elif isinstance(starttime, float):
            t_start = Time(starttime, format='jd', scale='utc')
        else:
            raise ValueError('unrecognized "starttime" value: %r' % (starttime,))

        if stoptime is not None:
            if isinstance(stoptime, Time):
                t_stop = stoptime.utc
            elif isinstance(starttime, float):
                t_stop = Time(stoptime, format='jd', scale='utc')
            else:
                raise ValueError('unrecognized "stoptime" value: %r' % (stoptime,))

        if stoptime is not None:
            ptemp_list = self.query(PaperTemperatures).filter(
                PaperTemperatures.gps_time.between(t_start.gps, t_stop.gps)).all()
        else:
            ptemp_list = self.query(PaperTemperatures).filter(
                PaperTemperatures.gps_time >= t_start.gps).order_by(
                    PaperTemperatures.gps_time).limit(1).all()

        return ptemp_list

    def get_station_type(self):
        """
        returns a dictionary of sub-arrays
             [prefix]{'Description':'...', 'plot_marker':'...', 'stations':[]}
        """
        from .geo_location import GeoLocation
        from .geo_location import StationType

        station_data = self.query(StationType).all()
        stations = {}
        for sta in station_data:
            stations[sta.prefix] = {'Name': sta.station_type_name, 'Description': sta.description,
                                    'Marker': sta.plot_marker, 'Stations': []}
        locations = self.query(GeoLocation).all()
        for loc in locations:
            for k in stations.keys():
                if loc.station_name[:len(k)] == k:
                    stations[k]['Stations'].append(loc.station_name)
        return stations
