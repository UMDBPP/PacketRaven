from ast import literal_eval
from datetime import date, datetime
from functools import partial
from typing import Any, Union

import psycopg2
from pyproj import CRS
from shapely import wkb, wkt
from shapely.errors import WKBReadingError, WKTReadingError
from shapely.geometry import LineString, LinearRing, MultiLineString, MultiPoint, MultiPolygon, Point, Polygon, shape as shapely_shape
from shapely.geometry.base import BaseGeometry
from sshtunnel import SSHTunnelForwarder

from packetraven.utilities import get_logger

LOGGER = get_logger('packetraven.connection')

POSTGRES_DEFAULT_PORT = 5432
SSH_DEFAULT_PORT = 22

POSTGRES_TYPES = {
    'NoneType' : 'NULL',
    'bool'     : 'BOOL',
    'float'    : 'REAL',
    'int'      : 'INTEGER',
    'str'      : 'VARCHAR',
    'bytes'    : 'BYTEA',
    'date'     : 'DATE',
    'time'     : 'TIME',
    'datetime' : 'TIMESTAMP',
    'timedelta': 'INTERVAL',
    'list'     : 'VARCHAR[]',
    'dict'     : 'HSTORE',
    'ipaddress': 'INET',
    'Point'    : 'GEOMETRY'
}

DEFAULT_CRS = CRS.from_epsg(4326)
GEOMETRY_TYPES = (Point, LineString, Polygon, MultiPoint, MultiLineString, MultiPolygon)


class InheritedTableError(Exception):
    pass


