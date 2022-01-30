#!/usr/bin/env python3

import configparser
import csv
import datetime as dt
import os
import shutil
import traceback
import pandas as pd
from pathlib import Path
from xml.etree import ElementTree as ET
from new_content.process_new_content_folder import ProcessNewContentFolder as pncf
from utilities.run_log_command import run_shell_command, OvernightLogger

from external_sites.manage_google_drive import ManageGoogleDrive
from manage_users.create_resident_list import CreateResidentList


# RClone config file in /home/don/.config/rclone/rclone.conf

def driver():
    try:
        # Use environment variable to determine user for accessing config file
        # machine dependencies.  When running in PyCharm, define in run configuration.
        # Values = 'don', 'sam', (add others as needed)
        sst_user = os.environ['USER']
    except:
        raise SystemError("No TargetHost Environment Variable specified")
    # This script is intended to run daily, so there is a notion of 'testing' which is applicable
    # during development or other non-automated execution.  Automated execution requires creating
    # a Linux timer driven script.
    do_testing = True
    # Assume that any run between 1am and 4am is for production
    start_notest = dt.time(1, 0)  # but not if between 1am and 4am
    end_notest = dt.time(4, 0)
    if start_notest < dt.datetime.now().time() < end_notest:
        do_testing = False

    if do_testing:
        prototyping = False
        process_images = False  # Generate web pages to be uploaded to server                #     Use of 'local_' is as a sub-command under process_images
        load_content_files = False
        build_user_list = True
        # drive_content_dir = "SSTManagement/NewContent"
        drive_content_dir = "SSTmanagement/NewContentTest"
    else:
        prototyping = False
        process_images = False
        load_content_files = False
        build_user_list = True
        drive_content_dir = "SSTManagement/NewContent"

    config = configparser.ConfigParser()

    with open("./config_file.cfg") as source:
        config.read(source.name)
    # Load parameters from configuration file

    # dbname = config['database']['dbName']
    # dbuser = config['database']['dbUser']

    work_directory = config[sst_user]['workingDirectory']
    os.curdir = work_directory  # Set current working directory
    logs_directory = config[sst_user]['logsDirectory']
    temp_directory = config[sst_user]['tempDirectory']
    docx_directory = config[sst_user]['docxDirectory']
    image_directory = config[sst_user]['imageDirectory']
    gallery_directory = config[sst_user]['galleryDirectory']
    sst_directory = config[sst_user]['SSTDirectory']

    # Linix commands needed to access Google Drive
    # cmd_rclone = 'rclone -v copyto {} sst_store:/RClone/{}'
    # cmd_save_sst_files = "rclone -v copyto {} 'sst_store:/Sunnyside Times/SST Admin/{}'"
    # cmd_get_sst_files = "rclone -v copy 'sst_store:/Sunnyside Times/SST Admin/{}' {}"
    cmd_list_directory = 'rclone ls "sst_store:/{}"'

    summary_logger = OvernightLogger('summary_log', logs_directory)  # Logger - see use below
    if do_testing:
        summary_logger.make_info_entry('Start Testing Run')
    else:
        summary_logger.make_info_entry('Start Nightly Run')

    if load_content_files:
        # Copy source files from google drive (SSTmanagement/NewContent) to
        # a temporary directory.
        # - Move the docx files to sst_static/support/docx_pages
        # - Build meta files
        # - Move singlepic files to images directory
        # - Move gallery sub-directory to gallery directory and create yml file
        try:  # Trap error in this function so others don't get aborted
            # First set up a logger for this capability
            sst_logger = OvernightLogger('load_content_files', logs_directory)
            sst_logger.make_info_entry('Start Docx Loading')

            manage_drive = ManageGoogleDrive()

            temps = temp_directory + 'docx_temp/'
            if os.path.exists(temps):  # Anything from prior runs is gone
                shutil.rmtree(temps)
            os.mkdir(temps)

            try:
                # pull everything from Google Drive to local temp directory
                manage_drive.download_directory(sst_logger, drive_content_dir, temps)
                for story_dir in os.listdir(temps):
                    dirpath = temps + story_dir
                    content = os.listdir(dirpath)
                    dirnames = []
                    filenames = []
                    for x in content:
                        if os.path.isdir(dirpath + '/' + x):
                            dirnames.append(x)
                        else:
                            filenames.append(x)

                    process_folder = pncf(dirpath, dirnames, filenames, temp_directory, docx_directory,
                                          sst_directory, image_directory, gallery_directory)
                    result = process_folder.process_content()
            except Exception as e:
                print(e)
                traceback.print_exc()

            # Log completion
            sst_logger.make_info_entry('Complete Docx Loading')
            sst_logger.close_logger()
            summary_logger.make_info_entry('load_content_files completed normally')
        except Exception as e:
            summary_logger.make_error_entry('load_content_files failed with exception: {}'.format(e.args))

    if build_user_list:
        # Copy xslx (or other source) files from google drive (SSTmanagement/UserData) to
        # a temporary directory.  Parse and convert the files to build user login asset
        try:  # Trap error in this function so others don't get aborted
            # First set up a logger for this capability
            sst_logger = OvernightLogger('build_user_list', logs_directory)
            sst_logger.make_info_entry('Start User Login Creation')

            resident_phone_list = "Sunnyside Resident Phone Directory. 01-2022.xls"
            google_drive_dir = "SSTmanagement/UserData/"
            temps = temp_directory + 'user_list_temp/'
            if os.path.exists(temps):  # Anything from prior runs is gone
                shutil.rmtree(temps)
            os.mkdir(temps)

            res_list_processor = CreateResidentList(sst_logger, temps, google_drive_dir)
            resident_list = res_list_processor.process_resident_directory(resident_phone_list)


            # Log completion
            sst_logger.make_info_entry('Complete User Login Creation')
            sst_logger.close_logger()
            summary_logger.make_info_entry('build_user_list completed normally')
        except Exception as e:
            summary_logger.make_error_entry('build_user_list failed with exception: {}'.format(e.args))

    if process_images:
        # THIS MAY NOT BE NEEDED AS IMAGES ARE HANDLED WHEN LOADING OTHER CONTENT FILES
        target_directory = work_directory + 'auto_update'  # auto_update is temporary working dir - emptied at use
        try:
            process_images_log = OvernightLogger('process_images', logs_directory)
            process_images_log.make_info_entry('Start Image Importing')


        except Exception as e:
            summary_logger.make_error_entry('process_images failed: {}'.format(e.args))
            process_images_log.make_error_entry('process_images failed: {}'.format(e.args))

        process_images_log.make_info_entry('Complete Image Importing')
        process_images_log.close_logger()

    if prototyping:
        logger = OvernightLogger('prototyping', logs_directory)
        db_name = 'sst'
        drive_dir_to_download = config['drive paths']['driveAdmin'] + config['drive paths']['driveMinutes']
        target_directory = work_directory + 'worktemp/'
        try:
            outfile = work_directory + "tmp.txt"
            cmd = cmd_list_directory.format('Sunnyside Times')
            run_shell_command(cmd, logger, outfile=outfile)

        except Exception as e:
            print(e)
            traceback.print_exc()

        logger.close_logger()

    summary_logger.make_info_entry('Nightly Run Completed')
    summary_logger.close_logger()


if __name__ == '__main__':
    driver()
