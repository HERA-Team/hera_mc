#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
This is meant to hold helpful modules for parts and connections scripts

"""
from __future__ import absolute_import, division, print_function
from tabulate import tabulate
import sys

from hera_mc import mc, part_connect, geo_location, correlator_levels, cm_utils
import copy

def _make_part_key(hpn,rev):
    return ":".join([hpn,rev])
def _make_connection_key(hpn,rev,direction,next_part,start_date,fragment=False):
    if type(fragment) == list:
        return ":".join(fragment)
    else:
        return ":".join([hpn,rev,direction,next_part,cm_utils._get_datekeystring(start_date)])
def _make_hookup_key(hpn,rev,port):
    return ":".join([hpn,rev,port])

class Handling:
    """
    Class to allow various manipulations of parts and their properties etc.  Things are 
    manipulated/passed as dictionaries currently.
    """
    no_connection_designator = '--'
    last_revisions = {}
    connections_dictionary = {}
    non_class_connections_dict_entries = ['ordered_pairs',no_connection_designator]
    parts_dictionary = {}
    current = ''

    def __init__(self,args):
        self.args = args

    def is_in_connections(self,hpn_query,rev_query='LAST',return_active=False):
        """
        checks to see if a part is in the connections database (which means it is also in parts)

        returns True/False, unless return_active True (return list of active connections)
        """
        revq = rev_query.upper()
        if revq == 'LAST':
            revq = part_connect.get_last_revision(self.args,hpn_query,False)

        connection_dict = self.get_connections(hpn_query,revq,exact_match=True,return_dictionary=True,show_connection=False)
        num_connections = len(connection_dict.keys())
        if num_connections == len(self.non_class_connections_dict_entries):
            found_connected = False
        else:
            found_connected = True
            if return_active:
                connections_found = []
                current = cm_utils._get_datetime(self.args.date,self.args.time)
                for c in connection_dict.keys():
                    if c in self.non_class_connections_dict_entries:
                        continue
                    if cm_utils._is_active(current,connection_dict[c].start_date,connection_dict[c].stop_date):
                        connections_found.append(c)
                if len(connections_found)>0:
                    found_connected = connections_found
        return found_connected


    def get_part(self, hpn_query=None, rev_query=None, exact_match=False, return_dictionary=True, show_part=False):
        """
        Return information on a part.  It will return all matching first characters unless exact_match==True.
        It gets all parts, the receiving module should filter on date if desired.

        Returns part_dict: {'part':CLASS , 'part_info':CLASS, 'connections':CLASS ,'geo':DICT, 'input_ports':[], 'output_ports':[]}

        Parameters
        -----------
        args:  arguments as per mc and parts argument parser
        hpn_query:  the input hera part number (whole or first part thereof)
        exact_match:  boolean to enforce full part number match
        show_part:  boolean to call show_part or not
        """
        args=self.args
        if hpn_query is None:
            hpn_query = args.hpn
            exact_match = args.exact_match
        if rev_query is None:
            rev_query = args.revision
        if not exact_match and hpn_query[-1]!='%':
            hpn_query = hpn_query+'%'

        part_dict = {}
        db = mc.connect_to_mc_db(args)
        with db.sessionmaker() as session:
            # Get part(s):revision number dictionary (Need it to handle LAST revision)
            rev_part = {}
            for fp in session.query(part_connect.Parts).filter(part_connect.Parts.hpn.like(hpn_query)):
                rq = rev_query.upper()
                if rq == 'LAST':
                    rq = part_connect.get_last_revision(args,fp.hpn,False)
                rev_part[fp.hpn] = rq

            ### Now get unique part/rev and put into dictionary
            for hpn in rev_part.keys():
                part_query = session.query(part_connect.Parts).filter( (part_connect.Parts.hpn==hpn) &
                                                                       (part_connect.Parts.hpn_rev==rev_part[hpn]) )
                part_cnt = part_query.count()
                if part_cnt == 0:
                    continue
                elif part_cnt == 1:
                    part = copy.copy(part_query.all()[0])
                    pr_key = _make_part_key(part.hpn,part.hpn_rev)
                    part_dict[pr_key] = {'part':part, 'part_info':None, 
                                         'input_ports':[], 'output_ports':[], 
                                         'connections':None, 'geo':None}
                    for part_info in session.query(part_connect.PartInfo).filter( (part_connect.PartInfo.hpn == part.hpn) &
                                                                                  (part_connect.PartInfo.hpn_rev == part.hpn_rev) ):
                        part_dict[pr_key]['part_info'] = part_info
                    connections = self.get_connections(hpn_query=part.hpn, rev_query = part.hpn_rev, port_query='all', 
                                                       exact_match=True, return_dictionary=True, show_connection=False)
                    part_dict[pr_key]['connections'] = connections
                    if part.hptype == 'station':
                        args.locate = part.hpn
                        part_dict[pr_key]['geo'] = geo_location.locate_station(args, show_geo=False)
                    ptsin = ''; ptsout = ''
                    for k,v in part_dict[pr_key]['connections'].iteritems():
                        if k in self.non_class_connections_dict_entries:  continue
                        if ':up:' in k:     part_dict[pr_key]['input_ports'].append(v.downstream_input_port)
                        elif ':down:' in k: part_dict[pr_key]['output_ports'].append(v.upstream_output_port)
                        else: print("cm_handling[158]: ERROR SHOULD BE UP or DOWN ",k)
                        part_dict[pr_key]['output_ports'].sort()
                        part_dict[pr_key]['input_ports'].sort()
                else:
                    print("Warning cm_handling[115]:  Well, being here is a surprise -- should only be one part.", part.hpn)
        if show_part:
            self.show_part(part_dict)
        if return_dictionary:
            return part_dict


    def show_part(self, part_dict):
        """
        Print out part information.  Uses tabulate package.

        Parameters
        -----------
        part_dict:  input dictionary of parts, generated by self.get_part
        """
        if len(part_dict.keys()) == 0:
            print('Part not found')
            return
        current = cm_utils._get_datetime(self.args.date,self.args.time)
        table_data = []
        if self.args.verbosity == 'm':
            headers = ['HERA P/N','Rev','Part Type','Mfg #','Start','Stop','Active']
        elif self.args.verbosity == 'h':
            headers = ['HERA P/N','Rev','Part Type','Mfg #','Start','Stop','Active','Input','Output','Info','Geo']
        for hpnr in sorted(part_dict.keys()):
            pdpart = part_dict[hpnr]['part']
            is_active = cm_utils._is_active(current, pdpart.start_date, pdpart.stop_date)
            show_it = True
            if self.args.active:
                if not is_active:
                    show_it = False
            if show_it:
                active = 'Yes' if (is_active and len(part_dict[hpnr]['connections'])>0) else 'N/C' if is_active else 'No'
                if self.args.verbosity == 'l':
                    print(pdpart)
                else:
                    tdata = [pdpart.hpn, pdpart.hpn_rev, pdpart.hptype, pdpart.manufacturer_number,
                             pdpart.start_date, pdpart.stop_date, active]
                    if self.args.verbosity == 'h':
                        ptsin = ''; ptsout = ''
                        for k in part_dict[hpnr]['input_ports']:
                            ptsin+=k+', '
                        for k in part_dict[hpnr]['output_ports']:
                            ptsout+=k+', '
                        tdata.append(ptsin.strip().strip(',')); tdata.append(ptsout.strip().strip(','))
                        comment = part_dict[hpnr]['part_info'].comment if (part_dict[hpnr]['part_info'] is not None) else None
                        tdata.append(comment)
                        if part_dict[hpnr]['geo'] is not None:
                            tdata.append("{:.1f}E, {:.1f}N, {:.1f}m".format(part_dict[hpnr]['geo']['easting'],
                                          part_dict[hpnr]['geo']['northing'],part_dict[hpnr]['geo']['elevation']))
                        else:
                            tdata.append(None)
                        table_data.append(tdata)
        print('\n'+tabulate(table_data,headers=headers,tablefmt='orgtbl')+'\n')


    def get_connections(self, hpn_query=None, rev_query=None, port_query=None, exact_match=False, 
                             return_dictionary=True, show_connection=False):
        """
        Return information on parts connected to hpn_query (args.connection)
        It should get connections immediately adjacent to one part (upstream and downstream).
        It does not filter on date but gets all.  The receiving (or showing module) should filter
           on date if desired.

        Returns connection_dict, a dictionary keyed on part number of adjacent connections

        Parameters
        -----------
        args:  arguments as per mc and parts argument parser
        hpn_query:  the input hera part number (whole or first part thereof)
        port_query:  a specifiable port name,  default is 'all'
        exact_match:  boolean to enforce full part number match
        show_connection:  boolean to call show_part or not
        """
        args = self.args
        if hpn_query is None:
            hpn_query = args.connection
            exact_match = args.exact_match
        if rev_query is None:
            rev_query = args.revision
        if not exact_match and hpn_query[-1]!='%':
            hpn_query = hpn_query+'%'
        if port_query is None:
            port_query = args.specify_port
        connection_dict = {'ordered_pairs':None}
        down_parts = []
        up_parts = []
        db = mc.connect_to_mc_db(args)
        with db.sessionmaker() as session:
            rev_part = {}
            for fp in session.query(part_connect.Parts).filter(part_connect.Parts.hpn.like(hpn_query)):
                rq = rev_query.upper()
                if rq == 'LAST':
                    rq = part_connect.get_last_revision(args,fp.hpn,False)
                rev_part[fp.hpn] = rq
            for hpn in rev_part.keys():
                ### Find where the part is in the upward connection, so identify its downward connection
                for conn in session.query(part_connect.Connections).filter( (part_connect.Connections.upstream_part == hpn) &
                                                                            (part_connect.Connections.up_part_rev == rev_part[hpn]) ):
                    if port_query.lower()=='all' or match_connection.upstream_output_port.lower() == port_query.lower():
                        prc_key = _make_connection_key(hpn,rev_part[hpn],'down',conn.downstream_part,conn.start_date)
                        connection_dict[prc_key] = copy.copy(conn)
                        down_parts.append(prc_key)
                ### Find where the part is in the downward connection, so identify its upward connection
                for conn in session.query(part_connect.Connections).filter( (part_connect.Connections.downstream_part == hpn) &
                                                                            (part_connect.Connections.down_part_rev == rev_part[hpn]) ):
                    if port_query.lower()=='all' or match_connection.downstream_input_port.lower() == port_query.lower():
                        prc_key = _make_connection_key(hpn,rev_part[hpn],'up',conn.upstream_part,conn.start_date)
                        connection_dict[prc_key] = copy.copy(conn)
                        up_parts.append(prc_key)
        if len(up_parts) > len(down_parts):
            down_parts = (down_parts + len(up_parts)*[self.no_connection_designator])[:len(up_parts)]
        elif len(down_parts) > len(up_parts):
            up_parts = (up_parts + len(down_parts)*[self.no_connection_designator])[:len(down_parts)]
        connection_dict['ordered_pairs'] = [sorted(up_parts),sorted(down_parts)]
        nc = self.no_connection_designator
        connection_dict[nc] = part_connect.Connections(upstream_part=nc,upstream_output_port=nc,up_part_rev=nc,
                                                       downstream_part=nc,downstream_input_port=nc,down_part_rev=nc,
                                                       start_date=cm_utils._get_datetime('<','<'),
                                                       stop_date=cm_utils._get_datetime('>','>'))
        if show_connection:
            self.show_connection(connection_dict)
        if return_dictionary:
            return connection_dict
            

    def show_connection(self, connection_dict):
        """
        Print out connection information.  Uses tabulate package.

        Parameters
        -----------
        connection_dict:  input dictionary of parts, generated by self.get_connection
        """
        
        current = cm_utils._get_datetime(self.args.date,self.args.time)
        table_data = []
        ordered_pairs = connection_dict['ordered_pairs']
        vb = self.args.verbosity
        if vb == 'm':
            headers = ['Upstream', '<Output:', ':Input>', 'Part', '<Output:', ':Input>', 'Downstream']
        elif vb == 'h':
            headers = ['Upstream', '<Output:', ':Input>', 'Part', '<Output:', ':Input>', 'Downstream']
        for i,up in enumerate(connection_dict['ordered_pairs'][0]):
            dn = connection_dict['ordered_pairs'][1][i]
            tdata = range(0,len(headers))
            # Do upstream
            connup = connection_dict[up]
            pos = {'Upstream':{'h':0,'m':0}, 'Output':{'h':1,'m':1}, 'Input':{'h':2,'m':2}, 'Part':{'h':3,'m':3}}
            if pos['Upstream'][vb] > -1:
                del tdata[pos['Upstream'][vb]]
                tdata.insert(pos['Upstream'][vb],connup.upstream_part)
            if pos['Output'][vb] > -1:
                del tdata[pos['Output'][vb]]
                tdata.insert(pos['Output'][vb],connup.upstream_output_port)
            if pos['Input'][vb] > -1:
                del tdata[pos['Input'][vb]]
                tdata.insert(pos['Input'][vb],connup.downstream_input_port)
            if pos['Part'][vb] > -1:
                del tdata[pos['Part'][vb]]
                tdata.insert(pos['Part'][vb],'['+connup.downstream_part+']')
            # Do downstream
            conndn = connection_dict[dn]
            pos = {'Part':{'h':3,'m':3}, 'Output':{'h':4,'m':4}, 'Input':{'h':5,'m':5}, 'Downstream':{'h':6,'m':6}}
            if connup.downstream_part==self.no_connection_designator:
                if pos['Part'][vb] > -1:
                    del tdata[pos['Part'][vb]]
                    tdata.insert(pos['Part'][vb],'['+conndn.upstream_part+']')
            if pos['Output'][vb] > -1:
                del tdata[pos['Output'][vb]]
                tdata.insert(pos['Output'][vb],conndn.upstream_output_port)
            if pos['Input'][vb] > -1:
                del tdata[pos['Input'][vb]]
                tdata.insert(pos['Input'][vb],conndn.downstream_input_port)
            if pos['Downstream'][vb] > -1:
                del tdata[pos['Downstream'][vb]]
                tdata.insert(pos['Downstream'][vb],conndn.downstream_part)
            # Write to row list if desired
            show_it = True
            if self.args.active:
                show_it = cm_utils._is_active(current,connup.start_date,connup.stop_date) or \
                          cm_utils._is_active(current,conndn.start_date,conndn.stop_date)
            if show_it:
                if vb == 'h' or vb == 'm':
                    table_data.append(tdata)
                else:
                    print("Connections")
        if vb=='m' or vb=='h':
            print('\n'+tabulate(table_data,headers=headers,tablefmt='orgtbl')+'\n')


    def __get_next_part(self, hpn, rev, port, direction, first_one=False):
        """
        Get next part going the direction.  Called via hookup
        Return list of [[part,rev,port,start1,stop1],...]
        """

        end_of_the_line = False
        part_dict = self.get_part(hpn_query=hpn,rev_query=rev, exact_match=True, return_dictionary=True, show_part=False)
        if len(part_dict.keys()) == 0:
            return None
        pk = part_dict.keys()[0] # is only one, but get the key
        if port in part_dict[pk]['input_ports']:
            if direction == 'down':
                try:
                    port = part_dict[pk]['output_ports'][part_dict[pk]['input_ports'].index(port)]
                except IndexError:
                    end_of_the_line = True
        elif port in part_dict[pk]['output_ports']:
            if direction == 'up':
                try:
                    port = part_dict[pk]['input_ports'][part_dict[pk]['output_ports'].index(port)]
                except IndexError:
                    end_of_the_line = True
        else:
            print('cm_handling[349]: not there',hpn,rev,port)
            end_of_the_line = True

        if end_of_the_line:
            return None

        return_parts = []
        if first_one:
            if direction == 'up': 
                return_parts = [hpn,rev,port,None,None]
        else:       
            for k,c in part_dict[pk]['connections'].iteritems():
                if k in self.non_class_connections_dict_entries:  continue
                next_part = []
                if direction == 'up':
                    if c.downstream_part == hpn and c.down_part_rev == rev and c.downstream_input_port == port:
                        next_part = [c.upstream_part,c.up_part_rev,c.upstream_output_port,c.start_date,c.stop_date]
                elif direction == 'down':
                    if c.upstream_part == hpn and c.up_part_rev == rev and c.upstream_output_port == port:
                        next_part = [c.downstream_part,c.down_part_rev,c.downstream_input_port,c.start_date,c.stop_date]
                if len(next_part)>0:
                    return_parts.append(next_part)
        return return_parts


    def __recursive_go(self, direction, hpn, rev, port):
        """
        Find the next connection up the signal chain.
        """
        next_parts = self.__get_next_part(hpn,rev,port,direction)
        if next_parts is not None:
            for part in next_parts:
                if self.no_connection_designator in part:
                    pass
                else:
                    if direction=='up':
                        self.upstream.append(part)
                    else:
                        self.downstream.append(part)
                self.__recursive_go(direction, part[0], part[1], part[2])


    def get_hookup(self, hpn_query=None, rev_query=None, port_query='all', show_hookup=False):
        """
        Return the full hookup.  Note that if a part is selected up or down stream of a branching part, 
        it picks one and doesn't give all options -- something to work on.
        Returns hookup_dict, a dictionary keyed on derived key of hpn:port.  Returns all entries,
           if you want to filter on date the receiving (or showing) module should do that.

        Parameters
        -----------
        hpn_query:  the input hera part number (whole or first part thereof)
        port_query:  a specifiable port name,  default is 'all'
        show_hookup:  boolean to call show_hookup or not

        """
        args = self.args
        self.current = cm_utils._get_datetime(args.date,args.time)
        exact_match = args.exact_match
        if hpn_query is None:
            hpn_query = self.args.mapr
            exact_match = self.args.exact_match
        if rev_query is None:
            rev_query = args.revision
        port_query = self.args.specify_port if self.args.specify_port!='all' else port_query
        parts = self.get_part(hpn_query=hpn_query, rev_query=rev_query, 
                exact_match=exact_match, return_dictionary=True, show_part=False)
        connections = None
        hookup_dict = {}
        for hpnr in parts.keys():
            rq = rev_query.upper()
            part_no = parts[hpnr]['part'].hpn
            part_rev= parts[hpnr]['part'].hpn_rev
            if rq == 'LAST':
                rq = part_connect.get_last_revision(args, part_no, False)
            if len(parts[hpnr]['connections']['ordered_pairs'][0]) == 0:
                continue
            if type(port_query) == str and port_query.lower() == 'all':
                port_query = parts[hpnr]['input_ports']
            else:  # This to handle range of port_query possibilities outside of 'all'
                if type(port_query) != list:
                    port_query = [port_query]
            for p in port_query:
                self.upstream = []
                self.downstream = []
                self.upstream.append(self.__get_next_part(part_no, rq, p, 'up', first_one=True))
                self.__recursive_go('up', part_no, rq, p)
                self.__recursive_go('down', part_no, rq, p)

                furthest_up = self.upstream[-1]
                try_station = self.get_part(hpn_query=furthest_up[0],rev_query=furthest_up[1],
                              exact_match=True, return_dictionary=True, show_part=False)
                keep_entry = True
                hukey = _make_hookup_key(part_no, part_rev, p)

                station_try_key = _make_part_key(furthest_up[0],furthest_up[1])
                if try_station[station_try_key]['part'].hptype == 'station':
                    hookup_dict[hukey] = [[str(try_station[station_try_key]['geo']['antenna_number']),'S']]
                else:
                    hookup_dict[hukey] = []
                for pn in reversed(self.upstream):
                    hookup_dict[hukey].append(pn)
                for pn in self.downstream:
                    hookup_dict[hukey].append(pn)
        if len(hookup_dict.keys())==0:
            print(hpn_query,'not found')
            return None
        tkey = hookup_dict.keys()[0]
        hookup_dict['columns'] = []
        for hu in hookup_dict[tkey]:
            if hu[1]=='S':
                hookup_dict['columns'].append(['station','column'])
            else:
                get_part_type = self.get_part(hpn_query=hu[0],rev_query=hu[1],
                                exact_match=True, return_dictionary=True, show_part=False)
                pr_key = _make_part_key(hu[0],hu[1])
                hookup_dict['columns'].append([get_part_type[pr_key]['part'].hptype,'column'])
        if args.show_levels:
            hookup_dict = self.__hookup_add_correlator_levels(hookup_dict,args.levels_testing)
        if show_hookup:
            self.show_hookup(hookup_dict,args.mapr_cols,args.show_levels,args.active)
        return hookup_dict


    def __hookup_add_correlator_levels(self,hookup_dict,testing):
        hookup_dict['columns'].append(['levels','column'])
        pf_input = []
        for k in sorted(hookup_dict.keys()):
            if k=='columns':
                continue
            f_engine = hookup_dict[k][-1][0].strip('*')
            pf_input.append(f_engine)
        levels = correlator_levels.get_levels(pf_input,testing)
        for i,k in enumerate(sorted(hookup_dict.keys())):
            if k=='columns':
                continue
            lstr = '%s' % (levels[i])
            hookup_dict[k].append([lstr,pf_input[i]])
        return hookup_dict


    def show_hookup(self, hookup_dict, cols_to_show, show_levels, show_active_only=True):
        """
        Print out the hookup table -- uses tabulate package.  
        Station is used twice, so grouped together and applies some ad hoc formatting.

        Parameters
        -----------
        hookup_dict:  generated in self.get_hookup
        """

        headers = []
        show_flag = []
        if cols_to_show != 'all':
            cols_to_show=cols_to_show.split(',')
            if show_levels:
                cols_to_show.append('levels')
        for col in hookup_dict['columns']:
            if col[0][-2:]=='_e' or col[0][-2:]=='_n': #Makes these specific pol parts generic
                colhead = col[0][:-2]
            else:
                colhead = col[0]
            if cols_to_show == 'all' or colhead in cols_to_show:
                show_flag.append(True)
            else:
                show_flag.append(False)
                continue
            if colhead not in headers: #Accounts for station used twice
                headers.append(colhead)
        if show_levels:
            show_flag.append(True)
        table_data = []
        for hukey in sorted(hookup_dict.keys()):
            if hukey=='columns':
                continue
            if len(hookup_dict[hukey]) != len(hookup_dict['columns']):
                print('Issues with ',hukey)
                continue
            td = []
            show_it = True
            for i,pn in enumerate(hookup_dict[hukey]):
                if show_active_only and '*' in pn[0]:
                    show_it = False
                    break
                if not i or not show_flag[i]:  #If station first time or not shown
                    continue
                if i==1:
                    s = "{:0>3}  {}".format(str(hookup_dict[hukey][0][0]), str(hookup_dict[hukey][1][0]))
                else:
                    if pn[0] == hukey.split(':')[0]:
                        s = '['+pn[0]+']'
                    else:
                        s = pn[0]
                td.append(s)
            if show_it:
                table_data.append(td)
        print(tabulate(table_data,headers=headers,tablefmt='orgtbl'))
        print('\n')

    def get_part_types(self, show_hptype=False):
        """
        Goes through database and pulls out part types and some other info to display in a table.

        Returns part_type_dict, a dictionary keyed on part type

        Parameters
        -----------
        args:  arguments as per mc and parts argument parser
        show_hptype:  boolean variable to print it out
        """
        
        self.part_type_dict = {}
        db = mc.connect_to_mc_db(self.args)
        with db.sessionmaker() as session:
            for part in session.query(part_connect.Parts).all():
                if part.hptype not in self.part_type_dict.keys():
                    self.part_type_dict[part.hptype] = {'part_list':[part.hpn], 'input_ports':[], 'output_ports':[]}
                else:
                    self.part_type_dict[part.hptype]['part_list'].append(part.hpn)
        if show_hptype:
            headers = ['Part type','# in dbase','A ports','B ports']
            table_data = []
        for k in self.part_type_dict.keys():  ###ASSUME FIRST PART IS FULLY CONNECTED
            pa = self.part_type_dict[k]['part_list'][0]  
            pd = self.get_part(pa,show_part=False)
            self.part_type_dict[k]['input_ports'] = pd[pa]['input_ports']
            self.part_type_dict[k]['output_ports'] = pd[pa]['output_ports']
            if show_hptype:
                td = [k,len(self.part_type_dict[k]['part_list'])]
                pts = ''
                for a in self.part_type_dict[k]['input_ports']:
                    pts+=(a+', ')
                td.append(pts.strip().strip(','))
                pts = ''
                for b in self.part_type_dict[k]['output_ports']:
                    pts+=(b+', ')
                td.append(pts.strip().strip(','))
                table_data.append(td)
        if show_hptype:
            print(tabulate(table_data,headers=headers,tablefmt='orgtbl'))          
        return self.part_type_dict


