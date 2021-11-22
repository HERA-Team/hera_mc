# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Node M&C info from the node's Redis database."""

import numpy as np
from sqlalchemy import Column, BigInteger, Integer, Float, Boolean, String

from . import MCDeclarativeBase
from . import cm_utils

# the address of a redis database being used as a clearing house for meta-data
# and message passing which the node server has access to and watches
defaultServerAddress = "redishost"

# These four dictionaries convert the keyname in psql to redis - psql-key: redis-key
sensor_key_dict = {
    "top_sensor_temp": "temp_top",
    "middle_sensor_temp": "temp_mid",
    "bottom_sensor_temp": "temp_bot",
    "humidity_sensor_temp": "temp_humid",
    "humidity": "humid",
}

power_status_key_dict = {
    "snap_relay_powered": "power_snap_relay",
    "snap0_powered": "power_snap_0",
    "snap1_powered": "power_snap_1",
    "snap2_powered": "power_snap_2",
    "snap3_powered": "power_snap_3",
    "pam_powered": "power_pam",
    "fem_powered": "power_fem",
}

# key is part to command, value is function name in hera_node_mc
power_command_part_dict = {
    "snap_relay": "power_snap_relay",
    "snap0": "power_snap_0",
    "snap1": "power_snap_1",
    "snap2": "power_snap_2",
    "snap3": "power_snap_3",
    "pam": "power_pam",
    "fem": "power_fem",
    "reset": "reset",
}

wr_key_dict = {
    "board_info_str": "board_info_str",
    "aliases": "aliases",
    "ip": "ip",
    "mode": "mode",
    "serial": "serial",
    "node_time": "timestamp",
    "temperature": "temp",
    "build_date": "sw_build_date",
    "gw_date": "wr_gw_date",
    "gw_version": "wr_gw_version",
    "gw_id": "wr_gw_id",
    "build_hash": "wr_build",
    "manufacture_tag": "wr_fru_custom",
    "manufacture_device": "wr_fru_device",
    "manufacture_date": "wr_fru_fid",
    "manufacture_partnum": "wr_fru_partnum",
    "manufacture_serial": "wr_fru_serial",
    "manufacture_vendor": "wr_fru_vendor",
    "port0_ad": "wr0_ad",
    "port0_link_asymmetry_ps": "wr0_asym",
    "port0_manual_phase_ps": "wr0_aux",
    "port0_clock_offset_ps": "wr0_cko",
    "port0_cable_rt_delay_ps": "wr0_crtt",
    "port0_master_slave_delay_ps": "wr0_dms",
    "port0_master_rx_phy_delay_ps": "wr0_drxm",
    "port0_slave_rx_phy_delay_ps": "wr0_drxs",
    "port0_master_tx_phy_delay_ps": "wr0_dtxm",
    "port0_slave_tx_phy_delay_ps": "wr0_dtxs",
    "port0_hd": "wr0_hd",
    "port0_link": "wr0_lnk",
    "port0_lock": "wr0_lock",
    "port0_md": "wr0_md",
    "port0_rt_time_ps": "wr0_mu",
    "port0_nsec": "wr0_nsec",
    "port0_packets_received": "wr0_rx",
    "port0_phase_setpoint_ps": "wr0_setp",
    "port0_servo_state": "wr0_ss",
    "port0_sv": "wr0_sv",
    "port0_sync_source": "wr0_syncs",
    "port0_packets_sent": "wr0_tx",
    "port0_update_counter": "wr0_ucnt",
    "port0_time": "wr0_sec",
    "port1_ad": "wr1_ad",
    "port1_link_asymmetry_ps": "wr1_asym",
    "port1_manual_phase_ps": "wr1_aux",
    "port1_clock_offset_ps": "wr1_cko",
    "port1_cable_rt_delay_ps": "wr1_crtt",
    "port1_master_slave_delay_ps": "wr1_dms",
    "port1_master_rx_phy_delay_ps": "wr1_drxm",
    "port1_slave_rx_phy_delay_ps": "wr1_drxs",
    "port1_master_tx_phy_delay_ps": "wr1_dtxm",
    "port1_slave_tx_phy_delay_ps": "wr1_dtxs",
    "port1_hd": "wr1_hd",
    "port1_link": "wr1_lnk",
    "port1_lock": "wr1_lock",
    "port1_md": "wr1_md",
    "port1_rt_time_ps": "wr1_mu",
    "port1_nsec": "wr1_nsec",
    "port1_packets_received": "wr1_rx",
    "port1_phase_setpoint_ps": "wr1_setp",
    "port1_servo_state": "wr1_ss",
    "port1_sv": "wr1_sv",
    "port1_sync_source": "wr1_syncs",
    "port1_packets_sent": "wr1_tx",
    "port1_update_counter": "wr1_ucnt",
    "port1_time": "wr1_sec",
}
wr_timestamp_keys = {
    "node_time": "unix",
    "build_date": "unix",
    "gw_date": "unix",
    "manufacture_date": "unix",
}


