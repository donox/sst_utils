#!/usr/bin/env python3
import pathlib as pl
import tempfile as tf
import os
import shutil

import yaml as YAML
from yaml.scanner import ScannerError

import config_private as cp
from new_content.process_story_content import ProcessStoryContent as PSC
from new_content.relocate_info import RelocateInformation as RI
from system_control import manage_google_drive as mgd
from system_control.exceptions import SstCommandDefinitionException as CDEx


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
            self.logger.make_error_entry(f"Fail loading config_users with error: {e.args}")

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

    def __init__(self, config, logger, users, command_prefix):
        self.config = config
        self.logger = logger
        self.temp_dir = config.get_configuration_parameter('tempDirectory')
        self.sst_directory = config.get_configuration_parameter('SSTDirectory')
        self.support_directory = config.get_configuration_parameter('supportDirectory')
        # Note: local_temp is reused - it must be emptied before loading a new command file (get_commands)
        self.local_temp = tf.TemporaryDirectory(dir=self.temp_dir, prefix='cmd')
        self.users = users
        self.command_prefix = command_prefix  # Prefix to append to top level commands.txt to allow multiple users
        self.manage_drive = mgd.ManageGoogleDrive()
        self.top_folder = config.get_configuration_parameter("driveSSTManagement", group="drive paths")
        # self.current_folder is the full path to the folder being processed (leaf node, a.k.a. folder)
        # folder is used as the name of the specific folder (leaf node) being processed.
        self.current_folder = self.top_folder
        self.valid_command_sets = ["top", "content", "story", "transfer_files", "transfer_to_support", "update_pages"]
        self.valid_commands = \
            {"top": ["identity", "change_folder", "process_single_folder"],
             "content": ["identity", "process_single_folder", "all"],
             "story": ["identity", "story"],
             "transfer_files": ["identity", "move_files"],
             "transfer_to_support": ["identity", "move_files"],
             "update_pages": ["identity", "process_pages"],
             }
        self.command_subcommands = \
            {("top", "identity"): self._command_identity,
             ("top", "change_folder"): self._command_change_folder,
             ("top", "process_single_folder"): self._command_single_folder,
             ("content", "identity"): self._command_identity,
             ("content", "process_single_folder"): self._command_single_folder,
             ("content", "all"): self._command_all,
             ("content", "process_single_folder"): self._command_single_folder,
             ("story", "identity"): self._command_identity,
             ("story", "story"): self._command_process_story,
             ("transfer_files", "identity"): self._command_identity,
             ("transfer_files", "move_files"): self._command_transfer_files,
             ("transfer_to_support", "identity"): self._command_identity,
             ("transfer_to_support", "move_files"): self._command_transfer_support_files,
             ("update_pages", "process_pages"): self._command_update_pages,
             ("update_pages", "identity"): self._command_identity,
             }
        # Note:  this is a potential bug if the same subcommand exists in two different commands with different attrs
        self.subcommand_definitions = \
            {"identity": ['person', 'send_log'],
             "process_single_folder": ['folder', 'folder_type'],
             "change_folder": ['folder'],
             "move_files": ['target_directory'],
             }
        self.context = []
        self.futures = []

    def validate_command_file(self, directory, file):
        """Read and check command file for possible errors."""
        err = self.logger.make_error_entry
        filepath = pl.Path(directory) / file
        try:
            with open(filepath) as cmd_file:
                self.logger.make_info_entry(f"Validating file: {file}.")
                cmd_set = None
                curr_cmd = None
                for line_no, line in enumerate(cmd_file.readlines()):
                    line_strip = line.strip()
                    if len(line_strip) < 3:
                        break
                    if line_strip[0] == '#':
                        break
                    first_tab = line.find('\t')
                    if first_tab != -1:
                        err(f"File contains at least one tab at position {first_tab}")
                    if line.startswith("---"):
                        curr_cmd = None
                    else:
                        line_parts = line.split('#')[0].split(':')
                        el = line_parts[0]
                        if len(line_parts) < 2:
                            err(f"Command_set does not contain a specific command_set ")
                            raise CDEx(f"No command_set found")
                        el2 = line_parts[1].strip().lower()
                        if not curr_cmd:  # Validate command_set
                            if not cmd_set:
                                if el != 'command_set':
                                    err(f"'Command_set' not found in file.")
                                    raise CDEx("Missing Command Set")
                                if el2 not in self.valid_command_sets:
                                    err(f"{el2} in line {line_no}' is not a valid command_set")
                                    raise CDEx(f"Unrecognized Command Set")
                                cmd_set = el2
                            else:  # must be a command appropriate for the command_set
                                if el != 'command':
                                    err(f"{el} is not a part of command {cmd_set}")
                                    raise CDEx(f"Invalid command for this command set")
                                curr_cmd = el2
                        else:
                            if not self._check_function_in_subcommand_definitions(curr_cmd, el):
                                err(f"{el} is not valid in this command: {curr_cmd}")
                                raise CDEx(f"Invalid subcommand")
        except CDEx as e:
            cmd_file.close()
            return False
        cmd_file.close()
        return True

    def _check_function_in_subcommand_definitions(self, cmd, sub_cmd):
        if cmd not in self.subcommand_definitions.keys():
            return False
        if sub_cmd not in self.subcommand_definitions[cmd]:
            return False
        return True

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
        files = self.manage_drive.directory_list_files(self.logger, folder)
        return files

    def get_commands(self, folder):
        """Load commands.txt as yaml list of documents (dictionaries)."""
        try:
            filename = "commands.txt"
            filepath = filename
            if folder == self.top_folder:
                if self.command_prefix == 'use_config_private':         # Hack to support old still till all changed.
                    filename = cp.command_file
                    if self.current_folder.endswith('/'):
                        self.current_folder = self.current_folder + cp.command_path
                    else:
                        self.current_folder = self.current_folder + '/' + cp.command_path
                else:
                    filename = self.command_prefix + filename
            # We must clear the temp directory before downloading - this soln is more general than needed
            # but works in all cases
            for root, dirs, files in os.walk(self.local_temp.name):
                for f in files:
                    os.unlink(os.path.join(root, f))
                for d in dirs:
                    shutil.rmtree(os.path.join(root, d))
            self.manage_drive.download_file(self.logger, self.current_folder, filename, self.local_temp.name)
            if not self.validate_command_file(self.local_temp.name, filename):
                self.logger.make_error_entry(f"Invalid command file in folder: {folder}")
                raise CDEx("Invalid Command File")
            with open(pl.Path(self.local_temp.name) / filename, 'r', encoding='utf-8') as fd:
                res = YAML.safe_load_all(fd)
                docs = [doc for doc in res]
                fd.close()
                if not docs[-1]:   # Remove empty terminating line if it exists
                    docs.pop()
            return docs
        except ScannerError as e:
            self.logger.make_error_entry(f"YAML error reading commands.txt: error: {e.args}\n\tBeware of tab chars")
        except Exception as e:
            self.logger.make_error_entry(f"Error retreiving commands.txt in folder {folder} with error: {e.args}")
            raise e

    def get_command_file(self, folder):
        """Load commands.txt as list of txt lines."""
        try:
            filename = "commands.txt"
            filename = self.command_prefix + filename
            self.manage_drive.download_file(self.logger, folder, filename, self.local_temp.name)
            with open(pl.Path(self.local_temp.name) / filename, 'r', encoding='utf-8') as fd:
                res = fd.readlines()
                fd.close()
            return res
        except Exception as e:
            self.logger.make_error_entry(
                f"Error retreiving commands.txt as text in folder {folder} with error: {e.args}")
            raise e

    def process_commands_top(self):
        self.process_commands(self.top_folder)

    def process_commands(self, folder):
        """Open and initiate processing of a folder containing commands.txt"""
        cmds = self._get_command_set(folder)
        command_set = cmds[0]['command_set'].lower()
        if command_set not in self.valid_command_sets:
            self.logger(f"Invalid command set: {command_set} for folder: {folder}")
            raise CDEx(f"Invalid command set: {command_set}")
        valid_commands = self.valid_commands[command_set]
        for command in self._generate_commands(cmds[1:], valid_commands):
            print(f"Command {command}  in folder {folder} to be executed.")  # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            # 'command' has already been checked for existence in the generator
            command_name = command['command']
            key = (command_set, command_name)
            if key not in self.command_subcommands:
                self.logger.make_error_entry(f"Command: {command} not valid for command_set: {command_set} in folder: {folder}")
                raise CDEx(f"Invalid command: {command} - not supported")
            cmd = self.command_subcommands[key]
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
        self.context.append(cmd)

    def _context_remove(self):
        self.context.pop()

    def _context_find(self, item):
        return item

    def _get_command_set(self, folder):
        """Retrieve command set for a folder as a list
        """
        cmds = self.get_commands(folder)
        if not cmds:
            self.logger.make_error_entry(f"There is no commands.txt file in {folder}")
            raise CDEx("Missing commands.txt")
        try:
            _ = cmds[0]["command_set"]
        except KeyError as e:
            self.logger.make_error_entry(f"No command_set key found in folder: {folder}")
            raise e
        return cmds

    def _generate_commands(self, command_list, allowable_commands):
        """Create generator for list of allowable commands."""
        for command_dict in command_list:
            cmd = command_dict["command"].lower()
            if cmd not in allowable_commands:
                self.logger.make_error_entry(f"Invalid  command: {cmd} not in {allowable_commands}")
                raise CDEx(f"Invalid command: {cmd}")
            yield command_dict

    def _get_command_attribute(self, attribute, command, default=None):
        try:
            res = command[attribute]
            return res
        except KeyError as e:
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
        """Process all folders in containing folder."""
        content = self.manage_drive.directory_list_directories(self.logger, self.current_folder)
        for item in content:
            if item != 'ignore':
                current_folder = self.current_folder
                self.current_folder += '/' + item
                self.process_commands(item)
                self.current_folder = current_folder

    def _command_single_folder(self, command, folder=None, folder_type=None):
        # Keyword args are to allow the 'All' command to use this code and provide otherwise missing values.
        # folder represents a leaf node not yet appended to self.current_folder
        try:
            if not folder:
                folder = self._get_command_attribute("folder", command)
            if not folder_type:
                folder_type = self._get_command_attribute("folder_type", command)
            current_folder = self.current_folder
            self.current_folder += '/' + folder
            # Allow for use of either underscore or dash
            # Note: site_content implies processing a single folder in the case where
            #       there may be other folders that are to be skipped (e.g., at top level)
            if folder_type == "site_content" or folder_type == 'site-content':
                self.process_commands(folder)
            elif folder_type == "story":  # content for a single story (or part of one)
                self.process_commands(folder)
            else:
                self.logger.make_error_entry(f"Unrecognized folder_type: {folder_type} for folder: {folder}")
                self.current_folder = current_folder
                raise CDEx(f"Invalid folder_type: {folder_type}")
            self.current_folder = current_folder
        finally:
            self.current_folder = current_folder

    def _command_process_story(self, command):
        """Process 'story' content - a page that generates actual web content."""
        # A story may be either a docx file,  a template file, or an md file
        docx_directory = self.config.get_configuration_parameter('docxDirectory')
        sst_directory = self.config.get_configuration_parameter('SSTDirectory')
        image_directory = self.config.get_configuration_parameter('imageDirectory')
        gallery_directory = self.config.get_configuration_parameter('galleryDirectory')
        process_folder = PSC(self.logger, self.current_folder, self.temp_dir,
                             docx_directory, sst_directory, image_directory, gallery_directory)
        process_folder.process_content()

    def _command_transfer_files(self, command):
        """Transfer files to pages directory for processing

        Files are transferred without checking or change. This presumes they
        are suitable for nikola processing and have been updated on Drive."""
        relocator = RI(self.logger, self.current_folder, self.config)
        target_dir = self._get_command_attribute("target_directory", command)
        relocator.move_folder_of_pagefiles(target_dir)

    def _command_transfer_support_files(self, command):
        """Transfer files to Support directory for further processing

        Files are transferred without checking or change. They will be processed
        by additional Nikola commands."""
        print(f"Command: {command} called")
        target_dir = self._get_command_attribute("target_directory", command)
        self.manage_drive.download_directory(self.logger, self.current_folder, self.local_temp.name)
        all_files = os.listdir(self.local_temp.name)
        real_target = (self.support_directory + target_dir).replace('//', '/')
        if not os.path.isdir(real_target):
            os.mkdir(real_target)
        for file in all_files:
            try:
                if not cp.test_run and file != 'commands.txt':
                    shutil.copy(self.local_temp.name + '/' + file, real_target + file)
            except NameError:
                pass


    def _command_change_folder(self, command):
        """Modify top folder."""
        added_folder = self._get_command_attribute("folder", command)
        self.top_folder += '/' + added_folder
        self.current_folder = self.top_folder
        print(f"Command: {command} called - top folder now: {self.top_folder}")

    def _command_update_pages(self, command):
        """Perform file management actions in pages directory."""
        print(f"Command: {command} called")
        file_names = self.get_file_names(self.current_folder)
        relocator = RI(self.logger, self.current_folder, self.config)
        for file in file_names:
            if file != 'meta.txt' and file != 'commands.txt':
                relocator.process_page_file_actions(file)
        pass

    def _command_xxx(self, command):
        print(f"Command: {command} called")
        pass

    def _command_xxx(self, command):
        print(f"Command: {command} called")
        pass

    def _command_xxx(self, command):
        print(f"Command: {command} called")
        pass