class DatabaseTable:
    def __init__(self, hostname: str, database: str, table: str, fields: {str: type}, primary_key: str = None, crs: CRS = None, username: str = None, password: str = None, users: [str] = None,
                 **kwargs):
        self.hostname = hostname
        self.database = database
        self.table = table

        self.fields = fields
        self.primary_key = primary_key
        self.crs = crs if crs is not None else DEFAULT_CRS

        self.username = username
        self.password = password
        if users is None:
            users = []

        # parse port from URL
        self.hostname, self.port = split_URL_port(hostname)
        if self.port is None:
            self.port = POSTGRES_DEFAULT_PORT

        connector = partial(psycopg2.connect, database=self.database, user=self.username, password=self.password, port=self.port)
        if 'ssh_hostname' in kwargs or 'ssh_port' in kwargs:
            with SSHTunnelForwarder((kwargs['ssh_hostname'] if 'ssh_hostname' in kwargs else self.hostname,
                                     int(kwargs['ssh_port']) if 'ssh_port' in kwargs else SSH_DEFAULT_PORT),
                                    ssh_username=kwargs['ssh_username'] if 'ssh_username' in kwargs else None,
                                    ssh_password=kwargs['ssh_password'] if 'ssh_password' in kwargs else None,
                                    remote_bind_address=('localhost', self.port)):
                self.connection = connector(host='localhost')
        else:
            self.connection = connector(host=self.hostname)

        with self.connection:
            with self.connection.cursor() as cursor:
                if database_has_table(cursor, self.table):
                    if database_table_is_inherited(cursor, self.table):
                        raise InheritedTableError(f'inheritance of table "{self.database}/{self.table}" will cause unexpected behaviour; aborting')

                    remote_fields = self.remote_fields
                    if list(remote_fields) != list(self.fields):
                        LOGGER.warning(f'schema of existing table "{self.database}/{self.table}" differs from given fields')

                        remote_fields_not_in_local_table = {field: value for field, value in remote_fields.items() if field not in self.fields}
                        if len(remote_fields_not_in_local_table) > 0:
                            LOGGER.warning(f'remote table has {len(remote_fields_not_in_local_table)} fields not in local table: {list(remote_fields_not_in_local_table)}')
                            LOGGER.warning(f'adding {len(remote_fields_not_in_local_table)} fields to local table: {list(remote_fields_not_in_local_table)}')

                            for field, field_type in remote_fields_not_in_local_table.items():
                                previous_field = list(remote_fields)[list(remote_fields).index(field) - 1]

                                local_fields = {}
                                for local_field, local_value in self.fields.items():
                                    local_fields[local_field] = local_value
                                    if local_field == previous_field:
                                        local_fields[field] = field_type

                                self.fields = local_fields

                        local_fields_not_in_remote_table = {field: value for field, value in self.fields.items() if field not in remote_fields}
                        if len(local_fields_not_in_remote_table) > 0:
                            LOGGER.warning(f'local table has {len(local_fields_not_in_remote_table)} fields not in remote table: {list(local_fields_not_in_remote_table)}')
                            LOGGER.warning(f'adding {len(local_fields_not_in_remote_table)} fields to remote table: {list(local_fields_not_in_remote_table)}')

                        if list(remote_fields) != list(self.fields):
                            LOGGER.warning(f'altering schema of "{self.database}/{self.table}"')
                            LOGGER.debug(self.remote_fields)
                            LOGGER.debug(self.fields)

                            copy_table_name = f'old_{self.table}'

                            if database_has_table(cursor, copy_table_name):
                                cursor.execute(f'DROP TABLE {copy_table_name};')

                            cursor.execute(f'ALTER TABLE {self.table} RENAME TO {copy_table_name};')

                            cursor.execute(f'CREATE TABLE {self.table} ({self.schema});')
                            for user in users:
                                cursor.execute(f'GRANT INSERT, SELECT, UPDATE, DELETE ON TABLE public.{self.table} TO {user};')

                            cursor.execute('SELECT column_name FROM information_schema.columns WHERE table_name=%s;', [f'{copy_table_name}'])
                            column_names = [record[0] for record in cursor.fetchall()]

                            cursor.execute(f'INSERT INTO {self.table} ({", ".join(column_names)}) SELECT * FROM {copy_table_name};')

                            cursor.execute(f'DROP TABLE {copy_table_name};')
                else:
                    LOGGER.warning(f'creating remote table "{self.database}/{self.table}"')
                    cursor.execute(f'CREATE TABLE {self.table} ({self.schema});')

                    for user in users:
                        cursor.execute(f'GRANT INSERT, SELECT, UPDATE, DELETE ON TABLE public.{self.table} TO {user};')

    def __getitem__(self, key: Any) -> {str: Any}:
        """
        Query table for the given value of the primary key.

        Parameters
        ----------
        key
            value to query from primary key

        Returns
        -------
        {str: Any}
            dictionary record
        """

        records = self.records_where({self.primary_key: key})

        if len(records) > 1:
            LOGGER.warning(f'found more than one record with primary key "{self.primary_key} = {key}": {records}')

        return records[0]

    def __setitem__(self, key: Any, record: {str: Any}):
        """
        Insert the given record into the table with the given primary key value.

        Parameters
        ----------
        key
            value of primary key at which to insert record
        record
            dictionary record
        """

        record[self.primary_key] = key
        self.insert([record])

    @property
    def records(self) -> [{str: Any}]:
        with self.connection:
            with self.connection.cursor() as cursor:
                cursor.execute(f'SELECT {", ".join(self.fields.keys())} FROM {self.table}')
                records = cursor.fetchall()

        return [parse_record_values(dict(zip(self.fields.keys(), record)), self.fields) for record in records]

    def records_where(self, where: {str: Union[Any, list]}) -> [{str: Any}]:
        """
        records in the table that match the given key-value pairs

        Parameters
        ----------
        where
            dictionary mapping keys to values, with which to match records

        Returns
        -------
        [{str: Any}]
            dictionaries of matching records
        """

        records = []
        try:
            for record in self.records:
                match = True
                for key, value in where.items():
                    if key in record:
                        record_value = record[key]
                        if type(value) in [tuple, list, slice, range]:
                            if record_value not in value:
                                match = False
                        elif value != record_value if value is not None else value is not record_value:
                            match = False
                    else:
                        match = False
                if match:
                    records.append(record)
        except KeyError:
            LOGGER.warning(f'no records found with given constraints: {where}')
        return records

    def insert(self, records: [{str: Any}]):
        """
        Insert the list of records into the table.

        Parameters
        ----------
        records
            dictionary records
        """

        if type(records) is dict:
            records = [records]

        assert all(self.primary_key in record for record in records), f'one or more records does not contain primary key "{self.primary_key}"'

        with self.connection:
            with self.connection.cursor() as cursor:
                for record in records:
                    record_fields_not_in_local_table = [field for field in record if field not in self.fields]
                    if len(record_fields_not_in_local_table) > 0:
                        LOGGER.warning(f'record has {len(record_fields_not_in_local_table)} fields not in the local table that will not be inserted: {record_fields_not_in_local_table}')

                    local_fields_in_record = [field for field in self.fields if field in record]
                    geometry_fields = [field for field in self.geometry_fields if field in record]

                    columns = [field for field in local_fields_in_record if field not in geometry_fields]
                    values = [record[field] for field in local_fields_in_record if field not in geometry_fields]

                    if database_table_has_record(cursor, self.table, record, self.primary_key):
                        record_without_primary_key = {column: value for column, value in zip(columns, values) if column != self.primary_key}

                        if len(record_without_primary_key) > 0:
                            if len(record_without_primary_key) > 1:
                                cursor.execute(f'UPDATE {self.table} SET ({", ".join(record_without_primary_key.keys())}) = %s WHERE {self.primary_key} = %s;',
                                               [tuple(record_without_primary_key.values()), record[self.primary_key]])
                            else:
                                cursor.execute(f'UPDATE {self.table} SET {tuple(record_without_primary_key.keys())[0]} = %s WHERE {self.primary_key} = %s;',
                                               [tuple(record_without_primary_key.values())[0], record[self.primary_key]])
                    else:
                        cursor.execute(f'INSERT INTO {self.table} ({", ".join(columns)}) VALUES %s;', [tuple(values)])

                    if len(geometry_fields) > 0:
                        geometries = {field: record[field] for field in geometry_fields}

                        for field, geometry in geometries.items():
                            cursor.execute(f'UPDATE {self.table} SET {field} = ST_GeomFromWKB(%s::geometry, %s) ' +
                                           f'WHERE {self.primary_key} = %s;', [geometry.wkb, self.crs.to_epsg(), record[self.primary_key]])

    @property
    def schema(self) -> str:
        """ PostGres schema string of local table, given field names and types """

        schema = []
        for field, field_type in self.fields.items():
            dimensions = 0
            while type(field_type) is list:
                field_type = field_type[0]
                dimensions += 1

            field_definition = f'{field} {POSTGRES_TYPES[field_type.__name__]}{"[]" * dimensions}'

            if field == self.primary_key:
                field_definition = f'{field_definition} PRIMARY KEY'

            schema.append(field_definition)

        return ', '.join(schema)

    @property
    def remote_fields(self) -> {str: type}:
        with self.connection:
            with self.connection.cursor() as cursor:
                if database_has_table(cursor, self.table):
                    cursor.execute(f'SELECT column_name, udt_name FROM information_schema.columns WHERE table_name=%s;', [self.table])
                    fields = {field[0]: field[1] for field in cursor.fetchall()}

                    for field, field_type in fields.items():
                        dimensions = field_type.count('_')
                        field_type = field_type.strip('_')

                        field_type = field_type.lower()
                        for python_type, postgres_type in POSTGRES_TYPES.items():
                            if postgres_type.lower() == field_type:
                                field_type = eval(python_type)
                                break
                        else:
                            for python_type, postgres_type in POSTGRES_TYPES.items():
                                if python_type.lower() in field_type:
                                    field_type = eval(python_type)
                                    break
                            else:
                                field_type = str

                        for _ in range(dimensions):
                            field_type = [field_type]
                        fields[field] = field_type

                    return fields

    @property
    def geometry_fields(self) -> {str: type}:
        return {field: field_type for field, field_type in self.fields.items() if field_type in GEOMETRY_TYPES}

    def __contains__(self, key: Any) -> bool:
        with self.connection:
            with self.connection.cursor() as cursor:
                return database_table_has_record(cursor, self.table, {self.primary_key: key})

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.hostname}, {self.database}, {self.table}, {self.fields}, {self.primary_key}, {self.crs}, {self.username}, {self.password})'


