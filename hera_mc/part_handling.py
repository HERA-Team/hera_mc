#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
This is meant to hold utility scripts for parts and connections

"""
from __future__ import absolute_import, division, print_function

from hera_mc import part_connect, mc, geo_location

# Pass part using a dictionary with a superset of part data:
#   [hpn]{hptype, manufacturer_number, manufacture_date, short_description, repr,
#         portA[name(s)],  portB[name(s)],  geo[E, N, z, station, subarray]}
# Pass connections by using a dictionary of lists:
#   {up[name(s)],   b_on_up[name(s)],   start_on_up[time(s)],   stop_on_up[time(s)],
#    down[name(s)], a_on_down[name(s)], start_on_down[time(s)], stop_on_down[time(s)]}


class PartsAndConnections:
    def __init__(self):
        pass

    def show_part(self, args, part_dict):
        """
        Print out part information.  PLACEHOLDER FOR NOW.
        """
        for pd in part_dict.keys():
            if args.verbosity == 'm' or args.verbosity == 'h':
                print(pd, part_dict[pd])
            else:
                print(pd, part_dict[pd]['repr'])

    def get_part(self, args, hpn_query=None, show_part=False):
        """
        Return information on a part.  It will return all matching first characters.
        """
        if hpn_query is None:
            hpn_query = args.hpn
        part_dict = {}
        db = mc.connect_to_mc_db(args)
        with db.sessionmaker() as session:
            for part in session.query(part_connect.Parts).filter(part_connect.Parts.hpn.like(hpn_query + '%')):
                part_dict[part.hpn] = {'hptype': part.hptype,
                                       'manufacturer_number': part.manufacturer_number,
                                       'manufacture_date': part.manufacture_date,
                                       'a_ports': [], 'b_ports': []}
                part_dict[part.hpn]['repr'] = part.__repr__()  # Keep for now
                for part_info in session.query(part_connect.PartInfo).filter(part_connect.PartInfo.hpn == part.hpn):
                    part_dict[part.hpn]['short_description'] = part_info.short_description
                for connection in session.query(part_connect.Connections).filter(part_connect.Connections.down.like(hpn_query + '%')):
                    if connection.a_on_down not in part_dict[part.hpn]['a_ports']:
                        part_dict[part.hpn]['a_ports'].append(connection.a_on_down)
                for connection in session.query(part_connect.Connections).filter(part_connect.Connections.up.like(hpn_query + '%')):
                    if connection.b_on_up not in part_dict[part.hpn]['b_ports']:
                        part_dict[part.hpn]['b_ports'].append(connection.b_on_up)
                if part.hptype == 'station':
                    #sub_arrays = session.split_arrays()
                    args.locate = part.hpn
                    part_dict[part.hpn]['geo'] = geo_location.locate_station(args, show_geo=False)
        if show_part:
            self.show_part(args, part_dict)
        return part_dict

    def show_connection(self, args, connection_dict):
        """
        Print out connection information.  PLACEHOLDER FOR NOW.
        """
        for cd in connection_dict:
            if args.verbosity == 'm' or args.verbosity == 'h':
                print(cd, connection_dict[cd])
            elif cd in ['repr_up', 'repr_down']:
                print(cd, connection_dict[cd])

    def get_connection(self, args, hpn_query=None, port_query=None, show_connection=False):
        """
        Return information on parts connected to args.connection -- NEED TO INCLUDE USING START/STOP_TIME!!!
        It should get connections immediately adjacent to one part (upstream and downstream).
        """
        if hpn_query is None:
            hpn_query = args.connection
        if port_query is None:
            port_query = args.define_port
        connection_dict = {'up':   [], 'b_on_up':   [], 'start_on_up':   [], 'stop_on_up':   [], 'repr_up':   [],
                           'down': [], 'a_on_down': [], 'start_on_down': [], 'stop_on_down': [], 'repr_down': []}
        db = mc.connect_to_mc_db(args)
        with db.sessionmaker() as session:
            for connection in session.query(part_connect.Connections).filter(part_connect.Connections.up.like(hpn_query + '%')):
                if port_query=='all' or connection.b_on_up == port.query:
                    connection_dict['down'].append(connection.down)
                    connection_dict['a_on_down'].append(connection.a_on_down)
                    connection_dict['start_on_down'].append(connection.start_time)
                    connection_dict['stop_on_down'].append(connection.stop_time)
                    connection_dict['repr_down'].append(connection.__repr__())
            for connection in session.query(part_connect.Connections).filter(part_connect.Connections.down.like(hpn_query + '%')):
                if port_query=='all' or connection.a_on_down == port.query:
                    connection_dict['up'].append(connection.up)
                    connection_dict['b_on_up'].append(connection.b_on_up)
                    connection_dict['start_on_up'].append(connection.start_time)
                    connection_dict['stop_on_up'].append(connection.stop_time)
                    connection_dict['repr_up'].append(connection.__repr__())
        if show_connection:
            self.show_connection(args, connection_dict)
        return connection_dict

    def __go_upstream(self, args, hpn, port):
        connection_dict = self.get_connection(args, hpn_query=hpn, port_query=port, show_connection=False)
        for hpn_up in connection_dict['up']:
            if hpn_up not in self.upstream:
                self.upstream.append(hpn_up)
            self.__go_upstream(args, hpn_up, port)

    def __go_downstream(self, args, hpn, port):
        connection_dict = self.get_connection(args, hpn_query=hpn, port_query=port, show_connection=False)
        for hpn_down in connection_dict['down']:
            if hpn_down not in self.downstream:
                self.downstream.append(hpn_down)
            self.__go_downstream(args, hpn_down, port)

    def get_hookup(self, args, hpn_query=None, port_query=None, show_hookup=False):
        """
        Return the full hookup.
        """
        print("NEED TO ADD CONNECTIONS INTO UPSTREAM/DOWNSTREAM")
        if hpn_query is None:
            hpn_query = args.mapr
        if port_query is None:
            port_query = args.define_port
        parts = self.get_part(args, hpn_query=hpn_query, show_part=False)
        for hpn in parts.keys():
            self.hookup_hpn = hpn
            self.upstream = []
            self.downstream = []
            ports = [port_query]
            if port_query == 'all':
                self.port_query_state = 'all'# = ['place', 'holder']
            for p in port_query:

                self.__go_upstream(args, hpn, p)
                self.__go_downstream(args, hpn, p)
            self.show_hookup(args)
            print("GET_HOOKUP:  BREAK AT 1 FOR NOW")
            break

    def show_hookup(self, args):
        list_hookups = args.define_hookup.split(':')
        # print('Hookup for hpn ', self.hookup_hpn)
        print('\t', end='')
        for hookup_part in list_hookups:
            for hpn in self.upstream:
                part_info = self.get_part(args, hpn_query=hpn, show_part=False)
                if hookup_part in part_info[hpn]['hptype']:
                    print(hpn, end='\t')
        print('[', self.hookup_hpn, ']', sep='', end='\t')
        for hookup_part in list_hookups:
            for hpn in self.downstream:
                part_info = self.get_part(args, hpn_query=hpn, show_part=False)
                if hookup_part in part_info[hpn]['hptype']:
                    print(hpn, end='\t')
        print('')

    def get_part_types(self, args, show_hptype=False):
        self.part_type_dict = {}
        db = mc.connect_to_mc_db(args)
        with db.sessionmaker() as session:
            for part in session.query(part_connect.Parts).all():
                if part.hptype not in self.part_type_dict.keys():
                    self.part_type_dict[part.hptype] = {'part_list':[part.hpn], 'a_ports':[], 'b_ports':[]}
                else:
                    self.part_type_dict[part.hptype]['part_list'].append(part.hpn)
        for k in self.part_type_dict.keys():  ###ASSUME FIRST PART IS FULLY CONNECTED
            pa = self.part_type_dict[k]['part_list'][0]  
            pd = self.get_part(args,pa,show_part=False)
            self.part_type_dict[k]['a_ports'] = pd[pa]['a_ports']
            self.part_type_dict[k]['b_ports'] = pd[pa]['b_ports']
            if show_hptype:
                print('%s: %d parts in database' % (k,len(self.part_type_dict[k]['part_list'])))
                print('\tA:',end=' ')
                for a in self.part_type_dict[k]['a_ports']:
                    print(a,end=' ')
                print('\n\tB:',end=' ')
                for b in self.part_type_dict[k]['b_ports']:
                    print(b,end=' ')
                print()
        return self.part_type_dict

