import pathlib as pl
import tempfile as tf
import traceback

import yaml as YAML

from new_content.process_story_content import ProcessStoryContent as PSC
from system_control import manage_google_drive as mgd


class SystemUser(object):
    """Provide support for permitted users of the system."""

    def __init__(self, temp_dir, logger, config):
        self.temp_dir = temp_dir
        self.config = config
        self.logger = logger
        self.user_data = self._load_config_users()  # dictionary (key=name) with name, emailAddress, mailLogs, isAdmin
        self.users = list(self.user_data.keys())  # list of names of users

    def _load_config_users(self):
        manage_drive = mgd.ManageGoogleDrive()

        temps = tf.TemporaryDirectory(prefix='user', dir=self.temp_dir)

        # First, pick up configuration yaml file
        user_config = 'config_users.yaml'
        try:
            top_level = self.config.get_configuration_parameter("driveSSTManagement", group="drive paths")
            manage_drive.download_file(self.logger, top_level, user_config, temps.name)
            with open(pl.Path(temps.name) / user_config, 'r', encoding='utf-8') as fd:
                res = YAML.safe_load_all(fd)
                docs = [doc for doc in res]
                fd.close()
            user_data = dict()
            for doc in docs:
                if doc:
                    user = doc['name']
                    user_data[user] = doc
            return user_data
        except Exception as e:
            print(e)
            traceback.print_exc()

    def get_users(self):
        return self.user_data

    def get_persons(self, name_string):
        """Split comma separated list of users and set default to admins."""
        names = name_string.split(',')
        res = []
        for name in names:
            if name in self.users:
                res.append(self.user_data[name])
        if not res:
            for person in self.user_data:
                if self.user_data[person]['isAdmin']:
                    res.append(person)
        return res


