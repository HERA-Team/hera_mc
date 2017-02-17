#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
This is computes and displays part hookups.

"""
from __future__ import absolute_import, division, print_function
from tabulate import tabulate
import sys

from hera_mc import mc, part_connect, geo_location, correlator_levels, cm_utils, cm_handling
import copy

def _make_hookup_key(hpn,rev,port):
    return ":".join([hpn,rev,port])

class Hookup:
    """
    Class to compute and display the hookup.
    """
    def __init__(self,args):
        self.args = args
        self.handling = cm_handling.Handling(args)

    def __get_first_part(self, hpn, rev, port):
        """
        Get the first part.  Called via hookup
        Return list of [[part,rev,port,start1,stop1,input_ports,output_ports],...]
        """

        part_dict = self.handling.get_part(hpn_query=hpn,rev_query=rev, exact_match=True, 
                                           return_dictionary=True, show_part=False)
        if len(part_dict.keys()) == 0:
            first_part = None
        else:
            if len(part_dict.keys()) > 1:
                print('cm_hookup[42] more than one, ok?')
            part = part_dict[part_dict.keys()[0]] # should be only one, but ...

            first_part = [hpn, rev, port, 
                          part['part'].start_date, part['part'].stop_date,
                          part['input_ports'], part['output_ports']]
        return first_part


    def __follow_port_stream(self, portstream):
        part_no  = portstream['part_number']
        part_rev = portstream['revision']
        port     = portstream['port']

        self.upstream = []
        self.downstream = []
        self.upstream.append(self.__get_first_part(part_no, part_rev, port))
        self.__recursive_go('up',   part_no, part_rev, port)
        self.__recursive_go('down', part_no, part_rev, port)

        furthest_up = self.upstream[-1]
        try_station = self.handling.get_part(hpn_query=furthest_up[0],rev_query=furthest_up[1],
                      exact_match=True, return_dictionary=True, show_part=False)
        station_try_key = cm_handling._make_part_key(furthest_up[0],furthest_up[1])
        if try_station[station_try_key]['part'].hptype == 'station':
            antenna_number = geo_location.is_in_connections(self.args,try_station[station_try_key]['geo'].station_name,True)
            hu = [[str(antenna_number),'S']]
        else:
            hu = [[self.handling.no_connection_designator]]
        for pn in reversed(self.upstream):
            hu.append(pn)
        for pn in self.downstream:
            hu.append(pn)
        return hu

    def __get_next_port(self, part_dict, port, direction):
        # Get port facing the correct direction and check whether you are at the end
        pk = part_dict.keys()[0]
        end_of_the_line = False
        if len(part_dict[pk]['input_ports']) == 0 and len(part_dict[pk]['output_ports']) == 0:
            end_of_the_line = True
        elif port in part_dict[pk]['input_ports']:
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
            print('cm_hookup[94]: not there',pk,port)
            end_of_the_line = True
        if end_of_the_line:
            port = None
        return port

    def __get_next_part(self, hpn, rev, port, direction):
        """
        Get next part going the given direction.  Called via hookup
        Return list of [[part,rev,port,start1,stop1,input_ports,output_ports],...]
        """

        # Get the current part information
        part_dict = self.handling.get_part(hpn_query=hpn,rev_query=rev, exact_match=True, 
                                           return_dictionary=True, show_part=False)
        if len(part_dict.keys()) == 0:
            return None
        elif len(part_dict.keys()) > 1:
            print('cm_hookup[66] more than one, ok?')
        pk = part_dict.keys()[0] # should be only one, but get the key

        port = self.__get_next_port(part_dict,port,direction)
        if port is None:
            return None

        return_parts = []       
        for k,c in part_dict[pk]['connections'].iteritems():
            if k in self.handling.non_class_connections_dict_entries:  continue
            next_part = []
            if direction == 'up':
                if c.downstream_part == hpn and c.down_part_rev == rev and c.downstream_input_port == port:
                    ports4part = self.handling.get_part(hpn_query=c.upstream_part,rev_query=c.up_part_rev, 
                                               exact_match=True, return_dictionary=True, show_part=False)
                    p4p = ports4part.keys()[0]
                    next_part = [c.upstream_part,c.up_part_rev,c.upstream_output_port,c.start_date,c.stop_date,
                                 ports4part[p4p]['input_ports'], ports4part[p4p]['output_ports']]
            elif direction == 'down':
                if c.upstream_part == hpn and c.up_part_rev == rev and c.upstream_output_port == port:
                    ports4part = self.handling.get_part(hpn_query=c.downstream_part,rev_query=c.down_part_rev, 
                                               exact_match=True, return_dictionary=True, show_part=False)
                    p4p = ports4part.keys()[0]
                    next_part = [c.downstream_part,c.down_part_rev,c.downstream_input_port,c.start_date,c.stop_date,
                                 ports4part[p4p]['input_ports'], ports4part[p4p]['output_ports']]
            if len(next_part)>0:
                return_parts.append(next_part)
        if len(return_parts)==0:
            return_parts = None
        return return_parts


    def __recursive_go(self, direction, hpn, rev, port):
        """
        Find the next connection up the signal chain.
        """
        next_parts = self.__get_next_part(hpn,rev,port,direction)
        if next_parts is not None:
            for part in next_parts:
                if cm_utils._is_active(self.current,part[3],part[4]):
                    if self.handling.no_connection_designator in part:
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
        Returns hookup_dict, a dictionary keyed on derived key of hpn:port.
        This only gets the contemporary hookups (unlike parts and connections, which get all.)

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
        if rev_query is None:
            rev_query = args.revision
        port_query = self.args.specify_port if self.args.specify_port!='all' else port_query
        parts = self.handling.get_part(hpn_query=hpn_query, rev_query=rev_query, 
                exact_match=exact_match, return_dictionary=True, show_part=False)

        hookup_dict = {}
        for hpnr in parts.keys():
            if not cm_utils._is_active(self.current,parts[hpnr]['part'].start_date,parts[hpnr]['part'].stop_date):
                continue
            part_no = parts[hpnr]['part'].hpn
            part_rev= parts[hpnr]['part'].hpn_rev
            if len(parts[hpnr]['connections']['ordered_pairs'][0]) == 0:
                continue
            if type(port_query) == str and port_query.lower() == 'all':
                port_query = parts[hpnr]['input_ports']
                if len(port_query) == 0:
                    port_query = parts[hpnr]['output_ports']
            else:  # This to handle range of port_query possibilities outside of 'all'
                if type(port_query) != list:
                    port_query = [port_query]
            for p in port_query:
                portstream = {'part_number':part_no, 'revision':part_rev, 'port':p}
                hukey = _make_hookup_key(part_no, part_rev, p)
                hookup_dict[hukey] = self.__follow_port_stream(portstream)
        if len(hookup_dict.keys())==0:
            print(hpn_query,rev_query,'not active')
            return None
        tkey = hookup_dict.keys()[0]
        hookup_dict['columns'] = []
        for hu in hookup_dict[tkey]:
            if len(hu)<2:
                continue
            if hu[1]=='S':
                hookup_dict['columns'].append(['station','column'])
            else:
                get_part_type = self.handling.get_part(hpn_query=hu[0],rev_query=hu[1],
                                exact_match=True, return_dictionary=True, show_part=False)
                pr_key = cm_handling._make_part_key(hu[0],hu[1])
                hookup_dict['columns'].append([get_part_type[pr_key]['part'].hptype,'column'])
        if args.show_levels:
            hookup_dict = self.__hookup_add_correlator_levels(hookup_dict,args.levels_testing)
        if show_hookup:
            self.show_hookup(hookup_dict,args.mapr_cols,args.show_levels)
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


    def show_hookup(self, hookup_dict, cols_to_show, show_levels):
        """
        Print out the hookup table -- uses tabulate package.  
        Station is used twice, so grouped together and applies some ad hoc formatting.

        Parameters
        -----------
        hookup_dict:  generated in self.get_hookup
        """
        # print('cm_handling[507]')
        # for hk in hookup_dict.keys():
        #     print(hk, hookup_dict[hk])
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
                #print('cm_handling[554]',i,pn)
                if not i or not show_flag[i]:  #If station first time or not shown
                    continue   #This is a clunky way to do it, but keep for now (so i==0 is 'special')
                if i==1:
                    prpn = "{:0>3}  {}:{}({})".format(str(hookup_dict[hukey][0][0]), pn[0],pn[1],pn[6][0])
                else:
                    inputp = ''
                    for p in pn[5]:
                        inputp+=(p+',')
                    prpn = inputp.strip(',')+'>'
                    if pn[0] == hukey.split(':')[0]:
                        prpn+= '['+pn[0]+':'+pn[1]+']'
                    else:
                        prpn+= pn[0]+':'+pn[1]
                    outputp = ''
                    for p in pn[6]:
                        outputp+=(p+',')
                    prpn+=('<'+outputp.strip(','))
                td.append(prpn)
            if show_it:
                table_data.append(td)
        print(tabulate(table_data,headers=headers,tablefmt='orgtbl'))
        print('\n')