class NodeSensor(MCDeclarativeBase):
    """
    Definition of node sensor table.

    Attributes
    ----------
    time : BigInteger Column
        GPS time of the node data, floored. Part of the primary key.
    node : Integer Column
        Node number. Part of the primary key.
    top_sensor_temp : Float Column
        Temperature of top sensor reported by node in Celsius.
    middle_sensor_temp : Float Column
        Temperature of middle sensor reported by node in Celsius.
    bottom_sensor_temp : Float Column
        Temperature of bottom sensor reported by node in Celsius.
    humidity_sensor_temp : Float Column
        Temperature of the humidity sensor reported by node in Celsius.
    humidity : Float Column
        Percent humidity measurement reported by node.

    """

    __tablename__ = "node_sensor"
    time = Column(BigInteger, primary_key=True)
    node = Column(Integer, primary_key=True)
    top_sensor_temp = Column(Float)
    middle_sensor_temp = Column(Float)
    bottom_sensor_temp = Column(Float)
    humidity_sensor_temp = Column(Float)
    humidity = Column(Float)

    @classmethod
    def create(
        cls,
        time,
        node,
        top_sensor_temp,
        middle_sensor_temp,
        bottom_sensor_temp,
        humidity_sensor_temp,
        humidity,
    ):
        """
        Create a new node sensor object.

        Parameters
        ----------
        time : Time
            Time based on a timestamp reported by node
        node : int
            Node number (within 0 to 29).
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

        Returns
        -------
        NodeSensor object
        """
        sens_time = int(np.floor(time.gps))
        return cls(
            time=sens_time,
            node=node,
            top_sensor_temp=top_sensor_temp,
            middle_sensor_temp=middle_sensor_temp,
            bottom_sensor_temp=bottom_sensor_temp,
            humidity_sensor_temp=humidity_sensor_temp,
            humidity=humidity,
        )


def create_sensor_readings(
    nodeServerAddress=defaultServerAddress, node_list="all", sensor_dict=None
):
    """
    Return a list of node sensor objects with data from the nodes.

    Parameters
    ----------
    nodeServerAddress : str
        Address of server where the node redis database can be accessed.
    node_list : int, list of int, 'all'.
        A list of integers specifying for which nodes to get data.
    sensor_dict : dict
        A dict spoofing the return dict from node_control for testing
        purposes.  If None, calls node_control.get_sensors()

    Returns
    -------
    A list of NodeSensor objects

    """
    node_sensor_list = []
    if sensor_dict is None:
        from node_control import node_control

        node_controller = node_control.NodeControl(
            node_list, redisServer=nodeServerAddress
        )
        sensor_dict = node_controller.get_sensors()

    for node in sensor_dict.keys():
        sensor_data = sensor_dict[node]
        time = cm_utils.get_astropytime(sensor_data["timestamp"], float_format="unix")
        if time is None:
            from warnings import warn

            warn("No timestamp given for node sensor reading -- ignoring this entry.")
        else:
            top_sensor_temp = sensor_data.get(sensor_key_dict["top_sensor_temp"], None)
            middle_sensor_temp = sensor_data.get(
                sensor_key_dict["middle_sensor_temp"], None
            )
            bottom_sensor_temp = sensor_data.get(
                sensor_key_dict["bottom_sensor_temp"], None
            )
            humidity_sensor_temp = sensor_data.get(
                sensor_key_dict["humidity_sensor_temp"], None
            )
            humidity = sensor_data.get(sensor_key_dict["humidity"], None)

            node_sensor_list.append(
                NodeSensor.create(
                    time,
                    node,
                    top_sensor_temp,
                    middle_sensor_temp,
                    bottom_sensor_temp,
                    humidity_sensor_temp,
                    humidity,
                )
            )

    return node_sensor_list


