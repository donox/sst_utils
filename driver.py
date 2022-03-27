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
import config_private as private
import tempfile as tf
from system_control import system_manager as sm
import yaml
from new_content import validate_shortcodes as vs


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
        do_testing = True

    if do_testing:
        prototyping = False
        sst_management = True
        build_user_list = False
        build_staff_list = False
        build_horizon_list = False
        create_combined_login = False

    else:           # Intended for cron job run nightly
        prototyping = False
        sst_management = False
        build_user_list = False
        build_staff_list = False
        build_horizon_list = False
        create_combined_login = False

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
        # commands.txt user prefix set with: os.environ["USER_PREFIX"]
        sys_mgr = sm.SystemManager()
        sys_mgr.run_command_processor()

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

    if prototyping:
        logger = OvernightLogger('prototyping', logs_directory)
        drive_dir_to_download = config['drive paths']['driveAdmin'] + config['drive paths']['driveMinutes']
        target_directory = work_directory + 'worktemp/'
        test_dir = temp_directory + 'fix_meta_paths/'
        path_element_to_find = 'pages/aa-activities-index'
        path_element_to_replace= 'pages'
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

            logger.close_logger()

        except Exception as e:
            print(e)
            traceback.print_exc()

    if False and prototyping:
        logger = OvernightLogger('prototyping', logs_directory)
        db_name = 'sst'
        drive_dir_to_download = config['drive paths']['driveAdmin'] + config['drive paths']['driveMinutes']
        target_directory = work_directory + 'worktemp/'
        test_dir = temp_directory + 'validate/'
        try:
            filepath = test_dir + 'Springtime.docx'
            filetype = 'docx'
            val_sc = vs.ValidateShortcodes(filepath, filetype, logger)
            val_sc.clean_docx()
            val_sc.process_shortcodes()
            logger.close_logger()

        except Exception as e:
            print(e)
            traceback.print_exc()

    if False and prototyping:
        logger = OvernightLogger('prototyping', logs_directory)
        db_name = 'sst'
        drive_dir_to_download = config['drive paths']['driveAdmin'] + config['drive paths']['driveMinutes']
        target_directory = work_directory + 'worktemp/'
        try:
            from collections import deque

            class SupportFlexbox(object):
                """Provide support for css flexbox.

                Nikola does not support nested shortcodes so we remove the "box" shortcode and
                convert it to proper html on the markdown file prior to submitting to nikola."""
                # Box start shortcode:  {{% box name="xxx" direction="row" %}}
                box_start = r'(?P<start>\{\{% +box\s+name="(?P<name_s>\w+)"'
                box_start += r'(\s+(?P<attrs>((((\w+)="((\w|:|-)+)")\s+))*))%\}\})'
                box_end = r'(?P<end>\{\{% +/box\s+name="(?P<name_e>\w+)"\s+%\}(?P<last_char>\}))'
                # Note: DOTALL makes '.' include newlines
                box_comp_start = re.compile(box_start)
                box_comp_end = re.compile(box_end)
                box_attr = re.compile(r'(?P<attribute>\w+)="(?P<value>(\w|_|-|:|;)+)"')

                def __init__(self):
                    self.stack = deque()

                def process_box_shortcodes(self, in_string, result):
                    """Process next shortcode and recurse to process nested codes.

                    There are three cases:
                    (1) input does not match start  or end of shortcode:  return in_string
                    (2) input finds first open box:
                            (a) get box name, other parameters and push on stack.
                            (b) recurse on tail of in_string.
                    (3) input finds close box:
                        (a) get name and compare to top of stack - must match or throw error.
                        (b) emit html using parameters from stack and surround current in_string as returned
                            from recursion.
                        (c) process tail."""
                    if not in_string:
                        return ''

                    # Determine closest box shortcode and amount of in_string before it
                    start_pos_start = start_pos_end = end_pos_start = end_pos_end = None
                    search_start = self.box_comp_start.search(in_string)
                    if search_start:
                        start_pos_start, start_pos_end = search_start.span()
                    search_end = self.box_comp_end.search(in_string)
                    if search_end:
                        end_pos_start, end_pos_end = search_end.span()
                    # Determine beginning of closest box shortcode
                    if search_start and start_pos_end:
                        str_beginning = min(start_pos_start, end_pos_start)
                    elif search_start:
                        str_beginning = start_pos_start
                    elif search_end:
                        str_beginning = end_pos_start
                    else:
                        str_beginning = len(in_string)

                    if str_beginning > 0:
                        result.append(in_string[0:str_beginning])
                        self.process_box_shortcodes(in_string[str_beginning:], result)
                    elif str_beginning == start_pos_start:
                        # Process box beginning
                        box_match = search_start.groupdict()
                        box_match_keys = box_match.keys()
                        if 'name_s' in box_match_keys:
                            print(f"Matched start: {box_match['name_s']}")
                            self.stack.append(box_match)
                            print(f"PUSH: {self.stack[-1]['name_s']}")
                            a_tmp = box_match['attrs']
                            begin_text = self._build_flex_container_start(box_match['attrs'])
                            result.append(begin_text)
                            # print(f"1: {in_string[match_len:]}")
                            self.process_box_shortcodes(in_string[start_pos_end:], result)
                            foo = 3
                    elif str_beginning == end_pos_start:
                        # process box end
                        box_match = search_end.groupdict()
                        box_match_keys = box_match.keys()
                        if 'name_e' in box_match_keys:
                            end_name = box_match['name_e']
                            print(f"Matched end: {box_match['name_e']}")
                            if not self.stack:
                                raise ValueError(f'Closing box found with no matching start')
                            start_dict = self.stack[-1]
                            start_name = start_dict['name_s']
                            if start_name != end_name:
                                raise ValueError(f'Unmatched containers: {start_name} and {end_name}')
                            print(f"POP: {self.stack[-1]['name_s']}")
                            self.stack.pop()
                            result.append('</div>')
                            self.process_box_shortcodes(in_string[end_pos_end:], result)
                            foo = 3
                    else:
                        result.append(in_string)

                def _build_flex_container_start(self, attrs):
                    attr_dict = dict()
                    while True:
                        parsed_attrs = self.box_attr.search(attrs)
                        if not parsed_attrs:
                            break
                        attr_dict[parsed_attrs.group('attribute')] = parsed_attrs.group('value')
                        attrs = attrs[parsed_attrs.end('value'):]
                    dict_keys = list(attr_dict.keys())
                    if 'direction' in dict_keys:
                        dict_keys.remove('direction')
                        val = attr_dict['direction']
                        if val == 'row':
                            cls = 'src_flex_container'
                        elif val == 'row-reverse':
                            cls = 'src_flex_container_rev'
                        elif val == 'column' or val == 'col':
                            cls = 'src_flex_container_col'
                        elif val == 'column-reverse' or val == 'col-reverse':
                            cls = 'src_flex_container'
                        else:
                            cls = f'src_flex_container UNRECOGNIZED BOX DIRECTION {val}'
                    other_attrs = []
                    for key in dict_keys:
                        other_attrs.append(f' {key}="{attr_dict[key]}"')
                    other_attrs = ' '.join(other_attrs)
                    start_str = f'<div class="{cls}" {other_attrs}>'
                    return start_str

            pbs = SupportFlexbox()
            a_test_string = b_test
            # a_test_string += 'Now is the time '
            # a_test_string += ' {{% box   name="foo" \n direction="row" %}}'
            # a_test_string += ' {{% cvb   name="foo"  direction="row" %}}'
            # a_test_string += ' {{% box \n  name="bar"  direction="column" %}}'
            # a_test_string += ' xx random stuff xx'
            # a_test_string += ' {{% /box name="bar" %}}'
            # # a_test_string += r'    direction="column"   style="display:None"   '
            # a_test_string += ' {{% box   name="baz"  direction="column" style="display:None" %}}'
            # a_test_string += ' xx random stuff xx'
            # a_test_string += ' {{% /box name="baz" %}}'
            # a_test_string += ' xx boxitems xx'
            # a_test_string += ' {{% /box name="foo" %}}'
            # a_test_string += '  asdfasdf asf'
            res = []
            pbs.process_box_shortcodes(a_test_string, res)
            full_result = "".join(res)

            foo = 3
        except Exception as e:
            print(e)
            traceback.print_exc()

        logger.close_logger()

    summary_logger.make_info_entry('Nightly Run Completed')
    summary_logger.close_logger()


