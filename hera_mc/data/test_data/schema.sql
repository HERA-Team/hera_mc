--
-- PostgreSQL database dump
--

-- Dumped from database version 12.1
-- Dumped by pg_dump version 12.1

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: rtp_process_enum; Type: TYPE; Schema: public; Owner: ddeboer
--

CREATE TYPE public.rtp_process_enum AS ENUM (
    'queued',
    'started',
    'finished',
    'error'
);


ALTER TYPE public.rtp_process_enum OWNER TO ddeboer;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO ddeboer;

--
-- Name: ant_metrics; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.ant_metrics (
    obsid bigint NOT NULL,
    ant integer NOT NULL,
    pol character varying NOT NULL,
    metric character varying NOT NULL,
    mc_time bigint NOT NULL,
    val double precision NOT NULL
);


ALTER TABLE public.ant_metrics OWNER TO ddeboer;

--
-- Name: antenna_status; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.antenna_status (
    "time" bigint NOT NULL,
    antenna_number integer NOT NULL,
    antenna_feed_pol character varying NOT NULL,
    snap_hostname character varying,
    snap_channel_number integer,
    adc_mean double precision,
    adc_rms double precision,
    adc_power double precision,
    pam_atten integer,
    pam_power double precision,
    eq_coeffs character varying,
    fem_current double precision,
    fem_id character varying,
    fem_temp double precision,
    fem_voltage double precision,
    histogram character varying,
    pam_current double precision,
    pam_id character varying,
    pam_voltage double precision,
    fem_imu_phi double precision,
    fem_imu_theta double precision,
    fem_lna_power boolean,
    fem_switch character varying,
    fft_overflow boolean
);


ALTER TABLE public.antenna_status OWNER TO ddeboer;

--
-- Name: apriori_antenna; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.apriori_antenna (
    antenna text NOT NULL,
    start_gpstime bigint NOT NULL,
    stop_gpstime bigint,
    status text NOT NULL
);


ALTER TABLE public.apriori_antenna OWNER TO ddeboer;

--
-- Name: array_metrics; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.array_metrics (
    obsid bigint NOT NULL,
    metric character varying NOT NULL,
    mc_time bigint NOT NULL,
    val double precision NOT NULL
);


ALTER TABLE public.array_metrics OWNER TO ddeboer;

--
-- Name: autocorrelations; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.autocorrelations (
    id bigint NOT NULL,
    "time" timestamp without time zone NOT NULL,
    antnum integer NOT NULL,
    polarization character varying(1) NOT NULL,
    measurement_type smallint NOT NULL,
    value double precision NOT NULL
);


ALTER TABLE public.autocorrelations OWNER TO ddeboer;

--
-- Name: autocorrelations_id_seq; Type: SEQUENCE; Schema: public; Owner: ddeboer
--

CREATE SEQUENCE public.autocorrelations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.autocorrelations_id_seq OWNER TO ddeboer;

--
-- Name: autocorrelations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ddeboer
--

ALTER SEQUENCE public.autocorrelations_id_seq OWNED BY public.autocorrelations.id;


--
-- Name: cm_version; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.cm_version (
    update_time bigint NOT NULL,
    git_hash character varying(64) NOT NULL
);


ALTER TABLE public.cm_version OWNER TO ddeboer;

--
-- Name: connections; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.connections (
    upstream_part character varying(64) NOT NULL,
    up_part_rev character varying(32) NOT NULL,
    downstream_part character varying(64) NOT NULL,
    down_part_rev character varying(64) NOT NULL,
    upstream_output_port character varying(64) NOT NULL,
    downstream_input_port character varying(64) NOT NULL,
    start_gpstime bigint NOT NULL,
    stop_gpstime bigint
);


ALTER TABLE public.connections OWNER TO ddeboer;

--
-- Name: correlator_config_active_snap; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.correlator_config_active_snap (
    config_hash character varying NOT NULL,
    hostname character varying NOT NULL
);


ALTER TABLE public.correlator_config_active_snap OWNER TO ddeboer;

--
-- Name: correlator_config_command; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.correlator_config_command (
    "time" bigint NOT NULL,
    command character varying NOT NULL,
    config_hash character varying NOT NULL
);


ALTER TABLE public.correlator_config_command OWNER TO ddeboer;

--
-- Name: correlator_config_file; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.correlator_config_file (
    config_hash character varying NOT NULL,
    filename character varying NOT NULL
);


ALTER TABLE public.correlator_config_file OWNER TO ddeboer;

--
-- Name: correlator_config_input_index; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.correlator_config_input_index (
    config_hash character varying NOT NULL,
    correlator_index integer NOT NULL,
    hostname character varying NOT NULL,
    antenna_index_position integer NOT NULL
);


ALTER TABLE public.correlator_config_input_index OWNER TO ddeboer;

--
-- Name: correlator_config_params; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.correlator_config_params (
    config_hash character varying NOT NULL,
    parameter character varying NOT NULL,
    value character varying NOT NULL
);


ALTER TABLE public.correlator_config_params OWNER TO ddeboer;

--
-- Name: correlator_config_phase_switch_index; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.correlator_config_phase_switch_index (
    config_hash character varying NOT NULL,
    hostname character varying NOT NULL,
    phase_switch_index integer NOT NULL,
    antpol_index_position integer NOT NULL
);


