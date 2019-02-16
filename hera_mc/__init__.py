# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

from __future__ import absolute_import, division, print_function

from types import MethodType
import numpy as np
import six

# Before we can do anything else, we need to initialize some core, shared
# variables.

from alembic.operations import Operations, MigrateOperation
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import DDLElement
from sqlalchemy.sql import table, label
from sqlalchemy.ext import compiler
from sqlalchemy import select

# define some default tolerances for various units
DEFAULT_DAY_TOL = {'atol': 1e-3 / (3600. * 24.), 'rtol': 0}  # ms
DEFAULT_HOUR_TOL = {'atol': 1e-3 / (3600), 'rtol': 0}  # ms
DEFAULT_MIN_TOL = {'atol': 1e-3 / (3600), 'rtol': 0}  # ms
DEFAULT_GPS_TOL = {'atol': 1e-3, 'rtol': 0}  # ms

# approximate gps to linux conversion to use in views for grafana
GPS_TO_UNIX_SEC = 315964782


class MCDeclarativeBase(object):
    def __repr__(self):
        columns = self.__table__.columns.keys()
        rep_str = '<' + self.__class__.__name__ + '('
        for c in columns:
            rep_str += c + ': ' + str(getattr(self, c)) + ', '
        rep_str = rep_str[0:-2]
        rep_str += ')>'
        return rep_str

    def isclose(self, other):
        if not isinstance(other, self.__class__):
            print('not the same class')
            return False

        self_columns = self.__table__.columns
        other_columns = other.__table__.columns
        if set(c.name for c in self_columns) != set(c.name for c in other_columns):
            print('set of columns are not the same')
            return False

        for c in self_columns:
            self_c = getattr(self, c.name)
            other_c = getattr(other, c.name)
            if isinstance(self_c, six.string_types + six.integer_types):
                if self_c != other_c:
                    print('column {col} is string-like or int-like, values are not '
                          'equal'.format(col=c))
                    return False
            elif isinstance(self_c, np.ndarray) and self_c.dtype.kind == 'i':
                if not np.all(self_c == other_c):
                    print('column {col} is an int-like array, values are not equal'.format(col=c))
                    return False
            elif self_c is None and other_c is None:
                pass  # nullable columns, both null
            else:
                if hasattr(self, 'tols') and c.name in self.tols.keys():
                    atol = self.tols[c.name]['atol']
                    rtol = self.tols[c.name]['rtol']
                else:
                    # use numpy defaults
                    atol = 1e-08
                    rtol = 1e-05
                if not np.isclose(self_c, other_c, atol=atol, rtol=rtol):
                    print('column {col} is float-like or a float-like array, values are not equal'.format(col=c))
                    return False
        return True


MCDeclarativeBase = declarative_base(cls=MCDeclarativeBase)


# create SQLAlchemy based objects for views
class CreateView(DDLElement):
    def __init__(self, name, selectable):
        self.name = name
        self.selectable = selectable


class DropView(DDLElement):
    def __init__(self, name):
        self.name = name


# This is used to generate the actual sqltext for Alembic
class ViewSQLText(DDLElement):
    def __init__(self, selectable):
        self.selectable = selectable


@compiler.compiles(CreateView)
def compile(element, compiler, **kw):
    return "CREATE VIEW %s AS %s" % (
        element.name,
        compiler.sql_compiler.process(element.selectable, literal_binds=True))


@compiler.compiles(ViewSQLText)
def compile(element, compiler, **kw):
    return compiler.sql_compiler.process(element.selectable, literal_binds=True)


@compiler.compiles(DropView)
def compile(element, compiler, **kw):
    return "DROP VIEW %s" % (element.name)


def view(name, metadata, selectable):
    t = table(name)

    for c in selectable.c:
        c._make_proxy(t)

    CreateView(name, selectable).execute_at('after-create', metadata)
    DropView(name).execute_at('before-drop', metadata)
    return t


def gps_to_unix(gps_second):
    return gps_second + GPS_TO_UNIX_SEC


