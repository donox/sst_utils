import os

from system_control import command_processor as cmd_proc
from system_control import config_control as conf
from utilities.run_log_command import OvernightLogger


class SystemManager(object):
    """Top level controller for managing content on website."""
    def __init__(self):
        try:
            # Use environment variable to determine user for accessing config file
            # machine dependencies.  When running in PyCharm, define in run configuration.
            # Values = 'don', 'sam', (add others as needed)
            sst_user = os.environ['USER']
        except:
            raise SystemError("No TargetHost Environment Variable specified")

        self.config = conf.ConfigurationManager()
        self.logs_directory = self.config.get_configuration_parameter('logsDirectory')
        self.temp_dir = self.config.get_configuration_parameter('tempDirectory')
        self.logger = OvernightLogger('SSTcontent', self.logs_directory)
        self.system_users = cmd_proc.SystemUser(self.temp_dir, self.logger, self.config)

    def run_command_processor(self):
        dirs = cmd_proc.ManageFolders(self.config, self.logger, self.system_users)
        dirs.process_commands_top()