ALTER TABLE public.correlator_config_phase_switch_index OWNER TO ddeboer;

--
-- Name: correlator_config_status; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.correlator_config_status (
    "time" bigint NOT NULL,
    config_hash character varying NOT NULL
);


ALTER TABLE public.correlator_config_status OWNER TO ddeboer;

--
-- Name: correlator_config_status_time_seq; Type: SEQUENCE; Schema: public; Owner: ddeboer
--

CREATE SEQUENCE public.correlator_config_status_time_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.correlator_config_status_time_seq OWNER TO ddeboer;

--
-- Name: correlator_config_status_time_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ddeboer
--

ALTER SEQUENCE public.correlator_config_status_time_seq OWNED BY public.correlator_config_status."time";


--
-- Name: correlator_control_command; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.correlator_control_command (
    "time" bigint NOT NULL,
    command character varying NOT NULL
);


ALTER TABLE public.correlator_control_command OWNER TO ddeboer;

--
-- Name: correlator_control_state; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.correlator_control_state (
    "time" bigint NOT NULL,
    state_type character varying NOT NULL,
    state boolean NOT NULL
);


ALTER TABLE public.correlator_control_state OWNER TO ddeboer;

--
-- Name: correlator_software_versions; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.correlator_software_versions (
    "time" bigint NOT NULL,
    package character varying NOT NULL,
    version character varying NOT NULL
);


ALTER TABLE public.correlator_software_versions OWNER TO ddeboer;

--
-- Name: correlator_take_data_arguments; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.correlator_take_data_arguments (
    "time" bigint NOT NULL,
    command character varying NOT NULL,
    starttime_sec bigint NOT NULL,
    starttime_ms integer NOT NULL,
    duration double precision NOT NULL,
    acclen_spectra integer NOT NULL,
    integration_time double precision NOT NULL,
    tag character varying NOT NULL
);


ALTER TABLE public.correlator_take_data_arguments OWNER TO ddeboer;

--
-- Name: daemon_status; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.daemon_status (
    name character varying(32) NOT NULL,
    hostname character varying(32) NOT NULL,
    jd bigint NOT NULL,
    "time" bigint NOT NULL,
    status character varying(32) NOT NULL
);


ALTER TABLE public.daemon_status OWNER TO ddeboer;

--
-- Name: dubitable; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.dubitable (
    start_gpstime bigint NOT NULL,
    stop_gpstime bigint,
    ant_list text NOT NULL
);


ALTER TABLE public.dubitable OWNER TO ddeboer;

--
-- Name: dubitable_start_gpstime_seq; Type: SEQUENCE; Schema: public; Owner: ddeboer
--

CREATE SEQUENCE public.dubitable_start_gpstime_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dubitable_start_gpstime_seq OWNER TO ddeboer;

--
-- Name: dubitable_start_gpstime_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ddeboer
--

ALTER SEQUENCE public.dubitable_start_gpstime_seq OWNED BY public.dubitable.start_gpstime;


--
-- Name: geo_location; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.geo_location (
    station_name character varying(64) NOT NULL,
    station_type_name character varying(64) NOT NULL,
    datum character varying(64),
    tile character varying(64),
    northing double precision,
    easting double precision,
    elevation double precision,
    created_gpstime bigint NOT NULL
);


ALTER TABLE public.geo_location OWNER TO ddeboer;

--
-- Name: hera_autos; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.hera_autos (
    "time" bigint NOT NULL,
    antenna_number integer NOT NULL,
    antenna_feed_pol character varying NOT NULL,
    measurement_type character varying NOT NULL,
    value double precision NOT NULL
);


ALTER TABLE public.hera_autos OWNER TO ddeboer;

--
-- Name: hera_obs; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.hera_obs (
    obsid bigint NOT NULL,
    lst_start_hr double precision NOT NULL,
    jd_start double precision NOT NULL,
    starttime double precision NOT NULL,
    stoptime double precision NOT NULL
);


ALTER TABLE public.hera_obs OWNER TO ddeboer;

--
-- Name: lib_files; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.lib_files (
    filename character varying(256) NOT NULL,
    obsid bigint,
    "time" bigint NOT NULL,
    size_gb double precision NOT NULL
);


ALTER TABLE public.lib_files OWNER TO ddeboer;

--
-- Name: lib_raid_errors_id_seq; Type: SEQUENCE; Schema: public; Owner: ddeboer
--

CREATE SEQUENCE public.lib_raid_errors_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.lib_raid_errors_id_seq OWNER TO ddeboer;

--
-- Name: lib_raid_errors; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.lib_raid_errors (
    "time" bigint NOT NULL,
    hostname character varying(32) NOT NULL,
    disk character varying NOT NULL,
    log text NOT NULL,
    id bigint DEFAULT nextval('public.lib_raid_errors_id_seq'::regclass) NOT NULL
);


ALTER TABLE public.lib_raid_errors OWNER TO ddeboer;

--
-- Name: lib_raid_status; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.lib_raid_status (
    "time" bigint NOT NULL,
    hostname character varying(32) NOT NULL,
    num_disks integer NOT NULL,
    info text NOT NULL
);


ALTER TABLE public.lib_raid_status OWNER TO ddeboer;

