import sys
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
                if paired_file:
                    shutil.copy(self.local_temp.name + '/' + file, real_target + metafile)
                    shutil.copy(self.local_temp.name + '/' + file, real_target + paired_file)

    def _copy_meta_file(self, story_meta, out_dir=None):
        if not out_dir:
            out_dir = pl.Path(self.docx_directory)
        # Copy meta file with proper renaming
        source = pl.Path(self.story_directory.name) / 'meta.txt'
        target = out_dir / (story_meta['slug'] + ".meta")
        if os.path.exists(target):
            os.remove(target)
        shutil.copy(source, target)



def create_empty_dirpath(path):
    """Create an empty directory and make any intermediate directories."""
    if os.path.exists(path):
        if not os.path.isdir(path):
            raise ValueError(f"Specified path, {path}, is not a directory in call to create_empty_dirpath.")
        shutil.rmtree(path)
        os.mkdir(path)
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)
