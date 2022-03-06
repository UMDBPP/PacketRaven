from packetraven.configuration.base import ConfigurationSection, ConfigurationYAML


class DatabaseCredentials(ConfigurationYAML, ConfigurationSection):
    name = 'database'
    fields = {
        'hostname': str,
        'port': int,
        'database': str,
        'table': str,
        'username': str,
        'password': str,
        'ssh_hostname': str,
        'ssh_port': int,
        'ssh_username': str,
        'ssh_password': str,
    }
    defaults = {
        'hostname': 'localhost',
        'port': 5432,
        'database': 'postgres',
        'username': 'postgres',
        'password': '',
    }


class APRSfiCredentials(ConfigurationYAML, ConfigurationSection):
    name = 'aprs_fi'
    fields = {
        'api_key': str,
    }


class CredentialsYAML(ConfigurationYAML):
    fields = {
        'aprs_fi': APRSfiCredentials,
        'database': DatabaseCredentials,
    }

    def __init__(self, **configuration):
        for section in [APRSfiCredentials, DatabaseCredentials]:
            if section.name in configuration:
                configuration[section.name] = section(**configuration[section.name])
        super().__init__(**configuration)
