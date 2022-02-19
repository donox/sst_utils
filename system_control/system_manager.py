import sys
import os
import shutil
import traceback
import yaml as YAML
from system_control import manage_google_drive as MGD
from system_control import config_control as conf
import tempfile as tf
import pathlib as pl
from new_content.process_story_content import ProcessStoryContent as psc
import system_control.config_control as cc
from utilities.run_log_command import run_shell_command, OvernightLogger
from system_control import command_processor as cmd_proc
import tempfile as tf
from utilities.send_email import ManageEmail


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
        self.logger = OvernightLogger('SSTcontent', self.logs_directory)

    def run_command_processor(self):
        dirs = cmd_proc.ManageFolders(self.config, self.logger)
        dirs.process_commands_top()

