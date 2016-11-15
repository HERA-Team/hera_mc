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

    def get_part(self, args, hpn_query=None, exact_match=False, show_part=False):
        """
        Return information on a part.  It will return all matching first characters.
        """
        if hpn_query is None:
            hpn_query = args.hpn
            exact_match = args.exact_match
        if not exact_match:
            hpn_query = hpn_query+'%'
        part_dict = {}
        db = mc.connect_to_mc_db(args)
        with db.sessionmaker() as session:
            for part in session.query(part_connect.Parts).filter(part_connect.Parts.hpn.like(hpn_query)):
                part_dict[part.hpn] = {'hptype': part.hptype,
                                       'manufacturer_number': part.manufacturer_number,
                                       'manufacture_date': part.manufacture_date,
                                       'a_ports': [], 'b_ports': []}
                part_dict[part.hpn]['repr'] = part.__repr__()  # Keep for now
                for part_info in session.query(part_connect.PartInfo).filter(part_connect.PartInfo.hpn == part.hpn):
                    part_dict[part.hpn]['short_description'] = part_info.short_description
                for connection in session.query(part_connect.Connections).filter(part_connect.Connections.down.like(hpn_query)):
                    if connection.a_on_down not in part_dict[part.hpn]['a_ports']:
                        part_dict[part.hpn]['a_ports'].append(connection.a_on_down)
                for connection in session.query(part_connect.Connections).filter(part_connect.Connections.up.like(hpn_query)):
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

    def get_connection(self, args, hpn_query=None, port_query=None, exact_match=False, show_connection=False):
        """
        Return information on parts connected to args.connection -- NEED TO INCLUDE USING START/STOP_TIME!!!
        It should get connections immediately adjacent to one part (upstream and downstream).
        """
        if hpn_query is None:
            hpn_query = args.connection
            exact_match = args.exact_match
        if not exact_match:
            hpn_query = hpn_query+'%'
        if port_query is None:
            port_query = args.define_port
        connection_dict = {'up':   [], 'b_on_up':   [], 'start_on_up':   [], 'stop_on_up':   [], 'repr_up':   [],
                           'down': [], 'a_on_down': [], 'start_on_down': [], 'stop_on_down': [], 'repr_down': []}
        db = mc.connect_to_mc_db(args)
        with db.sessionmaker() as session:
            for connection in session.query(part_connect.Connections).filter(part_connect.Connections.up.like(hpn_query)):
                if port_query=='all' or connection.b_on_up == port_query:
                    connection_dict['down'].append(connection.down)
                    connection_dict['a_on_down'].append(connection.a_on_down)
                    connection_dict['start_on_down'].append(connection.start_time)
                    connection_dict['stop_on_down'].append(connection.stop_time)
                    connection_dict['repr_down'].append(connection.__repr__())
            for connection in session.query(part_connect.Connections).filter(part_connect.Connections.down.like(hpn_query)):
                if port_query=='all' or connection.a_on_down == port_query:
                    connection_dict['up'].append(connection.up)
                    connection_dict['b_on_up'].append(connection.b_on_up)
                    connection_dict['start_on_up'].append(connection.start_time)
                    connection_dict['stop_on_up'].append(connection.stop_time)
                    connection_dict['repr_up'].append(connection.__repr__())
        if show_connection:
            self.show_connection(args, connection_dict)
        return connection_dict

    def __get_upstream_port(self,args,hpn,port):
        part_dict = self.get_part(args,hpn_query=hpn,exact_match=True,show_part=False)
        number_a_ports = len(part_dict[hpn]['a_ports'])
        number_b_ports = len(part_dict[hpn]['b_ports'])
        if port in part_dict[hpn]['a_ports']:
            return_port = port
        elif number_a_ports == 1:
            return_port = part_dict[hpn]['a_ports'][0]
        elif number_a_ports == 0:
            return None
        elif port in part_dict[hpn]['b_ports']:
            if number_b_ports == number_a_ports:
                return_port = port.replace('b','a')
            elif number_b_ports > number_a_ports:
                return_port = part_dict[hpn]['a_ports'][0]
                print("I don't think that this one can happen.")
        else:
            print('Error:  port not found',port)
            return_port = None 
        return return_port

    def __get_downstream_port(self,args,hpn,port):
        part_dict = self.get_part(args,hpn_query=hpn,exact_match=True,show_part=False)
        number_a_ports = len(part_dict[hpn]['a_ports'])
        number_b_ports = len(part_dict[hpn]['b_ports'])
        if port in part_dict[hpn]['b_ports']:
            return_port = port
        elif number_b_ports == 1:
            return_port = part_dict[hpn]['b_ports'][0]
        elif number_b_ports == 0:
            return None
        elif port in part_dict[hpn]['a_ports']:
            if number_a_ports == number_b_ports:
                return_port = port.replace('a','b')
            elif number_a_ports > number_b_ports:
                return_port = part_dict[hpn]['b_ports'][0]
                print("I don't think that this one can happen.")
        else:
            print('Error:  port not found',port)
            return_port = None 
        return return_port

    def __go_upstream(self, args, hpn, port):
        """
        Find the next connection up the signal chain -- needs port to be on 'a' side of hpn
        """
        up_port = self.__get_upstream_port(args,hpn,port)
        connection_dict = self.get_connection(args, hpn_query=hpn, port_query=up_port, exact_match=True, show_connection=False)
        for hpn_up in connection_dict['up']:
            if hpn_up not in self.upstream:
                self.upstream.append([hpn_up,up_port])
            port = connection_dict['b_on_up'][0]
            self.__go_upstream(args, hpn_up, port)

    def __go_downstream(self, args, hpn, port):
        """
        Find the next connection down the signal chain -- needs port to be on 'b' side of hpn
        """
        down_port = self.__get_downstream_port(args,hpn,port)
        connection_dict = self.get_connection(args, hpn_query=hpn, port_query=down_port, exact_match=True, show_connection=False)
        for hpn_down in connection_dict['down']:
            if hpn_down not in self.downstream:
                self.downstream.append([hpn_down,down_port])
            port = connection_dict['a_on_down'][0]
            self.__go_downstream(args, hpn_down, port)

    def get_hookup(self, args, hpn_query=None, port_query=None, show_hookup=False):
        """
        Return the full hookup.
        """
        exact_match = False
        if hpn_query is None:
            hpn_query = args.mapr
            exact_match = args.exact_match
        if port_query is None:
            port_query = args.define_port
        parts = self.get_part(args, hpn_query=hpn_query, exact_match=exact_match, show_part=False)
        hookup_dict = {}
        for hpn in parts.keys():
            number_a_ports = len(parts[hpn]['a_ports'])
            number_b_ports = len(parts[hpn]['b_ports'])
            if port_query == 'all':
                if number_b_ports>number_a_ports:
                    port_query = parts[hpn]['b_ports']
                else:
                    port_query = parts[hpn]['a_ports']
            elif type(port_query) is not list:
                port_query = [port_query]
            for p in port_query:
                self.upstream = [[hpn,p]]
                self.downstream = []
                self.__go_upstream(args, hpn, p)
                self.__go_downstream(args, hpn, p)
                station = self.get_part(args,hpn_query=self.upstream[-1][0],exact_match=True,show_part=False)
                if station[self.upstream[-1][0]]['hptype'] == 'station':
                    hookup_dict[hpn] = [[station[self.upstream[-1][0]]['geo'][4],'S']]
                else:
                    hookup_dict[hpn] = []
                for pn in reversed(self.upstream):
                    hookup_dict[hpn].append(pn)
                for pn in self.downstream:
                    hookup_dict[hpn].append(pn)
        if show_hookup:
            self.show_hookup(hookup_dict)

    def show_hookup(self, hookup_dict):
        for hpn in hookup_dict.keys():
            for pn in hookup_dict[hpn]:
                if pn[1]=='S':
                    print('(',pn[0],')',sep='',end=' ')
                elif pn[0] == hpn:
                    print('[',pn[0],']',sep='',end=' ')
                else:
                    print(pn[0],end=' ')
            print()
        return 

        # list_hookups = args.define_hookup.split(':')
        # print('Hookup for hpn ', self.hookup_hpn)
        # print('\t', end='')
        # for hookup_part in list_hookups:
        #     for hpn0 in self.upstream:
        #         hpn = hpn0[0]
        #         part_info = self.get_part(args, hpn_query=hpn, show_part=False)
        #         if hookup_part in part_info[hpn]['hptype']:
        #             print(hpn,':', end='\t')
        # print('[', self.hookup_hpn, ']', sep='', end='\t')
        # for hookup_part in list_hookups:
        #     for hpn0 in self.downstream:
        #         hpn = hpn0[0]
        #         part_info = self.get_part(args, hpn_query=hpn, show_part=False)
        #         if hookup_part in part_info[hpn]['hptype']:
        #             print(hpn, end='\t')
        # print('')

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

