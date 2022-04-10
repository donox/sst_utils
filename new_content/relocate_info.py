#!/usr/bin/env python3
import os
import shutil
import yaml
from system_control.manage_google_drive import ManageGoogleDrive as mgd
import tempfile as tf
import pathlib as pl
from mako.template import Template
from new_content import validate_shortcodes as vs
from mako.lookup import TemplateLookup
from mako.runtime import Context
from config_private import test_run




class RelocateInformation(object):
    """Copy, move, delete files and directories."""
    def __init__(self, logger, folder_path, config):
        self.logger = logger
        self.drive = mgd()
        self.folder_path = mgd.add_slash(folder_path)
        self.config = config
        self.sst_directory = config.get_configuration_parameter('SSTDirectory')
        self.image_directory = config.get_configuration_parameter('imageDirectory')
        self.gallery_directory = config.get_configuration_parameter('galleryDirectory')
        self.pages_directory = pl.Path(self.sst_directory) / 'pages/'
        self.temp_dir = config.get_configuration_parameter('tempDirectory')
        # Note: local_temp is reused - it must be emptied before loading a new command file (get_commands)
        self.local_temp = tf.TemporaryDirectory(dir=self.temp_dir, prefix='xfr')


    def move_folder_of_pagefiles(self, target_dir):
        """Copy all files that have a corresponding meta file."""
        self.drive.download_directory(self.logger, self.folder_path, self.local_temp.name)
        all_files = os.listdir(self.local_temp.name)
        metafiles = [x for x in all_files if x.endswith('meta')]
        nonmetafiles = [x for x in all_files if not x.endswith('meta')]
        real_target = (self.sst_directory + target_dir).replace('//', '/')
        for metafile in metafiles:
                file_base = metafile[:-4]
                paired_file = None
                for file in nonmetafiles:
                    if file.startswith(file_base):
                        paired_file = file
                        break
                try:
                    if not test_run and paired_file:
                        shutil.copy(self.local_temp.name + '/' + file, real_target + metafile)
                        shutil.copy(self.local_temp.name + '/' + file, real_target + paired_file)
                except NameError:
                    pass
    def process_page_file_actions(self, file_to_process):
        """Read YAML file and drive processing of specified actions."""
        self.drive.download_file(self.logger, self.folder_path, file_to_process, self.local_temp.name)
        with open(self.local_temp.name + '/' + file_to_process) as stream:
            try:
                # Note: yaml is small and we convert to list so it can be reused
                actions = [x for x in yaml.safe_load_all(stream)]
            except yaml.YAMLError as exc:
                self.logger.make_error_entry(f"YAML error encountered in {file_to_process} with error {exc.args}")
                raise exc
            for action in actions:
                try:
                    if action:
                        todo = action['function']
                        if todo in ['delete', 'add_to_this_list']:
                            if todo == 'delete':
                                urls = action['urls']
                                for url in urls:
                                    self.remove_page_from_website(url)
                        else:
                            self.logger.make_error_entry(f"Function {todo} not available in pages potential actions.")
                except KeyError as e:
                    self.logger.make_error_entry(f"Invalid key error processing actions: {e.args}")

    def remove_page_from_website(self, url):
        """Remove a page from the site."""
        file_path = url.split("/pages/")
        if len(file_path) == 2:
            file_path = file_path[1]
        else:
            file_path = file_path[0]
        file_path = file_path.split('/')
        if not file_path[-1]:
            file_path = file_path[:-1]
        file_name = file_path[-1]   # pick off filename
        system_file_path = self.sst_directory + 'pages/'
        for step in file_path[:-1]:
            if step in os.listdir(system_file_path):
                system_file_path += step + '/'
            else:
                self.logger.make_error_entry(f"Directory: {step} not found in path: {system_file_path}")
                return
        if file_name.endswith('.md'):
            file_name = file_name[:-3]
        if file_name.endswith('.meta'):
            file_name = file_name[:-5]
        file_base = system_file_path + file_name
        found = False
        if os.path.exists(file_base + '.md'):
            if not test_run:
                os.remove(file_base + '.md')
            found = True
        if os.path.exists(file_base + '.meta'):
            if not test_run:
                os.remove(file_base + '.meta')
        if found:
            self.logger.make_info_entry(f"Page {url} removed.")
        else:
            self.logger.make_error_entry(f"Page {url} not found.")

    def _copy_meta_file(self, story_meta, out_dir=None):
        if not out_dir:
            out_dir = pl.Path(self.docx_directory)
        # Copy meta file with proper renaming
        source = pl.Path(self.story_directory.name) / 'meta.txt'
        target = out_dir / (story_meta['slug'] + ".meta")
        try:
            if not test_run:
                if os.path.exists(target):
                    os.remove(target)
                shutil.copy(source, target)
        except NameError:
            pass



def create_empty_dirpath(path):
    """Create an empty directory and make any intermediate directories."""
    try:
        if not test_run:
            if os.path.exists(path):
                if not os.path.isdir(path):
                    raise ValueError(f"Specified path, {path}, is not a directory in call to create_empty_dirpath.")
                shutil.rmtree(path)
                os.mkdir(path)
            else:
                os.makedirs(os.path.dirname(path), exist_ok=True)
    except NameError:
        pass
