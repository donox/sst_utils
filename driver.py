#!/usr/bin/env python3

import configparser
import csv
import datetime as dt
import os
import shutil
import traceback
import yaml as YAML
import pathlib as pl
from xml.etree import ElementTree as ET
from new_content.process_new_content_folder import ProcessNewContentFolder as pncf
from utilities.run_log_command import run_shell_command, OvernightLogger

from system_control.manage_google_drive import ManageGoogleDrive
from manage_users.create_resident_list import CreateUserList
from utilities.send_email import ManageEmail
from system_control import command_processor as cmd_proc
import config_private as private
import tempfile as tf
from system_control import system_manager as sm
import yaml


# RClone config file in /home/don/.config/rclone/rclone.conf

def driver():
    try:
        # Use environment variable to determine user for accessing config file
        # machine dependencies.  When running in PyCharm, define in run configuration.
        # Values = 'don', 'sam', (add others as needed)
        sst_user = os.environ['USER']
    except:
        raise SystemError("No USER Environment Variable specified")

    # This script is intended to run daily, so there is a notion of 'testing' which is applicable
    # during development or other non-automated execution.  Automated execution requires creating
    # a Linux timer driven script.
    do_testing = True
    # Assume that any run between 1am and 4am is for production
    start_notest = dt.time(1, 0)  # but not if between 1am and 4am
    end_notest = dt.time(3, 0)
    if start_notest < dt.datetime.now().time() < end_notest:
        do_testing = False

    if do_testing:
        prototyping = False
        sst_management = True
        process_images = False  # Probably not needed process
        load_content_files = False
        build_user_list = False
        build_staff_list = False
        build_horizon_list = False
        create_combined_login = False
        drive_content_dir = "SSTmanagement/NewContentDev"
        # drive_content_dir = "SSTmanagement/NewContent"
        # drive_content_dir = "SSTmanagement/NewContentTest"
        stories_to_process = "all"              # To process specific directories, list them below


    else:
        prototyping = False
        sst_management = True
        process_images = False
        load_content_files = False
        build_user_list = False
        build_staff_list = False
        build_horizon_list = False
        create_combined_login = False
        drive_content_dir = "SSTmanagement/NewContent"
        stories_to_process = "all"  # To process specific directories, list them below
        # stories_to_process = ["dir 1", "dir 2"]

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
    smtp_server = config['email']['smtpServer']
    smtp_port = config['email']['smtpPort']
    email_username = private.username
    email_password = private.password

    summary_logger = OvernightLogger('summary_log', logs_directory)  # Logger - see use below
    if do_testing:
        summary_logger.make_info_entry('Start Testing Run')
    else:
        summary_logger.make_info_entry('Start Nightly Run')

    if sst_management:
        sys_mgr = sm.SystemManager()
        sys_mgr.run_command_processor()

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

            temps = tf.TemporaryDirectory(prefix='docx', dir=temp_directory)

            # First, pick up configuration yaml file
            filename = 'config_users.yaml'
            try:
                manage_drive.download_file(sst_logger, "SSTmanagement/", filename, temps.name)
                with open(pl.Path(temps.name) / filename, 'r', encoding='utf-8') as fd:
                    res = YAML.safe_load_all(fd)
                    docs = [doc for doc in res]
                    fd.close()
                users = [x["name"] for x in docs if x]
                user_data = dict()
                for n, user in enumerate(users):
                    if user:
                        user_data[user] = docs[n+1]
            except Exception as e:
                print(e)
                traceback.print_exc()

            try:
                # pull everything from Google Drive to local temp directory
                manage_drive.download_directory(sst_logger, drive_content_dir, temps.name)
                if stories_to_process == "all":
                    stories = os.listdir(temps.name)
                else:
                    stories = stories_to_process
                for story_dir in stories:
                    dirpath = temps.name
                    if os.path.isdir(dirpath):
                        content = os.listdir(dirpath)
                        dirnames = []
                        filenames = []
                        for x in content:
                            if os.path.isdir(dirpath + '/' + x):
                                dirnames.append(x)
                            else:
                                filenames.append(x)
                        try:
                            process_folder = pncf(sst_logger, dirpath, dirnames, filenames, temp_directory,
                                                  docx_directory, sst_directory, image_directory, gallery_directory)
                            result = process_folder.process_content()
                        except Exception as e:
                            sst_logger.make_error_entry(f"Folder {dirpath} has an error: {e.args}")
                    else:
                        sst_logger.make_error_entry(f"Folder {dirpath} from story list {stories} not found.")
            except Exception as e:
                print(e)
                traceback.print_exc()

            # Log completion
            sst_logger.make_info_entry('Complete Docx Loading')
            sst_logger.close_logger()
            summary_logger.make_info_entry('load_content_files completed normally')
        except Exception as e:
            summary_logger.make_error_entry('load_content_files failed with exception: {}'.format(e.args))

    if build_user_list or build_staff_list or build_horizon_list:
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
            if build_user_list:
                res_list_processor.process_resident_directory(resident_phone_list)
            if build_staff_list:
                res_list_processor.process_staff_directory(staff_phone_list)
            if build_horizon_list:
                res_list_processor.process_horizon_directory(horizon_club_list)

            # Log completion
            sst_logger.make_info_entry('Complete User Login Creation')
            sst_logger.close_logger()
            summary_logger.make_info_entry('build_user_list completed normally')
        except Exception as e:
            summary_logger.make_error_entry('build_user_list failed with exception: {}'.format(e.args))

    if create_combined_login:
        # Copy current login lists from Google Drive, combine them and move to sst/support/users.csv
        try:
            sst_logger = OvernightLogger('build_users_csv', logs_directory)
            sst_logger.make_info_entry('Start User Login Creation')

            resident_phone_list = "Sunnyside Resident Phone Directory. 01-2022.xls"
            staff_phone_list = "Sunnyside Staff Directory. 01-2022.xls"
            google_drive_dir = "SSTmanagement/UserData/"
            temps = temp_directory + 'user_list_temp/'
            if os.path.exists(temps):  # Anything from prior runs is gone
                shutil.rmtree(temps)
            os.mkdir(temps)

            files = ['residents.csv', 'staff.csv', 'horizon.csv']
            outfile = 'users.csv'
            res_list_processor = CreateUserList(sst_logger, temps, google_drive_dir)
            res_list_processor.get_all_users(files, outfile)

            shutil.copy(temps + 'users.csv', sst_support_directory + 'users.csv')

            # Log completion
            sst_logger.make_info_entry('Complete Creation of sst/support/users.csv')
            sst_logger.close_logger()
            summary_logger.make_info_entry('build_users_csv completed normally')
        except Exception as e:
            summary_logger.make_error_entry('build_users_csv failed with exception: {}'.format(e.args))

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
            # mgr = ManageEmail(email_username, email_password, smtp_server, smtp_port)
            # mgr.add_recipient("don@theoxleys.com")
            # mgr.add_recipient("donoxley@gmail.com")
            # mgr.set_subject("Log result of running test")
            # mgr.add_attachment(logs_directory + "summary_log.log")
            # mgr.set_body("THis is the body")
            # mgr.send_email()

            # cmds = cmd_proc.SystemUser(temp_directory, logger)
            # print(cmds.users)

            # dirs = cmd_proc.ManageFolders(temp_directory, logger)
            # dirs.process_commands_top()
            # dirs.process_commands("SSTmanagement/NewContentDev/", "content", ["identity", "single"])
            file_path = '/home/don/Documents/Temp/Sunnybear_New_Year.txt'
            with open(file_path) as stream:
                story_content = yaml.safe_load_all(stream)
                for line in story_content:
                    print(line)
            foo = 3

        except Exception as e:
            print(e)
            traceback.print_exc()

        logger.close_logger()

    summary_logger.make_info_entry('Nightly Run Completed')
    summary_logger.close_logger()


if __name__ == '__main__':
    driver()