# This function returns a dict with the attributes needed to make a new View object:
#   e.g. MyView = type('MyView', (MCDeclarativeBase,), mc_view(base_table_obj, ['time']))
# It would be nice to make this a base object that a new view object can inherit from
# but this is pretty close and I can't figure out how to do any better.
# !!! All new views need to be added to the Alembic version by hand -- they are not picked up in the autogeneration!!!
def mc_view(base_table_obj, gps_column_list):
    columns = list(base_table_obj.__table__.columns)

    column_names = [column.key for column in columns]
    for gps_col in gps_column_list:
        assert gps_col in column_names

    view_attributes = [getattr(base_table_obj, name) for name in column_names]
    label_obj_list = []
    for gps_col in gps_column_list:
        col_index = np.where(np.array(column_names) == gps_col)[0][0]
        label_obj_list.append(label(gps_col + '_unix', gps_to_unix(columns[col_index])))

    selectable = select(view_attributes + label_obj_list)
    view_name = base_table_obj.__tablename__ + '_view'

    return {'view_base_table': base_table_obj.__tablename__,
            '__tablename__': view_name,
            'sqltext': ViewSQLText(selectable),
            '__table__': view(view_name, MCDeclarativeBase.metadata, selectable)}


# create Alembic-based classes to handle views properly,
# based on: https://alembic.sqlalchemy.org/en/latest/cookbook.html
# not including the saved procedure part now, if needed can be added later
class ReversibleOp(MigrateOperation):
    def __init__(self, target):
        self.target = target

    @classmethod
    def invoke_for_target(cls, operations, target):
        op = cls(target)
        return operations.invoke(op)

    def reverse(self):
        raise NotImplementedError()

    @classmethod
    def _get_object_from_version(cls, operations, ident):
        version, objname = ident.split(".")

        module = operations.get_context().script.get_revision(version).module
        obj = getattr(module, objname)
        return obj

    @classmethod
    def replace(cls, operations, target, replaces=None, replace_with=None):

        if replaces:
            old_obj = cls._get_object_from_version(operations, replaces)
            drop_old = cls(old_obj).reverse()
            create_new = cls(target)
        elif replace_with:
            old_obj = cls._get_object_from_version(operations, replace_with)
            drop_old = cls(target).reverse()
            create_new = cls(old_obj)
        else:
            raise TypeError("replaces or replace_with is required")

        operations.invoke(drop_old)
        operations.invoke(create_new)


@Operations.register_operation("create_view", "invoke_for_target")
@Operations.register_operation("replace_view", "replace")
class CreateViewOp(ReversibleOp):
    def reverse(self):
        return DropViewOp(self.target)


@Operations.register_operation("drop_view", "invoke_for_target")
class DropViewOp(ReversibleOp):
    def reverse(self):
        return CreateViewOp(self.view)

# This assumes that View object have these attributes: __tablename__ & sqltext
@Operations.implementation_for(CreateViewOp)
def create_view(operations, operation):

    operations.execute("CREATE VIEW %s AS %s" % (
        operation.target.__tablename__,
        operation.target.sqltext
    ))


@Operations.implementation_for(DropViewOp)
def drop_view(operations, operation):
    operations.execute("DROP VIEW %s" % operation.target.__tablename__)


import logging  # noqa
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Now we can pull in the rest of our definitions.


def NotNull(kind, **kwargs):
    from sqlalchemy import Column
    return Column(kind, nullable=False, **kwargs)


from . import version  # noqa
from . import autocorrelations  # noqa
from . import cm_transfer  # noqa
from . import part_connect  # noqa
from . import geo_location  # noqa
from . import observations  # noqa
from . import subsystem_error  # noqa
from . import server_status  # noqa
from . import librarian  # noqa
from . import rtp  # noqa
from . import qm  # noqa
from . import weather  # noqa
from . import node  # noqa
from . import correlator  # noqa
from . import mc    # noqa keep this last.

__version__ = version.version