b_test = """<p><strong>{{% meta_info info_type=”title” %}}Musings from the Sunnyside Library{{%/ meta_info %}}</strong></p>
<p>{{% meta_info info_type=”byline” %}}By Barbara Boothe{{% meta_info %}}</p>
<p>Well, January brought us some significant snow and really cold temperatures! Let’s hope that February is a bit more moderate!</p>
<p>{{% singlepic image="/images/Eiland-Center-Library/Book-Lr.jpg" width="400px" height="300px" alignment="center" caption="" title="" has_borders="False" %}}</p>
<p>{{% box name="foo" direction="row" style="display:box"  foo="bar" baz="bat" %}}</p>
<p><strong>Eiland Center Library</strong></p>
<p>We have been busy cataloging the books at the Eiland Center Library in January. We hope to finish that project soon so Robert can begin the renovations of the two rooms. Two rooms, you say?</p>
<p>{{% box name="bar" direction="column" %}}</p>
<p>Well, if you have not been to the Eiland Center Library, I would encourage you to make a trip there. That way you will be able to see how it all transforms!</p>
<p>{{% /box name="bar" %}}</p>
<p>{{% box name="baz" direction="row-reverse" %}}</p>
<p>Barbara Boothe is interviewing the Assisted Living residents to get an idea of how best to make the library supportive of their needs and desires.</p>
<p>{{% /box name="baz" %}}</p>
<p><strong>Highlands Library</strong></p>
<p>We have some new signage coming. We also have a magnifier reader on its way. If you have trouble reading a magazine, newspaper, a regular print book, or the instructions on your pill bottle, we encourage you to check it out. Watch for more information about this new addition to the library.</p>
<p><strong>New Books </strong></p>
<p>New books are on the counter—<em><strong>The Judge’s List</strong></em> by John Grisham; <strong>The Thursday Murder Club</strong> and <strong>The Man Who Died Twice</strong> by Richard Orman; and <strong>Susie, Linda, Nina, and Cokie</strong> by Lisa Napoli.</p>
<p>{{% /box name="foo" %}}</p>
<p><strong>Book Clubs</strong></p>
<p><strong>Sunny Readers</strong></p>
<p>February 9, 3:00 p.m., 4263 Grattan Price Dr.</p>
<p><em>My Dear Hamilton</em> by Eliza Schuyler Hamilton</p>
<p><strong>Shenandoah Readers</strong></p>
<p>February 22, 10:00 a.m., Shenandoah Room, Highlands</p>
<p><em>Becoming</em> by Michelle Obama</p>
<p>March 22, 10:00 a.m., Shenandoah Room, Highlands</p>
<p><em>Cairnaerie</em> by MKB Graham</p>
<p><strong>Who Dun It Club</strong></p>
<p>March 2, 1:30 p.m., Sunnyside Room</p>
<p><em>Dolphin Junction</em> by Mick Herron</p>
<p>April 6, 1:30 p.m., Sunnyside Room</p>
<p><em>Daughter of Time</em> by Josephine Tey</p>
"""

if __name__ == '__main__':
    driver()
