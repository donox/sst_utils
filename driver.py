#!/usr/bin/env python3

import configparser
import csv
import datetime as dt
import os
import re
import shutil
import traceback
import yaml as YAML
import pathlib as pl
from xml.etree import ElementTree as ET
from utilities.run_log_command import run_shell_command, OvernightLogger

from system_control.manage_google_drive import ManageGoogleDrive
from manage_users.create_resident_list import CreateUserList
import config_private as pvt
import tempfile as tf
from system_control import system_manager as sm
import yaml
from new_content import validate_shortcodes as vs
import system_control.manage_google_drive as mgd


# RClone config file in /home/don/.config/rclone/rclone.conf

def driver():
    try:
        # Use environment variable to determine user for accessing config file
        # machine dependencies.  When running in PyCharm, define in run configuration.
        # Values = 'don', 'sam', (add others as needed)
        sst_user = os.environ['USER']
    except:
        raise SystemError("No USER Environment Variable specified")

    config = configparser.ConfigParser()

    # Load parameters from configuration file
    with open("./config_file.cfg") as source:
        config.read(source.name)
    work_directory = config[sst_user]['workingDirectory']
    os.curdir = work_directory  # Set current working directory
    logs_directory = config[sst_user]['logsDirectory']
    temp_directory = config[sst_user]['tempDirectory']
    docx_directory = config[sst_user]['docxDirectory']
    image_directory = config[sst_user]['imageDirectory']
    gallery_directory = config[sst_user]['galleryDirectory']
    sst_directory = config[sst_user]['SSTDirectory']
    sst_support_directory = config[sst_user]['supportDirectory']

    summary_logger = OvernightLogger('sst_utils_log', logs_directory)  # Logger - see use below
    summary_logger.make_info_entry(f"Begin sst_utils run ")

    if pvt.sst_management:
        summary_logger.make_info_entry(f"Begin command processing")
        # commands.txt user prefix set with: os.environ["USER_PREFIX"] of the form "username_"
        # where username must exist in config_users.yaml
        sys_mgr = sm.SystemManager()
        sys_mgr.run_command_processor()
        summary_logger.make_info_entry(f"Complete command processing")

    if pvt.build_user_list or pvt.build_staff_list or pvt.build_horizon_list:
        summary_logger.make_info_entry(f"Begin login list processing")
        # Copy Sunnyside Resident Phone Directory from google drive (SSTmanagement/UserData) to
        # a temporary directory.  Parse and convert the file to build user login csv file for residents
        try:
            sst_logger = OvernightLogger('build_user_list', logs_directory)
            sst_logger.make_info_entry('Start User Login Creation')

            resident_phone_list = "Sunnyside Resident Phone Directory. 01-2022.xls"
            staff_phone_list = "Sunnyside Staff Directory. 01-2022.xls"
            horizon_club_list = "Horizon_club.xls"
            google_drive_dir = "SSTmanagement/UserData/"
            temps = temp_directory + 'user_list_temp/'
            if os.path.exists(temps):  # Anything from prior runs is gone
                shutil.rmtree(temps)
            os.mkdir(temps)

            res_list_processor = CreateUserList(sst_logger, temps, google_drive_dir)
            if pvt.build_user_list:
                res_list_processor.process_resident_directory(resident_phone_list)
            if pvt.build_staff_list:
                res_list_processor.process_staff_directory(staff_phone_list)
            if pvt.build_horizon_list:
                res_list_processor.process_horizon_directory(horizon_club_list)

            # Log completion
            sst_logger.make_info_entry('Complete User Login Creation')
            sst_logger.close_logger()
            summary_logger.make_info_entry('build_user_list completed normally')
        except Exception as e:
            summary_logger.make_error_entry('build_user_list failed with exception: {}'.format(e.args))

    if pvt.create_combined_login:
        # Copy current login lists from Google Drive, combine them and move to sst/support/users.csv
        try:
            summary_logger.make_info_entry(f"Begin create combined login")

            resident_phone_list = "Sunnyside Resident Phone Directory. 01-2022.xls"
            staff_phone_list = "Sunnyside Staff Directory. 01-2022.xls"
            # TODO: move directory to config file, check if this is right way to handle temps
            google_drive_dir = "SSTmanagement/UserData/"
            temps = temp_directory + 'user_list_temp/'
            if os.path.exists(temps):  # Anything from prior runs is gone
                shutil.rmtree(temps)
            os.mkdir(temps)

            files = ['residents.csv', 'staff.csv', 'horizon.csv']
            outfile = 'users.csv'
            res_list_processor = CreateUserList(summary_logger, temps, google_drive_dir)
            res_list_processor.get_all_users(files, outfile)

            shutil.copy(temps + 'users.csv', sst_support_directory + 'users.csv')

            # Log completion
            summary_logger.make_info_entry('Complete Creation of sst/support/users.csv')
        except Exception as e:
            summary_logger.make_error_entry('build_users_csv failed with exception: {}'.format(e.args))

    if pvt.prototyping:
        """Download and unzip a backup file."""
        summary_logger.make_info_entry(f"Begin prototyping run")
        target_directory = temp_directory + 'worktemp/'
        manage_drive = mgd.ManageGoogleDrive()
        source_dir = "SSTmanagement/Backups/"
        file_to_download = "galleries-mar-27-2022.zip"

        manage_drive.download_file(summary_logger, source_dir, file_to_download, target_directory)
        foo = 3

    if False and pvt.prototyping:
        """Modify meta_paths in directory containing possibly recursive structure of files. """
        drive_dir_to_download = config['drive paths']['driveAdmin'] + config['drive paths']['driveMinutes']
        target_directory = work_directory + 'worktemp/'
        test_dir = temp_directory + 'fix_meta_paths/'
        path_element_to_find = 'pages/aa-activities-index'
        path_element_to_replace = 'pages'
        try:
            for root, dirs, files in os.walk(test_dir):
                print(f"{root}")
                # for dir in dirs:
                #     print(f"    DIR:  {dir}")
                # for file in files:
                #     print(f"    FILE: {file}")
                if 'meta.txt' in files:
                    meta_path = os.path.join(root, 'meta.txt')
                    changed = False
                    try:
                        with open(meta_path) as stream:
                            story_meta_tmp = yaml.safe_load(stream.read().replace('\t', ' '))
                            if not story_meta_tmp:
                                print(f"meta.txt is empty")
                            else:
                                path = story_meta_tmp['.. path']
                                print(f"{path}")
                                if path_element_to_find in path:
                                    path_new = path.replace(path_element_to_find, path_element_to_replace)
                                    print(f"\nOLD: {path}")
                                    print(f"NEW: {path_new}")
                                    story_meta_tmp['.. path'] = path_new
                                    changed = True
                            stream.close()
                        if changed:
                            with open(meta_path, 'w') as stream:
                                yaml.safe_dump(story_meta_tmp, stream)
                                stream.close()
                            foo =- 3
                    except Exception as e:
                        foo = 4

        except Exception as e:
            print(e)
            traceback.print_exc()

    summary_logger.make_info_entry('sst_utils Run Completed')
    summary_logger.close_logger()


if __name__ == '__main__':
    driver()
