#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""This is meant to hold utility scripts for parts and connections

"""
from __future__ import absolute_import, division, print_function

from hera_mc import part_connect, mc
import geo

import copy

#Pass part using a dictionary with a superset of part data:
#   [hpn]{hptype, manufacturer_number, manufacture_date, short_description, repr,
#         portA[name(s)], portB[name(s)], geo[E,N,z,station,subarray]}
#Pass connections by using a dictionary of lists:
#   {a[name(s)], port_on_a[name(s)], start_on_a[time(s)], stop_on_a[time(s)],
#    b[name(s)], port_on_b[name(s)], start_on_b[time(s)], stop_on_b[time(s)]}

class PartsAndConnections:
    def __init__(self):
        pass

    def show_part(self,args,part_dict):
        """
        Print out part information.  PLACEHOLDER FOR NOW.
        """
        for pd in part_dict.keys():
            if args.verbosity=='m' or args.verbosity=='h':
                print(pd,part_dict[pd])
            else:
                print(pd,part_dict[pd]['repr'])
    def get_part(self,args,hpn_query=None,show_part=False):
        """
        Return information on a part as contained in args.hpn.  It will return all matching first characters.
        """
        if hpn_query is None:
            hpn_query = args.hpn
        part_dict = {}
        db = mc.connect_to_mc_db(args)
        with db.sessionmaker() as session:
            for part in session.query(part_connect.Parts).filter(part_connect.Parts.hpn.like(hpn_query+'%')):
                part_dict[part.hpn] = {'hptype':part.hptype, 
                                      'manufacturer_number':part.manufacturer_number, 
                                      'manufacture_date':part.manufacture_date}
                part_dict[part.hpn]['repr'] = part.__repr__()  #Keep for now
                for part_info in session.query(part_connect.PartInfo).filter(part_connect.PartInfo.hpn==part.hpn):
                    part_dict[part.hpn]['short_description'] = part_info.short_description
                if part.hptype=='station':
                    sub_arrays = session.split_arrays(geo.sub_array_designators.keys())
                    args.locate = part.hpn
                    part_dict[part.hpn]['geo'] = geo.locate_station(args,show_geo=False)

        if show_part:
            self.show_part(args,part_dict)
        return part_dict

    def show_connection(self,args,connection_dict):
        """
        Print out connection information.  PLACEHOLDER FOR NOW.
        """
        for cd in connection_dict:
            if args.verbosity=='m' or args.verbosity=='h':
                print(cd, connection_dict[cd])
            elif cd in ['repr_a','repr_b']:
                print(cd, connection_dict[cd])
    def get_connection(self,args,hpn_query=None,show_connection=False):
        """
        Return information on parts connected to args.connection -- NEED TO INCLUDE USING START/STOP_TIME!!!
        It should get connections immediately adjacent to one part (upstream and downstream).
        """
        if hpn_query is None:
            hpn_query = args.connection
        connection_dict = {'a':[],'port_on_a':[],'start_on_a':[],'stop_on_a':[], 'repr_a':[],
                           'b':[],'port_on_b':[],'start_on_b':[],'stop_on_b':[], 'repr_b':[]}
        db = mc.connect_to_mc_db(args)
        with db.sessionmaker() as session:
            for connection in session.query(part_connect.Connections).filter(part_connect.Connections.a.like(hpn_query+'%')):
                #connected.append(self.get_part(args,connection.b,show_part=False))
                connection_dict['b'].append(connection.b)
                connection_dict['port_on_b'].append(connection.port_on_b)
                connection_dict['start_on_b'].append(connection.start_time)
                connection_dict['stop_on_b'].append(connection.stop_time)
                connection_dict['repr_b'].append(connection.__repr__())
            for connection in session.query(part_connect.Connections).filter(part_connect.Connections.b.like(hpn_query+'%')):
                #connected.append(self.get_part(args,connection.a,show_part=False))
                connection_dict['a'].append(connection.a)
                connection_dict['port_on_a'].append(connection.port_on_a)
                connection_dict['start_on_a'].append(connection.start_time)
                connection_dict['stop_on_a'].append(connection.stop_time)
                connection_dict['repr_a'].append(connection.__repr__())
        if show_connection:
            self.show_connection(args,connection_dict)
        return connection_dict

    def __go_upstream(self,args,hpn):
        connection_dict = self.get_connection(args,hpn_query=hpn,show_connection=False)
        for hpn_a in connection_dict['a']:
            if hpn_a not in self.upstream:
                self.upstream.append(hpn_a)
            self.__go_upstream(args,hpn_a)
    def __go_downstream(self,args,hpn):
        connection_dict = self.get_connection(args,hpn_query=hpn,show_connection=False)
        for hpn_b in connection_dict['b']:
            if hpn_b not in self.downstream:
                self.downstream.append(hpn_b)
            self.__go_downstream(args,hpn_b)

    def get_hookup(self,args,hpn_query=None,show_hookup=False):
        """
        Return the full hookup.
        """
        print("NEED TO ADD CONNECTIONS INTO UPSTREAM/DOWNSTREAM")
        if hpn_query is None:
            hpn_query = args.mapr
        parts = self.get_part(args,hpn_query=hpn_query,show_part=False)
        for hpn in parts.keys():
            self.hookup_hpn=hpn
            self.upstream=[]
            self.downstream=[]
            self.__go_upstream(args,hpn)
            self.__go_downstream(args,hpn)
            self.show_hookup(args)
            print("GET_HOOKUP:  BREAK AT 1 FOR NOW")
            break
    def show_hookup(self,args):
        list_hookups = args.define_hookup.split(':')
        #print('Hookup for hpn ',self.hookup_hpn)
        print('\t',end='')
        for hookup_part in list_hookups:
            for hpn in self.upstream:
                part_info = self.get_part(args,hpn_query=hpn,show_part=False)
                if hookup_part in part_info[hpn]['hptype']:
                    print(hpn,end='\t')
        print('[',self.hookup_hpn,']',sep='',end='\t')
        for hookup_part in list_hookups:
            for hpn in self.downstream:
                part_info = self.get_part(args,hpn_query=hpn,show_part=False)
                if hookup_part in part_info[hpn]['hptype']:
                    print(hpn,end='\t')
        print('')