--
-- Name: lib_remote_status; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.lib_remote_status (
    "time" bigint NOT NULL,
    remote_name character varying(32) NOT NULL,
    ping_time double precision NOT NULL,
    num_file_uploads integer NOT NULL,
    bandwidth_mbs double precision NOT NULL
);


ALTER TABLE public.lib_remote_status OWNER TO ddeboer;

--
-- Name: lib_server_status; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.lib_server_status (
    hostname character varying(32) NOT NULL,
    mc_time bigint NOT NULL,
    ip_address character varying(32) NOT NULL,
    mc_system_timediff double precision NOT NULL,
    num_cores integer NOT NULL,
    cpu_load_pct double precision NOT NULL,
    uptime_days double precision NOT NULL,
    memory_used_pct double precision NOT NULL,
    memory_size_gb double precision NOT NULL,
    disk_space_pct double precision NOT NULL,
    disk_size_gb double precision NOT NULL,
    network_bandwidth_mbs double precision
);


ALTER TABLE public.lib_server_status OWNER TO ddeboer;

--
-- Name: lib_status; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.lib_status (
    "time" bigint NOT NULL,
    num_files bigint NOT NULL,
    data_volume_gb double precision NOT NULL,
    free_space_gb double precision NOT NULL,
    upload_min_elapsed double precision NOT NULL,
    num_processes integer NOT NULL,
    git_version character varying(32) NOT NULL,
    git_hash character varying(64) NOT NULL
);


ALTER TABLE public.lib_status OWNER TO ddeboer;

--
-- Name: metric_list; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.metric_list (
    metric character varying NOT NULL,
    "desc" character varying NOT NULL
);


ALTER TABLE public.metric_list OWNER TO ddeboer;

--
-- Name: node_power_command; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.node_power_command (
    "time" bigint NOT NULL,
    node integer NOT NULL,
    part character varying NOT NULL,
    command character varying NOT NULL
);


ALTER TABLE public.node_power_command OWNER TO ddeboer;

--
-- Name: node_power_status; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.node_power_status (
    "time" bigint NOT NULL,
    node integer NOT NULL,
    snap_relay_powered boolean NOT NULL,
    snap0_powered boolean NOT NULL,
    snap1_powered boolean NOT NULL,
    snap2_powered boolean NOT NULL,
    snap3_powered boolean NOT NULL,
    fem_powered boolean NOT NULL,
    pam_powered boolean NOT NULL
);


ALTER TABLE public.node_power_status OWNER TO ddeboer;

--
-- Name: node_sensor; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.node_sensor (
    "time" bigint NOT NULL,
    node integer NOT NULL,
    top_sensor_temp double precision,
    middle_sensor_temp double precision,
    bottom_sensor_temp double precision,
    humidity_sensor_temp double precision,
    humidity double precision
);


ALTER TABLE public.node_sensor OWNER TO ddeboer;

--
-- Name: node_white_rabbit_status; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.node_white_rabbit_status (
    node_time bigint NOT NULL,
    node integer NOT NULL,
    board_info_str character varying,
    aliases character varying,
    ip character varying,
    mode character varying,
    serial character varying,
    temperature double precision,
    build_date bigint,
    gw_date bigint,
    gw_version character varying,
    gw_id character varying,
    build_hash character varying,
    manufacture_tag character varying,
    manufacture_device character varying,
    manufacture_date bigint,
    manufacture_partnum character varying,
    manufacture_serial character varying,
    manufacture_vendor character varying,
    port0_ad integer,
    port0_link_asymmetry_ps integer,
    port0_manual_phase_ps integer,
    port0_clock_offset_ps integer,
    port0_cable_rt_delay_ps integer,
    port0_master_slave_delay_ps integer,
    port0_master_rx_phy_delay_ps integer,
    port0_slave_rx_phy_delay_ps integer,
    port0_master_tx_phy_delay_ps integer,
    port0_slave_tx_phy_delay_ps integer,
    port0_hd integer,
    port0_link boolean,
    port0_lock boolean,
    port0_md integer,
    port0_rt_time_ps integer,
    port0_nsec integer,
    port0_packets_received integer,
    port0_phase_setpoint_ps integer,
    port0_servo_state character varying,
    port0_sv integer,
    port0_sync_source character varying,
    port0_packets_sent integer,
    port0_update_counter integer,
    port0_time bigint,
    port1_ad integer,
    port1_link_asymmetry_ps integer,
    port1_manual_phase_ps integer,
    port1_clock_offset_ps integer,
    port1_cable_rt_delay_ps integer,
    port1_master_slave_delay_ps integer,
    port1_master_rx_phy_delay_ps integer,
    port1_slave_rx_phy_delay_ps integer,
    port1_master_tx_phy_delay_ps integer,
    port1_slave_tx_phy_delay_ps integer,
    port1_hd integer,
    port1_link boolean,
    port1_lock boolean,
    port1_md integer,
    port1_rt_time_ps integer,
    port1_nsec integer,
    port1_packets_received integer,
    port1_phase_setpoint_ps integer,
    port1_servo_state character varying,
    port1_sv integer,
    port1_sync_source character varying,
    port1_packets_sent integer,
    port1_update_counter integer,
    port1_time bigint
);


ALTER TABLE public.node_white_rabbit_status OWNER TO ddeboer;

