#!/usr/bin/env python3

import configparser
import csv
import datetime as dt
import os
import shutil
import traceback
from pathlib import Path
from xml.etree import ElementTree as ET

from utilities.run_log_command import run_shell_command, OvernightLogger

from external_sites.manage_google_drive import ManageGoogleDrive

from practice.practice_one import DoNothingWell


# RClone config file in /home/don/.config/rclone/rclone.conf

def driver():
    try:
        # Use environment variable to determine user for accessing config file
        # machine dependencies
        # Values = 'don', 'sam', (add others as needed)
        sst_user = os.environ['USER']
    except:
        raise SystemError("No TargetHost Environment Variable specified")
    # This script runs daily
    do_testing = True

    start_notest = dt.time(1, 0)     # but not if between 1am and 4am
    end_notest = dt.time(4, 0)
    if start_notest < dt.datetime.now().time() < end_notest:
        do_testing = False

    if do_testing:
        prototyping = False
        process_images = False           # Generate web pages to be uploaded to server                #     Use of 'local_' is as a sub-command under process_images
        load_docx_files = True
        build_user_list = False
    else:
        prototyping = False
        process_images = True
        load_docx_files = True
        build_user_list = False

    pth = os.path.abspath(os.curdir)            # Find current directory (where we are running)

    config = configparser.ConfigParser()

    with open("./config_file.cfg") as source:
        config.read(source.name)
    # Load parameters from configuration file

    dbname = config['database']['dbName']
    dbuser = config['database']['dbUser']

    os.curdir = config[sst_user]['workingDirectory']         # Set current working directory
    work_directory = config[sst_user]['workingDirectory']
    logs_directory = config[sst_user]['logsDirectory']
    temp_directory = config[sst_user]['tempDirectory']
    docx_directory = config[sst_user]['docxDirectory']

    # Linix commands to access Google Drive
    cmd_rclone = 'rclone -v copyto {} sst_store:/RClone/{}'
    cmd_save_sst_files = "rclone -v copyto {} 'sst_store:/Sunnyside Times/SST Admin/{}'"
    cmd_get_sst_files = "rclone -v copy 'sst_store:/Sunnyside Times/SST Admin/{}' {}"
    cmd_list_directory = 'rclone ls "sst_store:/{}"'

    summary_logger = OvernightLogger('summary_log', logs_directory)     # Logger - see use below
    summary_logger.make_info_entry('Start Nightly Run')

    if load_docx_files:
        # Copy docx (or other source) files from google drive (SSTmanagement/NewContent) to
        # a temporary directory.  Move the docx files to sst_static/support/docx_pages

        try:                                            # Trap error in this function so others don't get aborted
            # First set up a logger for this capability
            sst_logger = OvernightLogger('load_docx_files', logs_directory)
            sst_logger.make_info_entry('Start Docx Loading')

            manage_drive = ManageGoogleDrive()

            temps = temp_directory + 'docx_temp/'
            if os.path.exists(temps):       # Anything from prior runs is gone
                shutil.rmtree(temps)
            os.mkdir(temps)

            try:
                manage_drive.download_directory(sst_logger, 'SSTmanagement/NewContent', temps)
                for _, _, files in os.walk(temps):
                    for file in files:
                        if not file.endswith('docx'):
                            raise ValueError(f"Unexpected file type in source directory: {file[-4:]}")
                        source = temps + file
                        target = docx_directory + file
                        if os.path.exists(target):
                            os.remove(target)
                        shutil.copy(source, target)
            except Exception as e:
                print(e)
                traceback.print_exc()

            # Log completion
            sst_logger.make_info_entry('Complete Docx Loading')
            sst_logger.close_logger()
            summary_logger.make_info_entry('load_docx_files completed normally')
        except Exception as e:
            summary_logger.make_error_entry('load_docx_files failed with exception: {}'.format(e.args))



    if process_images:
        target_directory = work_directory + 'auto_update'  # auto_update is temporary working dir - emptied at use
        try:
            process_images_log = OvernightLogger('process_images', logs_directory)
            process_images_log.make_info_entry('Start Image Importing')

            mg_google = ManageGoogleDrive()

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



