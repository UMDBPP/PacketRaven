import logging
import os

from tablecrow.utilities import parse_hostname

from packetraven.configuration.base import (
    ConfigurationSection,
    ConfigurationYAML,
    PacketSourceConfiguration,
)
from packetraven.connections.internet import APRSfi, APRSis, PacketDatabaseTable


class SSHCredentials(ConfigurationYAML, ConfigurationSection):
    name = 'tunnel'
    fields = {
        'hostname': str,
        'port': int,
        'username': str,
        'password': str,
    }
    defaults = {
        'port': 22,
    }

    @classmethod
    def from_connection_string(cls, connection_string: str):
        configuration = {}
        if connection_string is not None:
            configuration = parse_hostname(connection_string)
        return cls(**configuration)


class DatabaseCredentials(ConfigurationYAML, ConfigurationSection, PacketSourceConfiguration):
    name = 'database'
    fields = {
        'hostname': str,
        'port': int,
        'database': str,
        'table': str,
        'username': str,
        'password': str,
        'tunnel': SSHCredentials,
    }
    defaults = {
        'hostname': os.getenv('POSTGRES_HOSTNAME', 'localhost'),
        'port': os.getenv('POSTGRES_PORT', 5432),
        'database': os.getenv('POSTGRES_DATABASE', 'postgres'),
        'username': os.getenv('POSTGRES_USERNAME', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', ''),
    }

    @classmethod
    def from_connection_string(cls, connection_string: str, tunnel: SSHCredentials = None):
        configuration = {}
        if tunnel is not None:
            configuration['tunnel'] = tunnel
        if connection_string is not None:
            parsed = parse_hostname(connection_string)

            hostname = parsed['hostname']
            port = parsed['port']
            username = parsed['username']
            password = parsed['password']

            if hostname.count('/') != 2:
                logging.warning(f'unable to parse connection information from "{parsed}"')

            (
                configuration['hostname'],
                configuration['database'],
                configuration['table'],
            ) = hostname.split('/')

            configuration['username'] = username
            configuration['password'] = password
            configuration['port'] = port

        return cls(**configuration)

    def packet_source(self, callsigns: [str] = None) -> PacketDatabaseTable:
        ssh_kwargs = {}
        if self['tunnel'] is not None:
            ssh_kwargs.update({f'ssh_{key}': value for key, value in self['tunnel'].items()})

        return PacketDatabaseTable(
            hostname=self['hostname'],
            database=self['database'],
            table=self['table'],
            callsigns=callsigns,
            **ssh_kwargs,
        )


class APRSfiCredentials(ConfigurationYAML, ConfigurationSection, PacketSourceConfiguration):
    name = 'aprs_fi'
    fields = {
        'api_key': str,
    }
    defaults = {
        'api_key': os.getenv('APRS_FI_API_KEY', None),
    }

    def packet_source(self, callsigns: [str] = None) -> APRSfi:
        return APRSfi(callsigns=callsigns, api_key=self['api_key'])


class APRSisCredentials(ConfigurationYAML, ConfigurationSection, PacketSourceConfiguration):
    name = 'aprs_is'
    fields = {
        'hostname': str,
    }

    def packet_source(self, callsigns: [str] = None) -> APRSis:
        return APRSis(callsigns=callsigns, hostname=self['hostname'])


class CredentialsYAML(ConfigurationYAML):
    fields = {
        'aprs_fi': APRSfiCredentials,
        'database': DatabaseCredentials,
        'aprs_is': APRSisCredentials,
    }

    def __init__(self, **configuration):
        for section in [APRSfiCredentials, DatabaseCredentials, APRSisCredentials]:
            if section.name in configuration:
                configuration[section.name] = section(**configuration[section.name])
        super().__init__(**configuration)