--
-- Name: paper_temperatures; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.paper_temperatures (
    balun_east double precision,
    cable_east double precision,
    balun_west double precision,
    cable_west double precision,
    rcvr_1a double precision,
    rcvr_1b double precision,
    rcvr_2a double precision,
    rcvr_2b double precision,
    rcvr_3a double precision,
    rcvr_3b double precision,
    rcvr_4a double precision,
    rcvr_4b double precision,
    rcvr_5a double precision,
    rcvr_5b double precision,
    rcvr_6a double precision,
    rcvr_6b double precision,
    rcvr_7a double precision,
    rcvr_7b double precision,
    rcvr_8a double precision,
    rcvr_8b double precision,
    "time" bigint NOT NULL
);


ALTER TABLE public.paper_temperatures OWNER TO ddeboer;

--
-- Name: part_info; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.part_info (
    hpn character varying(64) NOT NULL,
    hpn_rev character varying(32) NOT NULL,
    comment character varying(2048) NOT NULL,
    reference character varying(256),
    posting_gpstime bigint NOT NULL
);


ALTER TABLE public.part_info OWNER TO ddeboer;

--
-- Name: part_rosetta; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.part_rosetta (
    hpn character varying(64) NOT NULL,
    syspn character varying(64) NOT NULL,
    start_gpstime bigint NOT NULL,
    stop_gpstime bigint
);


ALTER TABLE public.part_rosetta OWNER TO ddeboer;

--
-- Name: parts; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.parts (
    hpn character varying(64) NOT NULL,
    hpn_rev character varying(32) NOT NULL,
    hptype character varying(64) NOT NULL,
    manufacturer_number character varying(64),
    start_gpstime bigint NOT NULL,
    stop_gpstime bigint
);


ALTER TABLE public.parts OWNER TO ddeboer;

--
-- Name: roach_temperature; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.roach_temperature (
    "time" bigint NOT NULL,
    roach character varying NOT NULL,
    ambient_temp double precision,
    inlet_temp double precision,
    outlet_temp double precision,
    fpga_temp double precision,
    ppc_temp double precision
);


ALTER TABLE public.roach_temperature OWNER TO ddeboer;

--
-- Name: rtp_launch_record; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.rtp_launch_record (
    obsid bigint NOT NULL,
    submitted_time bigint,
    rtp_attempts bigint NOT NULL,
    jd bigint NOT NULL,
    obs_tag character varying(128) NOT NULL,
    filename character varying(128) NOT NULL,
    prefix character varying(128) NOT NULL
);


ALTER TABLE public.rtp_launch_record OWNER TO ddeboer;

--
-- Name: rtp_process_event; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.rtp_process_event (
    "time" bigint NOT NULL,
    obsid bigint NOT NULL,
    event public.rtp_process_enum NOT NULL
);


ALTER TABLE public.rtp_process_event OWNER TO ddeboer;

--
-- Name: rtp_process_record; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.rtp_process_record (
    "time" bigint NOT NULL,
    obsid bigint NOT NULL,
    pipeline_list text NOT NULL,
    rtp_git_version character varying(32) NOT NULL,
    rtp_git_hash character varying(64) NOT NULL,
    hera_cal_git_hash character varying(64) NOT NULL,
    hera_cal_git_version character varying(32) NOT NULL,
    hera_qm_git_hash character varying(64) NOT NULL,
    hera_qm_git_version character varying(32) NOT NULL,
    pyuvdata_git_hash character varying(64) NOT NULL,
    pyuvdata_git_version character varying(32) NOT NULL
);


ALTER TABLE public.rtp_process_record OWNER TO ddeboer;

--
-- Name: rtp_server_status; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.rtp_server_status (
    hostname character varying(32) NOT NULL,
    mc_time bigint NOT NULL,
    ip_address character varying(32) NOT NULL,
    mc_system_timediff double precision NOT NULL,
    num_cores integer NOT NULL,
    cpu_load_pct double precision NOT NULL,
    uptime_days double precision NOT NULL,
    memory_used_pct double precision NOT NULL,
    memory_size_gb double precision NOT NULL,
    disk_space_pct double precision NOT NULL,
    disk_size_gb double precision NOT NULL,
    network_bandwidth_mbs double precision
);


ALTER TABLE public.rtp_server_status OWNER TO ddeboer;

--
-- Name: rtp_status; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.rtp_status (
    "time" bigint NOT NULL,
    status character varying(64) NOT NULL,
    event_min_elapsed double precision NOT NULL,
    num_processes integer NOT NULL,
    restart_hours_elapsed double precision NOT NULL
);


ALTER TABLE public.rtp_status OWNER TO ddeboer;

--
-- Name: rtp_task_jobid; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.rtp_task_jobid (
    obsid bigint NOT NULL,
    task_name text NOT NULL,
    start_time bigint NOT NULL,
    job_id bigint NOT NULL
);


ALTER TABLE public.rtp_task_jobid OWNER TO ddeboer;

--
-- Name: rtp_task_multiple_jobid; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.rtp_task_multiple_jobid (
    obsid_start bigint NOT NULL,
    task_name text NOT NULL,
    start_time bigint NOT NULL,
    job_id bigint NOT NULL
);


ALTER TABLE public.rtp_task_multiple_jobid OWNER TO ddeboer;