class NodePowerStatus(MCDeclarativeBase):
    """
    Definition of node power status table.

    Attributes
    ----------
    time : BigInteger Column
        GPS time of the node data, floored. Part of the primary key.
    node : Integer Column
        Node number. Part of the primary key.
    snap_relay_powered : Boolean Column
        Power status of the snap relay, True=powered.
    snap0_powered : Boolean Column
        Power status of the SNAP 0 board, True=powered.
    snap1_powered : Boolean Column
        Power status of the SNAP 1 board, True=powered.
    snap2_powered : Boolean Column
        Power status of the SNAP 2 board, True=powered.
    snap3_powered : Boolean Column
        Power status of the SNAP 3 board, True=powered.
    fem_powered : Boolean Column
        Power status of the FEM, True=powered.
    pam_powered : Boolean Column
        Power status of the PAM, True=powered.
    """

    __tablename__ = "node_power_status"
    time = Column(BigInteger, primary_key=True)
    node = Column(Integer, primary_key=True)
    snap_relay_powered = Column(Boolean, nullable=False)
    snap0_powered = Column(Boolean, nullable=False)
    snap1_powered = Column(Boolean, nullable=False)
    snap2_powered = Column(Boolean, nullable=False)
    snap3_powered = Column(Boolean, nullable=False)
    fem_powered = Column(Boolean, nullable=False)
    pam_powered = Column(Boolean, nullable=False)

    @classmethod
    def create(
        cls,
        time,
        node,
        snap_relay_powered,
        snap0_powered,
        snap1_powered,
        snap2_powered,
        snap3_powered,
        fem_powered,
        pam_powered,
    ):
        """
        Create a new node power status object.

        Parameters
        ----------
        time : Time
            Timestamp reported by node.
        node : int
            Node number (within 0 to 29).
        snap_relay_powered: boolean
            Power status of the snap relay, True=powered.
        snap0_powered: boolean
            Power status of the SNAP 0 board, True=powered.
        snap1_powered: boolean
            Power status of the SNAP 1 board, True=powered.
        snap2_powered: boolean
            Power status of the SNAP 2 board, True=powered.
        snap3_powered: boolean
            Power status of the SNAP 3 board, True=powered.
        fem_powered: boolean
            Power status of the FEM, True=powered.
        pam_powered: boolean
            Power status of the PAM, True=powered.

        Returns
        -------
        NodePowerStatus object

        """
        stat_time = int(np.floor(time.gps))
        return cls(
            time=stat_time,
            node=node,
            snap_relay_powered=snap_relay_powered,
            snap0_powered=snap0_powered,
            snap1_powered=snap1_powered,
            snap2_powered=snap2_powered,
            snap3_powered=snap3_powered,
            fem_powered=fem_powered,
            pam_powered=pam_powered,
        )


def create_power_status(
    nodeServerAddress=defaultServerAddress, node_list="all", power_dict=None
):
    """
    Return a list of node power status objects with data from the nodes.

    Parameters
    ----------
    nodeServerAddress : str
        Address of server where the node redis database can be accessed.
    node_list : int, list of int, 'all'
        A list of integers specifying for which nodes to get data.
    power_dict : dict
        A dict containing info as in the return dict from node_control
        for testing purposes. If None, node_control.get_power_status() is called.

    Returns
    -------
    A list of NodePowerStatus objects

    """
    node_power_list = []
    if power_dict is None:
        from node_control import node_control

        node_controller = node_control.NodeControl(
            node_list, redisServer=nodeServerAddress
        )
        power_dict = node_controller.get_power_status()
    for node in power_dict.keys():
        power_data = power_dict[node]
        time = cm_utils.get_astropytime(power_data["timestamp"], float_format="unix")

        # All items in this dictionary are strings.
        snap_relay_powered = power_data[power_status_key_dict["snap_relay_powered"]]
        snap0_powered = power_data[power_status_key_dict["snap0_powered"]]
        snap1_powered = power_data[power_status_key_dict["snap1_powered"]]
        snap2_powered = power_data[power_status_key_dict["snap2_powered"]]
        snap3_powered = power_data[power_status_key_dict["snap3_powered"]]
        pam_powered = power_data[power_status_key_dict["pam_powered"]]
        fem_powered = power_data[power_status_key_dict["fem_powered"]]

        node_power_list.append(
            NodePowerStatus.create(
                time,
                node,
                snap_relay_powered,
                snap0_powered,
                snap1_powered,
                snap2_powered,
                snap3_powered,
                fem_powered,
                pam_powered,
            )
        )
    return node_power_list


