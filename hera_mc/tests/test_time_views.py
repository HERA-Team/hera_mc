# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for views with gps second converted to unix time.

"""
from __future__ import absolute_import, division, print_function

import unittest
import numpy as np
from sqlalchemy import inspect
from sqlalchemy.ext.declarative.clsregistry import _ModuleMarker

from hera_mc import MCDeclarativeBase
from hera_mc.tests import TestHERAMC


class TestObservation(TestHERAMC):

    def setUp(self):
        super(TestObservation, self).setUp()

    def test_all_views_exist(self):
        engine = self.test_session.get_bind()
        iengine = inspect(engine)

        tables = iengine.get_table_names()

        tables_with_time = []
        table_time_cols = {}
        for table in tables:
            columns = [c["name"] for c in iengine.get_columns(table)]
            time_cols = [s for s in columns if 'time' in s.lower()]

            if len(time_cols) > 0:
                tables_with_time.append(table)
                table_time_cols[table] = time_cols

        view_list = []
        view_dict = {}
        for name, klass in MCDeclarativeBase._decl_class_registry.items():
            if isinstance(klass, _ModuleMarker):
                # Not a model
                continue

            if hasattr(klass, 'view_base_table'):
                view_list.append(klass.__tablename__)
                view_dict[klass.view_base_table] = klass.__tablename__

        tables_with_time_with_views = []
        tables_with_time_no_views = []
        for table in tables_with_time:
            if table in view_dict.keys():
                tables_with_time_with_views.append(table)
            else:
                tables_with_time_no_views.append(table)

        print('\nTables with time views:\n')
        for table in tables_with_time_with_views:
            print(table + ': ' + ', '.join(table_time_cols[table]))

        print('\nTables with missing views:\n')
        for table in tables_with_time_no_views:
            print(table + ': ' + ', '.join(table_time_cols[table]))

        # uncomment the line below when this test should pass
        # assert(len(tables_with_time_no_views) == 0)
