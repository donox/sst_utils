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
    def __init__(self, config_files):
        # config_files is a list of filenames relative to the current working directory
        self.config_files = config_files
        self.config = configparser.ConfigParser()
        for file in self.config_files:
            with open("./config_file.cfg") as source:
                self.config.read(source.name)

    def get_configuration_parameter(self, parm):
        res = None
        try:
            res = self.config[sst_user][parm]
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
        # email_username = private.username
        # email_password = private.password