class NodePowerCommand(MCDeclarativeBase):
    """
    Definition of node power command table.

    Attributes
    ----------
    time : BigInteger Column
        GPS time of the command, floored. Part of the primary key.
    node : Integer Column
        Node number. Part of the primary key.
    part : String Column
        Part to be powered on/off. Part of the primary key.
    command : String Column
        Command, one of 'on' or 'off'.

    """

    __tablename__ = "node_power_command"
    time = Column(BigInteger, primary_key=True)
    node = Column(Integer, primary_key=True)
    part = Column(String, primary_key=True)
    command = Column(String, nullable=False)

    @classmethod
    def create(cls, time, node, part, command):
        """
        Create a new node power command object.

        Parameters
        ----------
        time : astropy Time
            When time command was sent.
        node : int
            Node number (within 0 to 29).
        part : str
            One of the keys in power_command_part_dict.
        command : {'on', 'off', 'reset'}
            The command that was sent.

        Returns
        -------
        NodePowerCommand object

        """
        comm_time = int(np.floor(time.gps))
        return cls(time=comm_time, node=node, part=part, command=command)


def create_power_command_list(
    nodeServerAddress=defaultServerAddress, node_list="all", power_dict=None
):
    """
    Return a list of node power status objects with data from the nodes.

    Parameters
    ----------
    nodeServerAddress : str
        Address of server where the node redis database can be accessed.
    node_list : list of int
        A list of integers specifying for which nodes to get data.
    power_dict : dict
        A dict containing info as in the return dict from node_control
        for testing purposes. If None, node_control.get_power_command_list is called.

    Returns
    -------
    A list of NodePowerCommand objects

    """
    if power_dict is None:
        from node_control import node_control

        node_controller = node_control.NodeControl(
            node_list, redisServer=nodeServerAddress
        )
        power_dict = node_controller.get_power_command_list()
    node_power_list = []
    for node in power_dict.keys():
        for prt, val in power_dict[node].items():
            time = cm_utils.get_astropytime(val["timestamp"], float_format="unix")
            cmd = val["command"]
            if cmd is not None:
                node_power_list.append(NodePowerCommand.create(time, node, prt, cmd))
    return node_power_list


