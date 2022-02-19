import config_private as private
import configparser
import os

try:
    # Use environment variable to determine user for accessing config file
    # machine dependencies.  When running in PyCharm, define in run configuration.
    # Values = 'don', 'sam', (add others as needed)
    sst_user = os.environ['USER']
except Exception as e:
    raise SystemError(f"No TargetHost Environment Variable specified: {e.args}")


class ConfigurationManager(object):
    def __init__(self):
        # config_files is a list of filenames relative to the current working directory
        self.config_file = "./config_file.cfg"
        self.config = configparser.ConfigParser()
        with open(self.config_file) as source:
            self.config.read(source.name)
        # Add values from private configuration to global config
        self.config['private'] = {}
        private_config = self.config['private']
        private_config['username'] = private.username
        private_config['password'] = private.password


    def get_configuration_parameter(self, parm, group=sst_user):
        res = None
        try:
            res = self.config[group][parm]
        except KeyError:
            return res
        return res

        # work_directory = config[sst_user]['workingDirectory']
        # os.curdir = work_directory  # Set current working directory
        # logs_directory = config[sst_user]['logsDirectory']
        # temp_directory = config[sst_user]['tempDirectory']
        # docx_directory = config[sst_user]['docxDirectory']
        # image_directory = config[sst_user]['imageDirectory']
        # gallery_directory = config[sst_user]['galleryDirectory']
        # sst_directory = config[sst_user]['SSTDirectory']
        # sst_support_directory = config[sst_user]['supportDirectory']
        # smtp_server = config['email']['smtpServer']
        # smtp_port = config['email']['smtpPort']
        # email_username = config['private']['username']
        # email_password = config['private']['password']