def parse_record_values(record: {str: Any}, field_types: {str: type}) -> {str: Any}:
    """
    Parse the values in the given record into their respective field types.

    Parameters
    ----------
    record
        dictionary mapping fields to values
    field_types
        dictionary mapping fields to types

    Returns
    -------
    {str: Any}
        record with values parsed into their respective types
    """

    for field, value in record.items():
        if field in field_types:
            field_type = field_types[field]
            value_type = type(value)

            if value_type is not field_type:
                if field_type is bool:
                    value = bool(value) if value_type is not str else literal_eval(value.capitalize())
                elif field_type is int:
                    value = int(value)
                elif field_type is float:
                    value = float(value)
                elif field_type is str:
                    value = str(value)
                elif value_type is str:
                    if field_type is list:
                        value = literal_eval(value)
                    elif field_type in (date, datetime):
                        value = datetime.strptime(value, '%Y%m%d')
                        if field_type is date:
                            value = value.date()
                    elif field_type in GEOMETRY_TYPES:
                        try:
                            value = wkb.loads(value, hex=True)
                        except WKBReadingError:
                            try:
                                value = wkt.loads(value)
                            except WKTReadingError:
                                try:
                                    value = wkb.loads(value)
                                except TypeError:
                                    value = shapely_shape(literal_eval(value))
                record[field] = value
    return record


