#!/usr/bin/env python3

import configparser
import csv
import datetime as dt
import os
import shutil
import traceback
from pathlib import Path
from xml.etree import ElementTree as ET

from utilities.db_mgt import sst_db
from utilities.restore_SsT_from_backup import install_SsT_backup
from utilities.run_log_command import run_shell_command, OvernightLogger

from external_sites.manage_1and1 import Manage1and1
from external_sites.manage_google_drive import ManageGoogleDrive
from external_sites.manage_docx import ManageDocx

from practice.practice_one import DoNothingWell


# RClone config file in /home/don/.config/rclone/rclone.conf

def driver():
    # This script runs daily
    do_testing = True

    start_notest = dt.time(1, 0)     # but not if between 1am and 4am
    end_notest = dt.time(4, 0)
    if start_notest < dt.datetime.now().time() < end_notest:
        do_testing = False

    if do_testing:
        prototyping = True
        generate_web_pages = False           # Generate web pages to be uploaded to server
        local_alexa = False                  #     Use of 'local_' is as a sub-command under generate_web_pages
        load_SsT_wp_backup = False          # Install SsT from most current backup
        do_upload_to_1and1 = False          # Upload generated pages to 1and1
    else:
        prototyping = False
        generate_web_pages = True
        local_alexa = False
        load_SsT_wp_backup = True       # install SsT from backup
        do_upload_to_1and1 = True

    pth = os.path.abspath(os.curdir)            # Find current directory (where we are running)

    config = configparser.ConfigParser()

    with open("/home/don/devel/prototype/config_file.cfg") as source:     # NEED TO CHANGE THIS!!!!!!!!!!
        config.read(source.name)
    # Load parameters from configuration file
    start_date = config['measurement period']['startDate']
    end_date = config['measurement period']['endDate']

    start_measurement = (dt.datetime.strptime(start_date, "%Y/%m/%d")).date()
    end_measurement = (dt.datetime.strptime(end_date, "%Y/%m/%d")).date()

    dbname = config['database']['dbName']
    dbuser = config['database']['dbUser']

    os.curdir = config['paths']['workingDirectory']         # Set current working directory
    work_directory = config['paths']['workingDirectory']
    logs_directory = config['paths']['logsDirectory']
    wellness_plots = config['paths']['wellnessPlots']

    don_dir = Path('/home/don')                             # Don's home directory
    wp_test_dir = Path('/var/www/html')                     # Wordpress install
    don_devel = don_dir / 'devel'                           # Development Directory (the '/' is a path join operator)

    # Linix commands to access Google Drive
    cmd_rclone = 'rclone -v copyto {} gdriveremote:/RClone/{}'
    cmd_save_sst_files = "rclone -v copyto {} 'gdriveremote:/Sunnyside Times/SST Admin/{}'"
    cmd_get_sst_files = "rclone -v copy 'gdriveremote:/Sunnyside Times/SST Admin/{}' {}"

    summary_logger = OvernightLogger('summary_log', logs_directory)     # Logger - see use below
    summary_logger.make_info_entry('Start Nightly Run')

    if load_SsT_wp_backup:
        try:                                            # Trap error in this function so others don't get aborted
            # First set up a logger for this capability
            sst_logger = OvernightLogger('install_sst', logs_directory)
            sst_logger.make_info_entry('Start SsT Restore')

            # Do the work  (not included in this prototype)
            install_SsT_backup(sst_logger, dbname)      #Note logger passed for detailed logging

            # Log completion
            sst_logger.make_info_entry('Complete SsT Restore')
            sst_logger.close_logger()
            summary_logger.make_info_entry('load_SsT_wp_backup completed normally')
        except Exception as e:
            summary_logger.make_error_entry('load_SsT_wp_backup failed with exception: {}'.format(e.args))



    if generate_web_pages:
        target_directory = work_directory + 'auto_update'  # auto_update is temporary working dir - emptied at use
        try:
            folder_html_auto_generation_log = OvernightLogger('autoGenerateWebPages', logs_directory)
            folder_html_auto_generation_log.make_info_entry('Start Generate Web Pages')
            hostname = config['ionos']['hostname']
            username = config['ionos']['username']
            password = config['ionos']['password']
            mg_1and1 = Manage1and1(hostname, username, password)
            mg_google = ManageGoogleDrive()

            if local_alexa:         # Note that this allows multiple different commands in larger command group
                # process miscellaneous docs
                drive_dir_to_download = config['drive paths']['driveAdmin'] + config['drive paths']['driveMiscellaneous']
                for file in os.listdir(target_directory):
                    os.remove(target_directory + '/' + file)
                mg_google.download_directory(folder_html_auto_generation_log, drive_dir_to_download, target_directory,
                                             as_type='odt', dummy_source=None)
                for file in os.listdir(target_directory):
                    with open(target_directory + '/' + file) as fl:
                        file_root, file_type = file.split('.')
                        if file_type == 'docx':
                            if file_root == 'Basic Alexa Commands - Library':
                                lo = ManageDocx(
                                    '/home/don/devel/nightly-scripts/auto_update/Basic Alexa Commands - Library.docx')
                                res = lo.do_alexa_commands()
                                # st = SimpleTemplate(auto_gen_pages)          ## REMOVED SO THESE REFERENCES WOULD FAIL
                                # template = 'alexa_commands.html'
                                # context = st.make_alexa_context(res)
                                # outfile = 'alexa_commands.html'
                                # st.do_render_template(template, context, outfile)

        except Exception as e:
            summary_logger.make_error_entry('automatic page and directory generation failed: {}'.format(e.args))
            folder_html_auto_generation_log.make_error_entry('automatic page and directory generation failed: {}'.format(e.args))

        folder_html_auto_generation_log.make_info_entry('Complete Generate Web Pages')
        folder_html_auto_generation_log.close_logger()

    if do_upload_to_1and1:
        try:
            ionos_log = OvernightLogger('ionos_log', logs_directory)
            ionos_log.make_info_entry('Start Upload to 1and1 Processing')
            hostname = config['ionos']['hostname']
            username = config['ionos']['username']
            password = config['ionos']['password']
            mg_1and1 = Manage1and1(hostname, username, password)
            mg_1and1.upload_file_directory(wellness_plots, '/wp-content/plots/', delete_first=False)
            ionos_log.make_info_entry('Complete 1and1 Processing')
            ionos_log.close_logger()
            summary_logger.make_info_entry('do_upload_to_1and1 completed normally')
        except Exception as e:
            summary_logger.make_error_entry('do_upload_to_1and1 failed with exception: {}'.format(e.args))

    if prototyping:
        logger = OvernightLogger('prototyping', logs_directory)
        db_name = 'sst'
        drive_dir_to_download = config['drive paths']['driveAdmin'] + config['drive paths']['driveMinutes']
        target_directory = work_directory + 'worktemp/'
        try:
            message1 = None
            message2 = 37
            my_first_object = DoNothingWell(message1, message2)   # Do interesting stuff here
            my_first_object.print_something("A Message of Interest")
        except Exception as e:
            print(e)
            traceback.print_exc()

        logger.close_logger()

    summary_logger.make_info_entry('Nightly Run Completed')
    summary_logger.close_logger()


if __name__ == '__main__':
    driver()