class NodeWhiteRabbitStatus(MCDeclarativeBase):
    """
    Definition of node white rabbit status table.

    Attributes
    ----------
    node_time: BigInteger Column
        Unix time of the status reported by the node, floored. Part of the primary key.
    node: Integer Column
        Node number. Part of the primary key.
    board_info_str : String Column
        A raw string representing the WR-LEN's response to the `ver` command.
        Relevant parts of this string are individually unpacked in other entries.
    aliases : String Column
        Hostname aliases of this node's WR-LEN (comma separated if more than one).
    ip : String Column
        IP address of this node's WR-LEN
    mode : String Column
        WR-LEN operating mode (eg. "WRC_SLAVE_WR0")
    serial : String Column
        Canonical HERA hostname (~= serial number) of this node's WR-LEN
    temperature : Float Column
        WR-LEN temperature in degrees C
    build_date : BigInteger Column
        Build date of WR-LEN software in floored GPS seconds.
    gw_date : BigInteger Column
        WR-LEN gateware build date in floored GPS seconds.
    gw_version : String Column
        WR-LEN gateware version number
    gw_id : String Column
        WR-LEN gateware ID number
    build_hash : String Column
        WR-LEN build git hash
    manufacture_tag : String Column
        Custom manufacturer tag
    manufacture_device : String Column
        Manufacturer device name designation
    manufacture_date : BigInteger Column
        Manufacturer invoice(?) date
    manufacture_partnum : String Column
        Manufacturer part number
    manufacture_serial : String Column
        Manufacturer serial number
    manufacture_vendor : String Column
        Vendor name
    port0_ad : Integer Column
        ???
    port0_link_asymmetry_ps : Integer Column
        Port 0 total link asymmetry in picosec
    port0_manual_phase_ps : Integer Column
        ??? Port 0 manual phase adjustment in picosec
    port0_clock_offset_ps : Integer Column
        Port 0 Clock offset in picosec
    port0_cable_rt_delay_ps : Integer Column
        Port 0 Cable round-trip delay in picosec
    port0_master_slave_delay_ps : Integer Column
        Port 0 Master-Slave delay in in picosec
    port0_master_rx_phy_delay_ps : Integer Column
        Port 0 Master RX PHY delay in picosec
    port0_slave_rx_phy_delay_ps : Integer Column
        Port 0 Slave RX PHY delay in picosec
    port0_master_tx_phy_delay_ps : Integer Column
        Port 0 Master TX PHY delay in picosec
    port0_slave_tx_phy_delay_ps : Integer Column
        Port 0 Slave TX PHY delay in picosec
    port0_hd : Integer Column
        ???
    port0_link : Boolean Column
        Port 0 link up state
    port0_lock : Boolean Column
        Port 0 timing lock state
    port0_md : Integer Column
        ???
    port0_rt_time_ps : Integer Column
        Port 0 round-trip time in picosec
    port0_nsec : Integer Column
        ???
    port0_packets_received : Integer Column
        Port 0 number of packets received
    port0_phase_setpoint_ps : Integer Column
        Port 0 phase setpoint in picosec
    port0_servo_state : String Column
        Port 0 servo state
    port0_sv : Integer Column
        ???
    port0_sync_source : String Column
        Port 0 source of synchronization (either 'wr0' or 'wr1')
    port0_packets_sent : Integer Column
        Port 0 number of packets transmitted
    port0_update_counter : Integer Column
        Port 0 update counter
    port0_time : BigInteger Column
        Port 0 current time in GPS seconds.
    port1_ad : Integer Column
        ???
    port1_link_asymmetry_ps : Integer Column
        Port 1 total link asymmetry in picosec
    port1_manual_phase_ps : Integer Column
        ??? Port 1 manual phase adjustment in picosec
    port1_clock_offset_ps : Integer Column
        Port 1 Clock offset in picosec
    port1_cable_rt_delay_ps : Integer Column
        Port 1 Cable round-trip delay in picosec
    port1_master_slave_delay_ps : Integer Column
        Port 1 Master-Slave delay in in picosec
    port1_master_rx_phy_delay_ps : Integer Column
        Port 1 Master RX PHY delay in picosec
    port1_slave_rx_phy_delay_ps : Integer Column
        Port 1 Slave RX PHY delay in picosec
    port1_master_tx_phy_delay_ps : Integer Column
        Port 1 Master TX PHY delay in picosec
    port1_slave_tx_phy_delay_ps : Integer Column
        Port 1 Slave TX PHY delay in picosec
    port1_hd : Integer Column
        ???
    port1_link : Boolean Column
        Port 1 link up state
    port1_lock : Boolean Column
        Port 1 timing lock state
    port1_md : Integer Column
        ???
    port1_rt_time_ps : Integer Column
        Port 1 round-trip time in picosec
    port1_nsec : Integer Column
        ???
    port1_packets_received : Integer Column
        Port 1 number of packets received
    port1_phase_setpoint_ps : Integer Column
        Port 1 phase setpoint in picosec
    port1_servo_state : String Column
        Port 1 servo state
    port1_sv : Integer Column
        ???
    port1_sync_source : String Column
        Port 1 source of synchronization (either 'wr0' or 'wr1')
    port1_packets_sent : Integer Column
        Port 1 number of packets transmitted
    port1_update_counter : Integer Column
        Port 1 update counter
    port1_time : BigInteger Column
        Port 1 current time in GPS seconds.

    """

    __tablename__ = "node_white_rabbit_status"
    node_time = Column(BigInteger, primary_key=True)
    node = Column(Integer, primary_key=True)
    board_info_str = Column(String)
    aliases = Column(String)
    ip = Column(String)
    mode = Column(String)
    serial = Column(String)
    temperature = Column(Float)
    build_date = Column(BigInteger)
    gw_date = Column(BigInteger)
    gw_version = Column(String)
    gw_id = Column(String)
    build_hash = Column(String)
    manufacture_tag = Column(String)
    manufacture_device = Column(String)
    manufacture_date = Column(BigInteger)
    manufacture_partnum = Column(String)
    manufacture_serial = Column(String)
    manufacture_vendor = Column(String)
    port0_ad = Column(Integer)
    port0_link_asymmetry_ps = Column(Integer)
    port0_manual_phase_ps = Column(Integer)
    port0_clock_offset_ps = Column(Integer)
    port0_cable_rt_delay_ps = Column(Integer)
    port0_master_slave_delay_ps = Column(Integer)
    port0_master_rx_phy_delay_ps = Column(Integer)
    port0_slave_rx_phy_delay_ps = Column(Integer)
    port0_master_tx_phy_delay_ps = Column(Integer)
    port0_slave_tx_phy_delay_ps = Column(Integer)
    port0_hd = Column(Integer)
    port0_link = Column(Boolean)
    port0_lock = Column(Boolean)
    port0_md = Column(Integer)
    port0_rt_time_ps = Column(Integer)
    port0_nsec = Column(Integer)
    port0_packets_received = Column(Integer)
    port0_phase_setpoint_ps = Column(Integer)
    port0_servo_state = Column(String)
    port0_sv = Column(Integer)
    port0_sync_source = Column(String)
    port0_packets_sent = Column(Integer)
    port0_update_counter = Column(Integer)
    port0_time = Column(BigInteger)
    port1_ad = Column(Integer)
    port1_link_asymmetry_ps = Column(Integer)
    port1_manual_phase_ps = Column(Integer)
    port1_clock_offset_ps = Column(Integer)
    port1_cable_rt_delay_ps = Column(Integer)
    port1_master_slave_delay_ps = Column(Integer)
    port1_master_rx_phy_delay_ps = Column(Integer)
    port1_slave_rx_phy_delay_ps = Column(Integer)
    port1_master_tx_phy_delay_ps = Column(Integer)
    port1_slave_tx_phy_delay_ps = Column(Integer)
    port1_hd = Column(Integer)
    port1_link = Column(Boolean)
    port1_lock = Column(Boolean)
    port1_md = Column(Integer)
    port1_rt_time_ps = Column(Integer)
    port1_nsec = Column(Integer)
    port1_packets_received = Column(Integer)
    port1_phase_setpoint_ps = Column(Integer)
    port1_servo_state = Column(String)
    port1_sv = Column(Integer)
    port1_sync_source = Column(String)
    port1_packets_sent = Column(Integer)
    port1_update_counter = Column(Integer)
    port1_time = Column(BigInteger)

    @classmethod
    def create(cls, col_dict):
        """
        Create a new node white rabbit status object.

        Parameters
        ----------
        col_dict : dict
            dictionary that must contain the following entries:

            node_time : Time
                Timestamp reported by node.
            node : int
                Node number (within 0 to 29).
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
            build_date : Time
                Build date of WR-LEN software.
            gw_date : Time
                WR-LEN gateware build date.
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
            manufacture_date : Time
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
            port0_time : Time
                Time based on Port 0 current TAI time in seconds from UNIX epoch.
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
            port1_time : Time
                Time based on Port 1 current TAI time in seconds from UNIX epoch.

        Returns
        -------
        NodeWhiteRabbitStatus object

        """
        for key in wr_timestamp_keys:
            try:
                col_dict[key] = int(np.floor(col_dict[key].gps))
            except (KeyError, AttributeError):
                continue
        return cls(**col_dict)