def flatten_geometry(geometry: BaseGeometry) -> BaseGeometry:
    geometry_type = type(geometry)

    # strip 3rd dimension
    if 'POLYGON Z' in geometry.wkt:
        polygons = [polygon for polygon in geometry] if geometry_type is MultiPolygon else [geometry]
        for polygon_index, polygon in enumerate(polygons):
            exterior_2d = LinearRing([vertex[:2] for vertex in polygon.exterior.coords])
            interiors_2d = [LinearRing([vertex[:2] for vertex in interior.coords]) for interior in polygon.interiors]
            polygons[polygon_index] = Polygon(exterior_2d, interiors_2d)
        geometry = MultiPolygon(polygons) if geometry_type is MultiPolygon else Polygon(polygons[0])

    if not geometry.is_valid:
        geometry = geometry.buffer(0)
    return geometry


def database_has_table(cursor: psycopg2._psycopg.cursor, table: str) -> bool:
    """
    Whether the given table exists within the given database.

    Parameters
    ----------
    cursor
        psycopg2 cursor
    table
        name of table

    Returns
    -------
    bool
        whether table exists
    """

    cursor.execute(f'SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name=%s);', [table.lower()])
    return cursor.fetchone()[0]


def database_table_has_record(cursor: psycopg2._psycopg.cursor, table: str, record: {str: Any}, primary_key: str = None) -> bool:
    """
    Whether the given record exists within the given table.

    Parameters
    ----------
    cursor
        psycopg2 cursor
    table
        name of table
    record
        dictionary record
    primary_key
        name of primary key

    Returns
    -------
    bool
        whether record exists in table
    """

    if primary_key is None:
        # cursor.execute(f'SELECT 1 FROM information_schema.table_constraints WHERE table_name=\'{table}\' AND constraint_type= \'PRIMARY KEY\';')
        # primary_key_index = cursor.fetchone()[0] - 1
        #
        # cursor.execute(f'SELECT * FROM information_schema.columns WHERE table_name=\'{table}\';')
        # primary_key = cursor.fetchall()[primary_key_index]
        primary_key = list(record)[0]

    value = record[primary_key]
    if type(value) is date:
        value = f'{value:%Y%m%d}'
    elif type(value) is datetime:
        value = f'{value:%Y%m%d %H%M%S}'

    cursor.execute(f'SELECT EXISTS(SELECT 1 FROM {table} WHERE {primary_key}=%s);', [value])
    return cursor.fetchone()[0]


def database_table_is_inherited(cursor: psycopg2._psycopg.cursor, table: str) -> bool:
    """
    Whether the given table is inherited.

    Parameters
    ----------
    cursor
        psycopg2 cursor
    table
        name of table

    Returns
    -------
    bool
        whether table is inherited
    """

    cursor.execute(f'SELECT EXISTS(SELECT 1 FROM pg_catalog.pg_inherits WHERE inhrelid=%s::regclass);', [f'public.{table}'])
    return cursor.fetchone()[0]


def database_table_columns(cursor: psycopg2._psycopg.cursor, table: str) -> {str: str}:
    """
    Get column names and data types of the given table, within the given database.

    Parameters
    ----------
    cursor
        psycopg2 cursor
    table
        name of table

    Returns
    -------
    {str: str}
        mapping of column names to the PostGres data type
    """

    cursor.execute(f'SELECT column_name, udt_name FROM information_schema.columns WHERE table_name=%s;', [table])
    return {record[0]: record[1] for record in cursor.fetchall()}


def postgis_geometry(geometry: Union[Point, LineString, Polygon, MultiPoint, MultiLineString, MultiPolygon], epsg: int = None) -> str:
    """
    Convert Shapely geometry to a PostGIS geometry string.

    Parameters
    ----------
    geometry
        Shapely geometry
    epsg
        EPSG code of CRS

    Returns
    -------
    str
        PostGIS input string
    """

    if epsg is None:
        epsg = 4326

    return f'ST_SetSRID(\'{geometry.wkb_hex}\'::geometry, {epsg})'


def split_URL_port(url: str) -> (str, Union[str, None]):
    """
    Split the given URL into host and port, assuming port is appended after a colon.

    Parameters
    ----------
    url
        URL string

    Returns
    ----------
    str, Union[str, None]
        URL and port (if found)
    """

    port = None

    if url.count(':') > 0:
        url = url.split(':')
        if 'http' in url:
            url = ':'.join(url[:2])
            if len(url) > 2:
                port = int(url[2])
        else:
            url, port = url
            port = int(port)

    return url, port
