import datetime
from itertools import repeat
from django.db.models.query import EmptyResultSet
from compositekey.db.models.sql.wherein import MultipleColumnsIN
from compositekey.utils import disassemble_pk

__author__ = 'aldaran'


class Atoms(object):
    def __init__(self, fields, sql_colums):
        self.fields = fields
        self.sql_colums = sql_colums

    def make_atoms(self, params, lookup_type, value_annot, qn, connection):
        if lookup_type == 'in':
            return MultipleColumnsIN(self.sql_colums, params).as_sql(qn, connection)

        if lookup_type in ['iexact']:
            # we have to be sure
            params = [[field.get_prep_value(val) for field, val in zip(self.fields, disassemble_pk(params[0]))]]

        atoms = zip(*[self.make_atom(field_sql, param, lookup_type, value_annot, qn, connection) for field_sql, param in zip(self.sql_colums, zip(*params))])
        if not atoms: return "", []
        sql, new_params = atoms

        # [0] is a bad smell
        return " AND ".join(sql), zip(*new_params)[0]

    def make_atom(self, field_sql, params, lookup_type, value_annot, qn, connection):
        
        if value_annot is datetime.datetime:
            cast_sql = connection.ops.datetime_cast_sql()
        else:
            cast_sql = '%s'

        if hasattr(params, 'as_sql'):
            extra, params = params.as_sql(qn, connection)
            cast_sql = ''
        else:
            extra = ''

        if (len(params) == 1 and params[0] == '' and lookup_type == 'exact'
            and connection.features.interprets_empty_strings_as_nulls):
            lookup_type = 'isnull'
            value_annot = True

        if lookup_type in connection.operators:
            format = "%s %%s %%s" % (connection.ops.lookup_cast(lookup_type),)
            return (format % (field_sql,
                              connection.operators[lookup_type] % cast_sql,
                              extra), params)

# todo: check lookup_type VALID for multicolumn
#        if lookup_type in ('range', 'year'):
#            return ('%s BETWEEN %%s and %%s' % field_sql, params)
#        elif lookup_type in ('month', 'day', 'week_day'):
#            return ('%s = %%s' % connection.ops.date_extract_sql(lookup_type, field_sql),
#                    params)
#        elif lookup_type == 'isnull':
#            return ('%s IS %sNULL' % (field_sql,
#                (not value_annot and 'NOT ' or '')), ())
#        elif lookup_type == 'search':
#            return (connection.ops.fulltext_search_sql(field_sql), params)
#        elif lookup_type in ('regex', 'iregex'):
#            return connection.ops.regex_lookup(lookup_type) % (field_sql, cast_sql), params

        raise TypeError('Invalid lookup_type: %r' % lookup_type)

class MultiColumn(object):
    def __init__(self, fields):
        self.fields = fields
        self.columns = [f.column for f in fields]

    def sql_for_columns(self, data, qn, connection):
        """
        "WHERE ...
        T1.foo = 6.
        T1.bar = 4
        """
        table_alias, _name, db_type = data

        fun = connection.ops.field_cast_sql

        if table_alias:
            lhs = [fun(f.db_type(connection)) % '%s.%s' % (qn(table_alias), qn(f.column)) for f in self.fields]
        else:
            lhs = [fun(f.db_type(connection)) % qn(f.column) for f in self.fields]
        return Atoms(self.fields, lhs)

    def __repr__(self):
        return ",".join(self.columns)

    def startswith(self, _):
        raise Exception(self.fields, self.columns)

    endswith = startswith