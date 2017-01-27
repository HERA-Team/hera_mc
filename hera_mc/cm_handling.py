#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
This is meant to hold helpful modules for parts and connections scripts

"""
from __future__ import absolute_import, division, print_function
from tabulate import tabulate

from hera_mc import mc, part_connect, geo_location, correlator_levels, cm_utils
import copy


class Handling:
    """
    Class to allow various manipulations of parts and their properties etc.  Things are 
    manipulated/passed as dictionaries currently.
    """
    no_connection_designator = '--'
    last_revisions = {}
    connections_dictionary = {}
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

        connection_dict = self.get_connection(hpn_query,revq,exact_match=True,return_dictionary=True,show_connection=False)
        num_connections = len(connection_dict.keys())
        if num_connections == 0:
            found_connected = False
        elif num_connections == 1:
            found_connected = True
            if return_active:
                connections_found = []
                current = cm_utils._get_datetime(self.args.date,self.args.time)
                for c in connection_dict:
                    if cm_utils._is_active(current,c.start_date,c.stop_date):
                        connections_found.append(c)
        else:
            found_connected = False
            print("Shouldn't get here, since is_in_connctions is exact_match.")
        return found_connected


    def get_part(self, hpn_query=None, rev_query=None, exact_match=False, return_dictionary=True, show_part=False):
        """
        Return information on a part.  It will return all matching first characters unless exact_match==True.
        It gets all parts, you check if active later if desired.

        Returns part_dict: {'part':CLASS , 'part_info':CLASS, 'connections':CLASS ,'geo':DICT}

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
                if part_cnt == 0:     ### None found.
                    continue
                elif part_cnt == 1:
                    part = copy.copy(part_query.all()[0])
                    pr_key = part.hpn+':'+part.hpn_rev
                    part_dict[pr_key] = {'part':part, 'part_info':None, 'connections':None, 'geo':None}
                    for part_info in session.query(part_connect.PartInfo).filter( (part_connect.PartInfo.hpn == part.hpn) &
                                                                                  (part_connect.PartInfo.hpn_rev == part.hpn_rev) ):
                        part_dict[pr_key]['part_info'] = part_info
                    connections = self.get_connections(hpn_query=part.hpn, rev_query = part.hpn_rev, port_query='all', 
                                                       exact_match=True, return_dictionary=True, show_connection=False)
                    part_dict[pr_key]['connections'] = connections
                    if part.hptype == 'station':
                        args.locate = part.hpn
                        part_dict[pr_key]['geo'] = geo_location.locate_station(args, show_geo=False)
                else:   ### Found more than one, which shouldn't happen.
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
                        for k,v in part_dict[hpnr]['connections'].iteritems():
                            if 'up:' in k:     ptsout+=(v.upstream_output_port+', ')
                            elif 'down:' in k: ptsin+=(v.downstream_input_port+', ')
                            else: print("cm_handling[171]: ERROR SHOULD BE ONE OF THE TWO")
                        tdata.append(ptsin.strip().strip(',')); tdata.append(ptsout.strip().strip(','))
                        comment = part_dict[hpnr]['part_info'].comment if (part_dict[hpnr]['part_info'] is not None) else None
                        tdata.append(comment)
                        if part_dict[hpnr]['geo'] is not None:
                            tdata.append("{:.1f}E, {:.1f}N, {:.1f}m".format(part_dict[hpnr]['geo']['easting'],
                                          part_dict[hpnr]['geo']['northing'],part_dict[hpnr]['geo']['elevation']))
                        else:
                            tdata.append(None)
                        table_data.append(tdata)
        print(tabulate(table_data,headers=headers,tablefmt='orgtbl')+'\n')


    def get_connections(self, hpn_query=None, rev_query=None, port_query=None, exact_match=False, 
                             return_dictionary=True, show_connection=False):
        """
        Return information on parts connected to args.connection -- NEED TO INCLUDE USING START/STOP_TIME!!!
        It should get connections immediately adjacent to one part (upstream and downstream).

        Returns connection_dict, a dictionary keyed on part number of adjacent connections

        NB:  I don't think that it handles general cases very well (ie. potentially likely incorrectly)
             That is, I'm not sure that the list structure within the dict entries necessarily correspond
             to the general case.  It might possibly work for the current actual case...

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
        connection_dict = {}
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
                        pr_key = ':'.join([hpn,rev_part[hpn],'down',conn.downstream_part])
                        connection_dict[pr_key] = copy.copy(conn)
                        down_parts.append(pr_key)
                ### Find where the part is in the downward connection, so identify its upward connection
                for conn in session.query(part_connect.Connections).filter( (part_connect.Connections.downstream_part == hpn) &
                                                                            (part_connect.Connections.down_part_rev == rev_part[hpn]) ):
                    if port_query.lower()=='all' or match_connection.downstream_input_port.lower() == port_query.lower():
                        pr_key = ':'.join([hpn,rev_part[hpn],'up',conn.upstream_part])
                        connection_dict[pr_key] = copy.copy(conn)
                        up_parts.append(pr_key)
        if show_connection:
            ordered_pairs = [sorted(up_parts),sorted(down_parts)]
            self.show_connection(ordered_pairs, connection_dict)
        if return_dictionary:
            return connection_dict
            

    def show_connection(self, ordered_pairs, connection_dict):
        """
        Print out connection information.  Uses tabulate package.

        Parameters
        -----------
        ordered_pairs:  ordered up/down pairs of keys, generated by self.get_connection
        connection_dict:  input dictionary of parts, generated by self.get_connection
        """
        
        current = cm_utils._get_datetime(self.args.date,self.args.time)
        table_data = []
        vb = self.args.verbosity
        if vb == 'm':
            headers = ['Upstream', '<Output:', ':Input>', 'Part', '<Output:', ':Input>', 'Downstream']
        elif vb == 'h':
            headers = ['Upstream', '<Output:', ':Input>', 'Part', '<Output:', ':Input>', 'Downstream']
        for i,up in enumerate(ordered_pairs[0]):
            dn = ordered_pairs[1][i]
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
            pos = {'Output':{'h':4,'m':4}, 'Input':{'h':5,'m':5}, 'Downstream':{'h':6,'m':6}}
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
            print(tabulate(table_data,headers=headers,tablefmt='orgtbl')+'\n')



    def __get_next_port(self,hpn,rev,port,direction,check_part):
        """
        Get port on correct side of a given part to move up/down stream.
        """
        if check_part:
            part_dict = check_part
        else:
            part_dict = self.get_part(hpn_query=hpn,rev_query=rev,
                exact_match=True, return_dictionary=True, show_part=False)
        if direction=='up':
            ports = [part_dict[hpn]['input_ports'],part_dict[hpn]['output_ports']]
            replacing = ['b','a']
        elif direction=='down':
            ports = [part_dict[hpn]['output_ports'],part_dict[hpn]['input_ports']]
            replacing = ['a','b']
        number_of_ports = [len(ports[0]),len(ports[1])]
        for i,p in enumerate(ports):
            if self.no_connection_designator in p: #This will only take out one.
                number_of_ports[i]-=1
        if port in ports[0]:
            return_port = port
        elif number_of_ports[0] == 1:
            return_port = ports[0][0]
        elif number_of_ports[0] == 0:
            return_port = None
        elif port in ports[1]:
            if number_of_ports[1] == number_of_ports[0]:
                return_port = port.replace(replacing[0],replacing[1])
            elif number_of_ports[1] > number_of_ports[0]: # SHOULDN'T GET HERE
                return_port = ports[0][0]                 #   BUT JUST IN CASE PICK ONE
            else:                                         # HERE IS THE ILL-DEFINED BRANCHING CASE
                return_port = ports[0][0]                 #   PICK ONE FOR NOW
        else:
            print('Error:  port not found',port)
            return_port = None 
        return return_port

    def __go_upstream(self, hpn, rev, port):
        """
        Find the next connection up the signal chain.
        """
        up_port = self.__get_next_port(hpn,rev,port,direction='up',check_part=False)
        if up_port == self.no_connection_designator or up_port is None:
            return
        connection_dict = self.get_connection(hpn_query=hpn, rev_query=rev, port_query=up_port, 
                                              exact_match=True, show_connection=False)
        for i,hpn_up in enumerate(connection_dict[hpn]['up_parts']):
            port = connection_dict[hpn]['upstream_output_port'][i]
            if hpn_up not in self.upstream:
                stopup = cm_utils._get_stopdate(connection_dict[hpn]['stop_on_up'][i])
                if (self.current>connection_dict[hpn]['start_on_up'][i]) and (self.current<stopup):
                    hpn_up_pr = hpn_up
                else:
                    hpn_up_pr = '**'+hpn_up
                self.upstream.append([hpn_up_pr,port])
            self.__go_upstream(hpn_up, rev, port)

    def __go_downstream(self, hpn, rev, port):
        """
        Find the next connection down the signal chain
        """
        down_port = self.__get_next_port(hpn,rev,port,direction='down',check_part=False)
        if down_port == self.no_connection_designator or down_port is None:
            return
        connection_dict = self.get_connection(hpn_query=hpn, rev_query=rev, port_query=down_port, 
                                              exact_match=True, show_connection=False)
        for i,hpn_down in enumerate(connection_dict[hpn]['down_parts']):
            port = connection_dict[hpn]['downstream_input_port'][i]
            if hpn_down not in self.downstream:
                stopdown = cm_utils._get_stopdate(connection_dict[hpn]['stop_on_down'][i])
                if (self.current>connection_dict[hpn]['start_on_down'][i]) and (self.current<stopdown):
                    hpn_down_pr = hpn_down
                else:
                    hpn_down_pr = '**'+hpn_down
                self.downstream.append([hpn_down_pr,port])
            self.__go_downstream(hpn_down, rev, port)


    def get_hookup(self, hpn_query=None, rev_query=None, port_query=None, show_hookup=False):
        """
        Return the full hookup.  Note that if a part is selected up or down stream of a branching part, 
        it picks one and doesn't give all options -- something to work on.
        Returns hookup_dict, a dictionary keyed on derived key of hpn:port

        Parameters
        -----------
        args:  arguments as per mc and parts argument parser
        hpn_query:  the input hera part number (whole or first part thereof)
        port_query:  a specifiable port name,  default is 'all'
        show_hookup:  boolean to call show_hookup or not

        """
        args = self.args
        self.current = cm_utils._get_datetime(args.date,args.time)
        exact_match = False
        if hpn_query is None:
            hpn_query = self.args.mapr
            exact_match = self.args.exact_match
        if rev_query is None:
            rev_query = args.revision
        if port_query is None:
            port_query = self.args.specify_port
        parts = self.get_part(hpn_query=hpn_query, rev_query=rev_query, 
                exact_match=exact_match, return_dictionary=True, show_part=False)
        connections = None
        hookup_dict = {}
        for hpn in parts.keys():
            if parts[hpn]['is_connected'] == False:
                continue
            number_a_ports = len(parts[hpn]['input_ports'])
            number_b_ports = len(parts[hpn]['output_ports'])
            if port_query == 'all':
                if number_b_ports>number_a_ports:
                    pq = 'output_ports'
                    alt_pq = 'input_ports'
                else:
                    pq = 'input_ports'
                    alt_pq = 'output_ports'
                port_query = parts[hpn][pq]
                if self.no_connection_designator in port_query:
                    port_query = parts[hpn][alt_pq]
            elif type(port_query) is not list:
                port_query = [port_query]
            for p in port_query:
                if p == self.no_connection_designator:
                    continue
                self.upstream = [[hpn,p]]
                self.downstream = []
                self.__go_upstream(hpn, rev_query, p)
                self.__go_downstream(hpn, rev_query, p)
                furthest_up = self.upstream[-1][0].strip('*')
                try_station = self.get_part(hpn_query=furthest_up,rev_query=rev_query,
                              exact_match=True, return_dictionary=True, show_part=False)
                keep_entry = True
                hukey = hpn+':'+p
                if try_station[furthest_up]['hptype'] == 'station':
                    hookup_dict[hukey] = [[str(try_station[furthest_up]['geo']['antenna_number']),'S']]
                else:
                    hookup_dict[hukey] = []
                for pn in reversed(self.upstream):
                    hookup_dict[hukey].append(pn)
                for pn in self.downstream:
                    hookup_dict[hukey].append(pn)
                #-#for pkey in hookup_dict.keys():
                #-#    print('#-#==>', hookup_dict[pkey])
        if len(hookup_dict.keys())==0:
            print(hpn_query,'not found')
            return None
        tkey = hookup_dict.keys()[0]
        hookup_dict['columns'] = []
        for hu in hookup_dict[tkey]:
            pn = hu[0].strip('*')
            if hu[1]=='S':
                hookup_dict['columns'].append(['station','column'])
            else:
                get_part_type = self.get_part(hpn_query=pn,rev_query=rev_query,
                                exact_match=True, return_dictionary=True, show_part=False)
                hookup_dict['columns'].append([get_part_type[pn]['hptype'],'column'])
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