--
-- Name: rtp_task_multiple_resource_record; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.rtp_task_multiple_resource_record (
    obsid_start bigint NOT NULL,
    task_name text NOT NULL,
    start_time bigint NOT NULL,
    stop_time bigint NOT NULL,
    max_memory double precision,
    avg_cpu_load double precision
);


ALTER TABLE public.rtp_task_multiple_resource_record OWNER TO ddeboer;

--
-- Name: rtp_task_multiple_track; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.rtp_task_multiple_track (
    obsid_start bigint NOT NULL,
    task_name text NOT NULL,
    obsid bigint NOT NULL
);


ALTER TABLE public.rtp_task_multiple_track OWNER TO ddeboer;

--
-- Name: rtp_task_resource_record; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.rtp_task_resource_record (
    obsid bigint NOT NULL,
    task_name text NOT NULL,
    start_time bigint NOT NULL,
    stop_time bigint NOT NULL,
    max_memory double precision,
    avg_cpu_load double precision
);


ALTER TABLE public.rtp_task_resource_record OWNER TO ddeboer;

--
-- Name: snap_config_version; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.snap_config_version (
    init_time bigint NOT NULL,
    version character varying NOT NULL,
    init_args character varying NOT NULL,
    config_hash character varying NOT NULL
);


ALTER TABLE public.snap_config_version OWNER TO ddeboer;

--
-- Name: snap_config_version_init_time_seq; Type: SEQUENCE; Schema: public; Owner: ddeboer
--

CREATE SEQUENCE public.snap_config_version_init_time_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.snap_config_version_init_time_seq OWNER TO ddeboer;

--
-- Name: snap_config_version_init_time_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ddeboer
--

ALTER SEQUENCE public.snap_config_version_init_time_seq OWNED BY public.snap_config_version.init_time;


--
-- Name: snap_status; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.snap_status (
    "time" bigint NOT NULL,
    hostname character varying NOT NULL,
    node integer,
    snap_loc_num integer,
    serial_number character varying,
    psu_alert boolean,
    pps_count bigint,
    fpga_temp double precision,
    uptime_cycles bigint,
    last_programmed_time bigint
);


ALTER TABLE public.snap_status OWNER TO ddeboer;

--
-- Name: station_type; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.station_type (
    station_type_name character varying(64) NOT NULL,
    prefix character varying(64) NOT NULL,
    description character varying(64),
    plot_marker character varying(64)
);


ALTER TABLE public.station_type OWNER TO ddeboer;

--
-- Name: subsystem_error; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.subsystem_error (
    id bigint NOT NULL,
    "time" bigint NOT NULL,
    subsystem character varying(32) NOT NULL,
    mc_time bigint NOT NULL,
    severity integer NOT NULL,
    log text NOT NULL
);


ALTER TABLE public.subsystem_error OWNER TO ddeboer;

--
-- Name: subsystem_error_id_seq; Type: SEQUENCE; Schema: public; Owner: ddeboer
--

CREATE SEQUENCE public.subsystem_error_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.subsystem_error_id_seq OWNER TO ddeboer;

--
-- Name: subsystem_error_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ddeboer
--

ALTER SEQUENCE public.subsystem_error_id_seq OWNED BY public.subsystem_error.id;


--
-- Name: weather_data; Type: TABLE; Schema: public; Owner: ddeboer
--

CREATE TABLE public.weather_data (
    "time" bigint NOT NULL,
    variable character varying NOT NULL,
    value double precision NOT NULL
);


ALTER TABLE public.weather_data OWNER TO ddeboer;

--
-- Name: autocorrelations id; Type: DEFAULT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.autocorrelations ALTER COLUMN id SET DEFAULT nextval('public.autocorrelations_id_seq'::regclass);


--
-- Name: correlator_config_status time; Type: DEFAULT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.correlator_config_status ALTER COLUMN "time" SET DEFAULT nextval('public.correlator_config_status_time_seq'::regclass);


--
-- Name: dubitable start_gpstime; Type: DEFAULT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.dubitable ALTER COLUMN start_gpstime SET DEFAULT nextval('public.dubitable_start_gpstime_seq'::regclass);


--
-- Name: snap_config_version init_time; Type: DEFAULT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.snap_config_version ALTER COLUMN init_time SET DEFAULT nextval('public.snap_config_version_init_time_seq'::regclass);


--
-- Name: subsystem_error id; Type: DEFAULT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.subsystem_error ALTER COLUMN id SET DEFAULT nextval('public.subsystem_error_id_seq'::regclass);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: ant_metrics ant_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.ant_metrics
    ADD CONSTRAINT ant_metrics_pkey PRIMARY KEY (obsid, ant, pol, metric);


--
-- Name: antenna_status antenna_status_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.antenna_status
    ADD CONSTRAINT antenna_status_pkey PRIMARY KEY ("time", antenna_number, antenna_feed_pol);


--
-- Name: apriori_antenna apriori_antenna_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.apriori_antenna
    ADD CONSTRAINT apriori_antenna_pkey PRIMARY KEY (antenna, start_gpstime);


--
-- Name: array_metrics array_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.array_metrics
    ADD CONSTRAINT array_metrics_pkey PRIMARY KEY (obsid, metric);


--
-- Name: autocorrelations autocorrelations_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.autocorrelations
    ADD CONSTRAINT autocorrelations_pkey PRIMARY KEY (id);


