import os

from system_control import command_processor as cmd_proc
from system_control import config_control as conf
from utilities.run_log_command import OvernightLogger
from utilities.send_email import ManageEmail
import config_private as pvt


class SystemManager(object):
    """Top level controller for managing content on website."""

    def __init__(self):
        try:
            # Use environment variable to determine user for accessing config file
            # machine dependencies.  When running in PyCharm, define in run configuration.
            # Values = 'don', 'sam', (add others as needed)
            sst_user = os.environ['USER']
        except:
            raise SystemError("No User Environment Variable specified")

        try:
            self.commands_prefix = os.environ["USER_PREFIX"]
        except:
            self.commands_prefix = ""

        self.config = conf.ConfigurationManager()
        self.logs_directory = self.config.get_configuration_parameter('logsDirectory')
        self.temp_dir = self.config.get_configuration_parameter('tempDirectory')
        self.logger = OvernightLogger('SSTcontent', self.logs_directory)
        self.system_users = cmd_proc.SystemUser(self.temp_dir, self.logger, self.config)
        self.smtp_server = self.config.get_configuration_parameter('smtpServer', group='email')
        self.smtp_port = self.config.get_configuration_parameter('smtpPort', group='email')

    def run_command_processor(self):
        dirs = cmd_proc.ManageFolders(self.config, self.logger, self.system_users, self.commands_prefix)
        dirs.process_commands_top()
        users_wanting_logs = dirs.get_log_requests()
        try:
            if pvt.email_logs:
                if users_wanting_logs:
                    self._email_logs(users_wanting_logs)
        except NameError:
            pass

    def _email_logs(self, users):
        system_users_wanting_logs = []
        names = []
        for user in self.system_users.user_data:
            if self.system_users.user_data[user]['mailLogs']:
                system_users_wanting_logs.append(user)
                names.append(user)
        mgr = ManageEmail(pvt.username, pvt.password, self.smtp_server, self.smtp_port)
        for user in users:
            if user in names:
                mgr.add_recipient(self.system_users.user_data[user]['emailAddress'])
        mgr.set_subject("Log result of running test")
        mgr.add_attachment(self.logs_directory + 'SSTcontent.log')
        mgr.set_body("THis is the body")
        mgr.send_email()