def create_wr_status(
    nodeServerAddress=defaultServerAddress, node_list="all", wr_status_dict=None
):
    """
    Return a list of node white rabbit status objects with data from the nodes.

    Parameters
    ----------
    nodeServerAddress: str
        Address of server where the node redis database can be accessed.
    node_list: int, list of int, 'all'
        A list of integers specifying for which nodes to get data.
    wr_status_dict: dict
        A dict spoofing the return dict from node_controller for testing
        purposes.  If None, calls node_controller.get_wr_status()

    Returns
    -------
    A list of NodeWhiteRabbitStatus objects

    """
    wr_status_list = []
    if wr_status_dict is None:
        from node_control import node_control

        node_controller = node_control.NodeControl(
            node_list, redisServer=nodeServerAddress
        )
        wr_status_dict = node_controller.get_wr_status()

    for node in wr_status_dict.keys():
        wr_data = wr_status_dict[node]
        col_dict = {"node": node}
        for sql_key, sens_key in wr_key_dict.items():
            wr_data_value = wr_data[sens_key]
            if sql_key in wr_timestamp_keys and wr_data_value is not None:
                fmt = wr_timestamp_keys[sql_key]
                col_dict[sql_key] = cm_utils.get_astropytime(
                    wr_data_value, float_format=fmt
                )
            elif isinstance(wr_data_value, float) and np.isnan(wr_data_value):
                col_dict[sql_key] = None
            elif sql_key == "aliases" and wr_data_value is not None:
                if len(wr_data_value) == 0:
                    col_dict[sql_key] = None
                else:
                    col_dict[sql_key] = ", ".join(wr_data_value)
            else:
                col_dict[sql_key] = wr_data_value
        wr_status_list.append(NodeWhiteRabbitStatus.create(col_dict))

    return wr_status_list