--
-- Name: cm_version cm_version_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.cm_version
    ADD CONSTRAINT cm_version_pkey PRIMARY KEY (update_time);


--
-- Name: connections connections_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.connections
    ADD CONSTRAINT connections_pkey PRIMARY KEY (upstream_part, up_part_rev, upstream_output_port, downstream_part, down_part_rev, downstream_input_port, start_gpstime);


--
-- Name: correlator_config_active_snap correlator_config_active_snap_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.correlator_config_active_snap
    ADD CONSTRAINT correlator_config_active_snap_pkey PRIMARY KEY (config_hash, hostname);


--
-- Name: correlator_config_command correlator_config_command_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.correlator_config_command
    ADD CONSTRAINT correlator_config_command_pkey PRIMARY KEY ("time", command);


--
-- Name: correlator_config_file correlator_config_file_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.correlator_config_file
    ADD CONSTRAINT correlator_config_file_pkey PRIMARY KEY (config_hash);


--
-- Name: correlator_config_input_index correlator_config_input_index_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.correlator_config_input_index
    ADD CONSTRAINT correlator_config_input_index_pkey PRIMARY KEY (config_hash, correlator_index);


--
-- Name: correlator_config_params correlator_config_params_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.correlator_config_params
    ADD CONSTRAINT correlator_config_params_pkey PRIMARY KEY (config_hash, parameter);


--
-- Name: correlator_config_phase_switch_index correlator_config_phase_switch_index_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.correlator_config_phase_switch_index
    ADD CONSTRAINT correlator_config_phase_switch_index_pkey PRIMARY KEY (config_hash, hostname, phase_switch_index);


--
-- Name: correlator_config_status correlator_config_status_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.correlator_config_status
    ADD CONSTRAINT correlator_config_status_pkey PRIMARY KEY ("time");


--
-- Name: correlator_control_command correlator_control_command_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.correlator_control_command
    ADD CONSTRAINT correlator_control_command_pkey PRIMARY KEY ("time", command);


--
-- Name: correlator_control_state correlator_control_state_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.correlator_control_state
    ADD CONSTRAINT correlator_control_state_pkey PRIMARY KEY ("time", state_type);


--
-- Name: correlator_software_versions correlator_software_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.correlator_software_versions
    ADD CONSTRAINT correlator_software_versions_pkey PRIMARY KEY ("time", package);


--
-- Name: correlator_take_data_arguments correlator_take_data_arguments_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.correlator_take_data_arguments
    ADD CONSTRAINT correlator_take_data_arguments_pkey PRIMARY KEY ("time", command);


--
-- Name: daemon_status daemon_status_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.daemon_status
    ADD CONSTRAINT daemon_status_pkey PRIMARY KEY (name, hostname, jd);


--
-- Name: dubitable dubitable_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.dubitable
    ADD CONSTRAINT dubitable_pkey PRIMARY KEY (start_gpstime);


--
-- Name: geo_location geo_location_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.geo_location
    ADD CONSTRAINT geo_location_pkey PRIMARY KEY (station_name);


--
-- Name: hera_autos hera_autos_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.hera_autos
    ADD CONSTRAINT hera_autos_pkey PRIMARY KEY ("time", antenna_number, antenna_feed_pol);


--
-- Name: hera_obs hera_obs_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.hera_obs
    ADD CONSTRAINT hera_obs_pkey PRIMARY KEY (obsid);


--
-- Name: lib_files lib_files_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.lib_files
    ADD CONSTRAINT lib_files_pkey PRIMARY KEY (filename);


--
-- Name: lib_raid_errors lib_raid_errors_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.lib_raid_errors
    ADD CONSTRAINT lib_raid_errors_pkey PRIMARY KEY (id);


--
-- Name: lib_raid_status lib_raid_status_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.lib_raid_status
    ADD CONSTRAINT lib_raid_status_pkey PRIMARY KEY ("time", hostname);


--
-- Name: lib_remote_status lib_remote_status_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.lib_remote_status
    ADD CONSTRAINT lib_remote_status_pkey PRIMARY KEY ("time", remote_name, ping_time);


--
-- Name: lib_server_status lib_server_status_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.lib_server_status
    ADD CONSTRAINT lib_server_status_pkey PRIMARY KEY (hostname, mc_time);


--
-- Name: lib_status lib_status_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.lib_status
    ADD CONSTRAINT lib_status_pkey PRIMARY KEY ("time");


--
-- Name: metric_list metric_list_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.metric_list
    ADD CONSTRAINT metric_list_pkey PRIMARY KEY (metric);


--
-- Name: node_power_command node_power_command_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.node_power_command
    ADD CONSTRAINT node_power_command_pkey PRIMARY KEY ("time", node, part);


--
-- Name: node_power_status node_power_status_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.node_power_status
    ADD CONSTRAINT node_power_status_pkey PRIMARY KEY ("time", node);


--
-- Name: node_sensor node_sensor_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.node_sensor
    ADD CONSTRAINT node_sensor_pkey PRIMARY KEY ("time", node);


--
-- Name: node_white_rabbit_status node_white_rabbit_status_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.node_white_rabbit_status
    ADD CONSTRAINT node_white_rabbit_status_pkey PRIMARY KEY (node_time, node);