class ManageFolders(object):
    """Manage top level directories on SSTManagement"""

    def __init__(self, config, logger, users):
        self.config = config
        self.logger = logger
        self.temp_dir = config.get_configuration_parameter('tempDirectory')
        self.users = users
        self.manage_drive = mgd.ManageGoogleDrive()
        self.top_folder = config.get_configuration_parameter("driveSSTManagement", group="drive paths")
        self.current_folder = self.top_folder
        self.valid_command_sets = ["top", "content", "story"]
        self.valid_commands = \
            {"top": ["identity", "process_single_folder"],
             "content": ["identity", "process_single_folder", "all"],
             "story": ["identity", "story"]
             }
        self.command_definitions = \
            {("top", "identity"): self._command_identity,
             ("top", "process_single_folder"): self._command_single_folder,
             ("content", "identity"): self._command_identity,
             ("content", "process_single_folder"): self._command_single_folder,
             ("content", "all"): self._command_all,
             ("content", "process_single_folder"): self._command_single_folder,
             ("story", "identity"): self._command_identity,
             ("story", "story"): self._command_process_story,
             }
        self.context = []
        self.futures = []

    def get_folder_names(self, folder):
        """Retrieve list of the names of the contained folders from drive within a given source folder."""
        dir_list = self.manage_drive.directory_list_directories(self.logger, folder).decode('utf-8')
        dirs = []
        for line in dir_list.split('\n'):
            elements = line.split()
            if type(elements) is list and len(elements) > 0:
                dirs.append(elements[-1])
        return dirs

    def get_folder_content(self, folder):
        """Download a specified folder into a new temporary directory and return the directory. """
        pass

    def get_file_names(self, folder):
        """Retrieve list of names of contained files in specific folder from drive."""
        file_list = self.manage_drive.directory_list_files(self.logger, folder).decode('utf-8')
        files = []
        for line in file_list.split('\n'):
            elements = line.split()
            if type(elements) is list and len(elements) > 0:
                files.append(elements[-1])
        return files

    def get_commands(self, folder):
        """Load commands.txt as yaml list of documents (dictionaries)."""
        try:
            filename = "commands.txt"
            temp_dir = tf.TemporaryDirectory(dir=self.temp_dir, prefix='cmd')
            self.manage_drive.download_file(self.logger, folder, filename, temp_dir.name)
            with open(pl.Path(temp_dir.name) / filename, 'r', encoding='utf-8') as fd:
                res = YAML.safe_load_all(fd)
                docs = [doc for doc in res]
                fd.close()
                if not docs[-1]:
                    docs.pop()
            return docs
        except Exception as e:
            print(e)
            traceback.print_exc()

    def process_commands_top(self):
        context = []  # state of work already done - each element is a dictionary
        futures = []  # stack of work to be done - each element is a function (continuation)
        self.process_commands(self.top_folder, "top")

    def process_commands(self, folder, command_set):
        if command_set not in self.valid_command_sets:
            self.logger(f"Invalid command_set: {command_set} for folder: {folder}")
            raise ValueError(f"Invalid command_set: {command_set}")
        valid_commands = self.valid_commands[command_set]
        cmds = self._get_command_set(command_set, folder)
        for command in self._generate_commands(cmds, valid_commands):
            print(f"Command {command} to be executed.")  # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            if 'command' not in command:
                self.logger.make_error_entry(f"Command: {command} does not specify the 'command' name.")
                raise ValueError(f"Invalid command: {command} - missing 'command'")
            command_name = command['command']
            key = (command_set, command_name)
            if key not in self.command_definitions:
                self.logger(f"Command: {command} not valid for command_set: {command_set}")
                raise ValueError(f"Invalid command: {command} - not supported")
            cmd = self.command_definitions[key]
            cmd(command)

    def get_log_requests(self):
        """Find users in context wanting a copy of the log."""
        res = []
        for item in self.context:
            if 'person' in item:
                if 'send_log' in item:
                    if item['send_log']:
                        res.append(item['person'])
        return res

    def _context_add(self, cmd, **kwargs):
        self.context.append(cmd)  # TRYING TO ADD KWARG Users

    def _context_remove(self):
        self.context.pop()

    def _context_find(self, item):
        return item

    def _get_command_set(self, command_set, folder):
        """Retrieve command set for a folder as a list
        """
        cmds = self.get_commands(folder)
        if not cmds:
            self.logger.make_error_entry(f"There is no commands.txt file in {folder}")
            raise ValueError("Missing commands.txt")
        try:
            cmd_set = cmds[0]["command_set"].lower()
        except KeyError as e:
            self.logger.make_error_entry(f"No command_set key found in folder: {folder}")
            raise e
        if cmd_set != command_set:
            self.logger.make_error_entry(f"Invalid command set: {cmd_set}, expecting: {command_set}")
            raise ValueError(f"Invalid command set {cmd_set}")
        return cmds[1:]

    def _generate_commands(self, command_list, allowable_commands):
        """Create generator for list of allowable commands."""
        for command_dict in command_list:
            try:
                cmd = command_dict["command"].lower()
                if cmd not in allowable_commands:
                    self.logger.make_error_entry(f"Invalid  command: {cmd} not in {allowable_commands}")
                    raise ValueError(f"Invalid command: {cmd}")
                yield command_dict
            except Exception as e:
                self.logger.make_error_entry(f"Invalid command: {command_dict}")
                raise ValueError(f"Invalid command dictionary: {command_dict}")

    def _get_command_attribute(self, attribute, command, default=None):
        try:
            res = command[attribute]
            return res
        except Exception as e:
            if default:
                return default
            self.logger.make_error_entry(f"Expected {attribute} in command: {command}")
            raise e

    def _command_identity(self, command):
        """Process identity command.

        If person(s) specified - must be known to system, else default to sys admin.
        If send_log specified as True - create future to send log to specified person."""
        if "person" in command:
            persons = self.users.get_persons(command['person'])
        self._context_add(command, users=persons)

    def _command_all(self, command):
        content = self.manage_drive.directory_list_directories(self.logger, self.current_folder)
        for item in content:
            self._command_single_folder(command, folder=item, folder_type="story")

    def _command_single_folder(self, command, folder=None, folder_type=None):
        # Keyword args are to allow the 'All' command to use this code and provide otherwise missing values.
        try:
            if not folder:
                folder = self._get_command_attribute("folder", command)
            if not folder_type:
                folder_type = self._get_command_attribute("folder_type", command)
            current_folder = self.current_folder
            self.current_folder += '/' + folder
            if folder_type == "site_content":  # may contain multiple folders of website content
                self.process_commands(self.current_folder, 'content')
            elif folder_type == "story":  # content for a single story (or part of one)
                self.process_commands(self.current_folder, 'story')
            else:
                self.logger.make_error_entry(f"Unrecognized folder_type: {folder_type} for folder: {folder}")
                self.current_folder = current_folder
                raise ValueError(f"Invalid folder_type: {folder_type}")
            self.current_folder = current_folder
            pass
        except Exception as e:
            raise e
        finally:
            self.current_folder = current_folder

    def _command_process_story(self, command):
        docx_directory = self.config.get_configuration_parameter('docxDirectory')
        sst_directory = self.config.get_configuration_parameter('SSTDirectory')
        image_directory = self.config.get_configuration_parameter('imageDirectory')
        gallery_directory = self.config.get_configuration_parameter('galleryDirectory')
        process_folder = PSC(self.logger, self.current_folder, self.temp_dir,
                             docx_directory, sst_directory, image_directory, gallery_directory)
        process_folder.process_content()

    def _command_xxx(self, command):
        print(f"Command: {command} called")
        pass

    def _command_xxx(self, command):
        print(f"Command: {command} called")
        pass
