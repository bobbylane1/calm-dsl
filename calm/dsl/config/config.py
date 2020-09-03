import os
import configparser
from jinja2 import Environment, PackageLoader

from .schema import validate_config, validate_init_config
from calm.dsl.tools import make_file_dir
from calm.dsl.log import get_logging_handle

LOG = get_logging_handle(__name__)


class InitConfig:

    _INIT_FILE_LOCATION = os.path.join(os.path.expanduser("~"), ".calm", "init.ini")

    @classmethod
    def get_init_data(cls):

        init_file = cls._INIT_FILE_LOCATION
        if not os.path.exists(init_file):
            raise FileNotFoundError(
                "'{}' not found. Please run: calm init dsl".format(init_file)
            )

        init_config = configparser.ConfigParser()
        init_config.optionxform = str
        init_config.read(init_file)

        # Validate init config
        if not validate_init_config(init_config):
            raise ValueError(
                "Invalid init config file: {}. Please run: calm init dsl".format(
                    init_file
                )
            )

        return init_config

    @classmethod
    def update_init_config(cls, config_file, db_file, local_dir):
        """updates the init file data"""

        # create required directories
        make_file_dir(config_file)
        make_file_dir(db_file)
        make_file_dir(local_dir, is_dir=True)

        # Note: No need to validate init data as it is rendered by template
        init_file = cls._INIT_FILE_LOCATION
        make_file_dir(init_file)

        LOG.debug("Rendering init template")
        text = cls._render_init_template(config_file, db_file, local_dir)

        # Write init configuration
        LOG.debug("Writing configuration to '{}'".format(init_file))
        with open(init_file, "w") as fd:
            fd.write(text)

    @staticmethod
    def _render_init_template(
        config_file, db_file, local_dir, schema_file="init.ini.jinja2"
    ):
        """renders the init template"""

        loader = PackageLoader(__name__, "")
        env = Environment(loader=loader)
        template = env.get_template(schema_file)
        text = template.render(
            config_file=config_file, db_file=db_file, local_dir=local_dir
        )
        return text.strip() + os.linesep


class ConfigFileParser:
    def __init__(self, config_file):

        config = configparser.ConfigParser()
        config.optionxform = str  # Maintaining case sensitivity for field names
        config.read(config_file)

        validate_config(config)

        config_obj = {}
        for section in config.sections():
            config_obj[section] = {}
            for k, v in config.items(section):
                config_obj[section][k] = v

        self._CONFIG = config_obj

    def get_server_config(self):
        """returns server config"""

        if "SERVER" in self._CONFIG:
            return self._CONFIG["SERVER"]

        else:
            return {}

    def get_project_config(self):
        """returns project config"""

        if "PROJECT" in self._CONFIG:
            return self._CONFIG["PROJECT"]

        else:
            return {}

    def get_log_config(self):
        """returns log config"""

        if "LOG" in self._CONFIG:
            return self._CONFIG["LOG"]

        else:
            return {}

    def get_categories_config(self):
        """returns categories config"""

        if "CATEGORIES" in self._CONFIG:
            return self._CONFIG["CATEGORIES"]

        else:
            return {}


class ConfigHandle:
    def __init__(self, config_file=None):

        if not config_file:
            init_obj = InitConfig.get_init_data()
            config_file = init_obj["CONFIG"]["location"]

        config_obj = ConfigFileParser(config_file)

        self.server_config = config_obj.get_server_config()
        self.project_config = config_obj.get_project_config()
        self.log_config = config_obj.get_log_config()
        self.categories_config = config_obj.get_categories_config()

    def get_server_config(self):
        """returns server configuration"""

        return self.server_config

    def get_project_config(self):
        """returns project configuration"""

        return self.project_config

    def get_log_config(self):
        """returns logging configuration"""

        return self.log_config

    def get_categories_config(self):
        """returns config categories"""

        return self.categories_config

    @classmethod
    def get_init_config(cls):

        return InitConfig.get_init_data()

    @classmethod
    def _render_config_template(
        cls,
        ip,
        port,
        username,
        password,
        project_name,
        log_level,
        schema_file="config.ini.jinja2",
    ):
        """renders the config template"""

        loader = PackageLoader(__name__, "")
        env = Environment(loader=loader)
        template = env.get_template(schema_file)
        text = template.render(
            ip=ip,
            port=port,
            username=username,
            password=password,
            project_name=project_name,
            log_level=log_level,
        )
        return text.strip() + os.linesep

    @classmethod
    def update_config_file(
        cls, config_file, host, port, username, password, project_name, log_level
    ):
        """Updates the config file data"""

        LOG.debug("Rendering configuration template")
        make_file_dir(config_file)
        text = cls._render_config_template(
            host, port, username, password, project_name, log_level
        )

        LOG.debug("Writing configuration to '{}'".format(config_file))
        with open(config_file, "w") as fd:
            fd.write(text)


_CONFIG_HANDLE = None


def get_config_handle(config_file=None):
    """If global data not exists or config_file is given, it will create ConfigHandle object"""

    global _CONFIG_HANDLE
    if not _CONFIG_HANDLE or config_file:
        _CONFIG_HANDLE = ConfigHandle(config_file)

    return _CONFIG_HANDLE


def set_dsl_config(
    host,
    port,
    username,
    password,
    project_name,
    log_level,
    db_location,
    local_dir,
    config_file,
):

    """
    overrides the existing server/dsl configuration
    Note: This helper assumes that valid configuration is present. It is invoked just to update the existing configuration.

    if config_file is given, it will update config file location in `init.ini` and update the server details in that file

    Note: Context will not be changed according to it.
    """

    InitConfig.update_init_config(
        config_file=config_file, db_file=db_location, local_dir=local_dir
    )

    ConfigHandle.update_config_file(
        config_file=config_file,
        host=host,
        port=port,
        username=username,
        password=password,
        project_name=project_name,
        log_level=log_level,
    )