--
-- Name: paper_temperatures paper_temperatures_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.paper_temperatures
    ADD CONSTRAINT paper_temperatures_pkey PRIMARY KEY ("time");


--
-- Name: part_info part_info_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.part_info
    ADD CONSTRAINT part_info_pkey PRIMARY KEY (hpn, hpn_rev, posting_gpstime);


--
-- Name: part_rosetta part_rosetta_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.part_rosetta
    ADD CONSTRAINT part_rosetta_pkey PRIMARY KEY (syspn, start_gpstime);


--
-- Name: parts parts_paper_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.parts
    ADD CONSTRAINT parts_paper_pkey PRIMARY KEY (hpn, hpn_rev);


--
-- Name: roach_temperature roach_temperature_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.roach_temperature
    ADD CONSTRAINT roach_temperature_pkey PRIMARY KEY ("time", roach);


--
-- Name: rtp_launch_record rtp_launch_record_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.rtp_launch_record
    ADD CONSTRAINT rtp_launch_record_pkey PRIMARY KEY (obsid);


--
-- Name: rtp_process_event rtp_process_event_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.rtp_process_event
    ADD CONSTRAINT rtp_process_event_pkey PRIMARY KEY ("time", obsid);


--
-- Name: rtp_process_record rtp_process_record_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.rtp_process_record
    ADD CONSTRAINT rtp_process_record_pkey PRIMARY KEY ("time", obsid);


--
-- Name: rtp_server_status rtp_server_status_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.rtp_server_status
    ADD CONSTRAINT rtp_server_status_pkey PRIMARY KEY (hostname, mc_time);


--
-- Name: rtp_status rtp_status_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.rtp_status
    ADD CONSTRAINT rtp_status_pkey PRIMARY KEY ("time");


--
-- Name: rtp_task_jobid rtp_task_jobid_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.rtp_task_jobid
    ADD CONSTRAINT rtp_task_jobid_pkey PRIMARY KEY (obsid, task_name, start_time);


--
-- Name: rtp_task_multiple_jobid rtp_task_multiple_jobid_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.rtp_task_multiple_jobid
    ADD CONSTRAINT rtp_task_multiple_jobid_pkey PRIMARY KEY (obsid_start, task_name, start_time);


--
-- Name: rtp_task_multiple_resource_record rtp_task_multiple_resource_record_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.rtp_task_multiple_resource_record
    ADD CONSTRAINT rtp_task_multiple_resource_record_pkey PRIMARY KEY (obsid_start, task_name);


--
-- Name: rtp_task_multiple_track rtp_task_multiple_track_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.rtp_task_multiple_track
    ADD CONSTRAINT rtp_task_multiple_track_pkey PRIMARY KEY (obsid_start, task_name, obsid);


--
-- Name: rtp_task_resource_record rtp_task_resource_record_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.rtp_task_resource_record
    ADD CONSTRAINT rtp_task_resource_record_pkey PRIMARY KEY (obsid, task_name);


--
-- Name: snap_config_version snap_config_version_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.snap_config_version
    ADD CONSTRAINT snap_config_version_pkey PRIMARY KEY (init_time);


--
-- Name: snap_status snap_status_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.snap_status
    ADD CONSTRAINT snap_status_pkey PRIMARY KEY ("time", hostname);


--
-- Name: station_type station_type_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.station_type
    ADD CONSTRAINT station_type_pkey PRIMARY KEY (station_type_name);


--
-- Name: subsystem_error subsystem_error_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.subsystem_error
    ADD CONSTRAINT subsystem_error_pkey PRIMARY KEY (id);


--
-- Name: weather_data weather_data_pkey; Type: CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.weather_data
    ADD CONSTRAINT weather_data_pkey PRIMARY KEY ("time", variable);


--
-- Name: ant_metrics ant_metrics_metric_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.ant_metrics
    ADD CONSTRAINT ant_metrics_metric_fkey FOREIGN KEY (metric) REFERENCES public.metric_list(metric);


--
-- Name: ant_metrics ant_metrics_obsid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.ant_metrics
    ADD CONSTRAINT ant_metrics_obsid_fkey FOREIGN KEY (obsid) REFERENCES public.hera_obs(obsid);


--
-- Name: array_metrics array_metrics_metric_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.array_metrics
    ADD CONSTRAINT array_metrics_metric_fkey FOREIGN KEY (metric) REFERENCES public.metric_list(metric);


--
-- Name: array_metrics array_metrics_obsid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.array_metrics
    ADD CONSTRAINT array_metrics_obsid_fkey FOREIGN KEY (obsid) REFERENCES public.hera_obs(obsid);


--
-- Name: connections connections_downstream_part_down_part_rev_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.connections
    ADD CONSTRAINT connections_downstream_part_down_part_rev_fkey FOREIGN KEY (downstream_part, down_part_rev) REFERENCES public.parts(hpn, hpn_rev);


--
-- Name: connections connections_upstream_part_up_part_rev_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.connections
    ADD CONSTRAINT connections_upstream_part_up_part_rev_fkey FOREIGN KEY (upstream_part, up_part_rev) REFERENCES public.parts(hpn, hpn_rev);


