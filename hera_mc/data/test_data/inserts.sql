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
-- Data for Name: station_type; Type: TABLE DATA; Schema: public; Owner: ddeboer
--

INSERT INTO public.station_type VALUES ('container', 'CR', 'Container location', 'k*');
INSERT INTO public.station_type VALUES ('herahex', 'HH', 'HERA Hex locations', 'ro');
INSERT INTO public.station_type VALUES ('node', 'ND', 'Node location', 'r*');
INSERT INTO public.station_type VALUES ('paperhex', 'PH', 'PAPER Hex locations', 'rs');
INSERT INTO public.station_type VALUES ('paperimaging', 'PI', 'PAPER Imaging locations', 'gs');
INSERT INTO public.station_type VALUES ('paperpolarized', 'PP', 'PAPER Polarized locations', 'bd');
INSERT INTO public.station_type VALUES ('stationgrid', 'S', 'Station grid locations', 'ks');
INSERT INTO public.station_type VALUES ('cofa', 'COFA', 'Center of array', 'bs');
INSERT INTO public.station_type VALUES ('heraringa', 'HA', 'HERA inner ring', 'ro');
INSERT INTO public.station_type VALUES ('heraringb', 'HB', 'HERA outer ring', 'ro');
INSERT INTO public.station_type VALUES ('herahexw', 'HH', 'HERA hex locations W tridrant', 'ro');
INSERT INTO public.station_type VALUES ('herahexe', 'HH', 'HERA hex locations E tridrant', 'ro');
INSERT INTO public.station_type VALUES ('herahexn', 'HH', 'HERA hex locations N tridrant', 'ro');


--
-- PostgreSQL database dump complete
--