--
-- Name: correlator_config_active_snap correlator_config_active_snap_config_hash_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.correlator_config_active_snap
    ADD CONSTRAINT correlator_config_active_snap_config_hash_fkey FOREIGN KEY (config_hash) REFERENCES public.correlator_config_file(config_hash);


--
-- Name: correlator_config_command correlator_config_command_config_hash_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.correlator_config_command
    ADD CONSTRAINT correlator_config_command_config_hash_fkey FOREIGN KEY (config_hash) REFERENCES public.correlator_config_file(config_hash);


--
-- Name: correlator_config_command correlator_config_command_time_command_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.correlator_config_command
    ADD CONSTRAINT correlator_config_command_time_command_fkey FOREIGN KEY ("time", command) REFERENCES public.correlator_control_command("time", command);


--
-- Name: correlator_config_input_index correlator_config_input_index_config_hash_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.correlator_config_input_index
    ADD CONSTRAINT correlator_config_input_index_config_hash_fkey FOREIGN KEY (config_hash) REFERENCES public.correlator_config_file(config_hash);


--
-- Name: correlator_config_params correlator_config_params_config_hash_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.correlator_config_params
    ADD CONSTRAINT correlator_config_params_config_hash_fkey FOREIGN KEY (config_hash) REFERENCES public.correlator_config_file(config_hash);


--
-- Name: correlator_config_phase_switch_index correlator_config_phase_switch_index_config_hash_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.correlator_config_phase_switch_index
    ADD CONSTRAINT correlator_config_phase_switch_index_config_hash_fkey FOREIGN KEY (config_hash) REFERENCES public.correlator_config_file(config_hash);


--
-- Name: correlator_config_status correlator_config_status_config_hash_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.correlator_config_status
    ADD CONSTRAINT correlator_config_status_config_hash_fkey FOREIGN KEY (config_hash) REFERENCES public.correlator_config_file(config_hash);


--
-- Name: correlator_take_data_arguments correlator_take_data_arguments_time_command_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.correlator_take_data_arguments
    ADD CONSTRAINT correlator_take_data_arguments_time_command_fkey FOREIGN KEY ("time", command) REFERENCES public.correlator_control_command("time", command);


--
-- Name: geo_location geo_location_station_type_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.geo_location
    ADD CONSTRAINT geo_location_station_type_name_fkey FOREIGN KEY (station_type_name) REFERENCES public.station_type(station_type_name);


--
-- Name: lib_files lib_files_obsid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.lib_files
    ADD CONSTRAINT lib_files_obsid_fkey FOREIGN KEY (obsid) REFERENCES public.hera_obs(obsid);


--
-- Name: rtp_launch_record rtp_launch_record_obsid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.rtp_launch_record
    ADD CONSTRAINT rtp_launch_record_obsid_fkey FOREIGN KEY (obsid) REFERENCES public.hera_obs(obsid);


--
-- Name: rtp_process_event rtp_process_event_obsid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.rtp_process_event
    ADD CONSTRAINT rtp_process_event_obsid_fkey FOREIGN KEY (obsid) REFERENCES public.hera_obs(obsid);


--
-- Name: rtp_process_record rtp_process_record_obsid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.rtp_process_record
    ADD CONSTRAINT rtp_process_record_obsid_fkey FOREIGN KEY (obsid) REFERENCES public.hera_obs(obsid);


--
-- Name: rtp_task_jobid rtp_task_jobid_obsid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.rtp_task_jobid
    ADD CONSTRAINT rtp_task_jobid_obsid_fkey FOREIGN KEY (obsid) REFERENCES public.hera_obs(obsid);


--
-- Name: rtp_task_multiple_jobid rtp_task_multiple_jobid_obsid_start_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.rtp_task_multiple_jobid
    ADD CONSTRAINT rtp_task_multiple_jobid_obsid_start_fkey FOREIGN KEY (obsid_start) REFERENCES public.hera_obs(obsid);


--
-- Name: rtp_task_multiple_resource_record rtp_task_multiple_resource_record_obsid_start_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.rtp_task_multiple_resource_record
    ADD CONSTRAINT rtp_task_multiple_resource_record_obsid_start_fkey FOREIGN KEY (obsid_start) REFERENCES public.hera_obs(obsid);


--
-- Name: rtp_task_multiple_track rtp_task_multiple_track_obsid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.rtp_task_multiple_track
    ADD CONSTRAINT rtp_task_multiple_track_obsid_fkey FOREIGN KEY (obsid) REFERENCES public.hera_obs(obsid);


--
-- Name: rtp_task_multiple_track rtp_task_multiple_track_obsid_start_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.rtp_task_multiple_track
    ADD CONSTRAINT rtp_task_multiple_track_obsid_start_fkey FOREIGN KEY (obsid_start) REFERENCES public.hera_obs(obsid);


--
-- Name: rtp_task_resource_record rtp_task_resource_record_obsid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.rtp_task_resource_record
    ADD CONSTRAINT rtp_task_resource_record_obsid_fkey FOREIGN KEY (obsid) REFERENCES public.hera_obs(obsid);


--
-- Name: snap_config_version snap_config_version_config_hash_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ddeboer
--

ALTER TABLE ONLY public.snap_config_version
    ADD CONSTRAINT snap_config_version_config_hash_fkey FOREIGN KEY (config_hash) REFERENCES public.correlator_config_file(config_hash);


--
-- PostgreSQL database dump complete
--
