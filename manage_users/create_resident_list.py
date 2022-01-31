from utilities.run_log_command import run_shell_command
import shutil
import os
import csv
import pandas as pd
from external_sites.manage_google_drive import ManageGoogleDrive
import xlrd


class CreateUserList(object):
    """Create list of users in form suitable for building user login or other uses."""
    def __init__(self, logger, temp_directory, google_dir):
        self.logger = logger
        self.drive = ManageGoogleDrive()
        self.temp_dir = temp_directory
        self.google_drive_dir = google_dir

    def process_resident_directory(self, dir_file):
        try:
            self.drive.download_file(self.logger, self.google_drive_dir, dir_file, self.temp_dir)
        except:
            raise ValueError(f"Failure downloading {dir_file}")

        try:
            res_date = pd.read_excel(self.temp_dir + dir_file, header=5)
            res_date.to_csv(self.temp_dir + "res.csv", columns=['Last Name', 'First Name'])
        except:
            raise ValueError(f"Failure reading resident phone list")

        res_list = []
        with open(self.temp_dir + "res.csv", 'r') as csv_file:
            rdr = csv.reader(csv_file)
            hdr = True
            for row in rdr:
                if hdr:
                    hdr = False
                else:
                    last = row[1]
                    first_names = row[2].split('&')
                    for first in first_names:
                        name_to_use = first
                        nickname_start = first.find("\"")
                        if nickname_start > -1:
                            nickname_end = first[nickname_start+1:].find("\"")
                            name_to_use = first[nickname_start+1: nickname_start + nickname_end + 1]
                        res_list.append((last.strip(), name_to_use.strip()))
            with open(self.temp_dir + 'residents.csv', 'w', newline='') as csvout:
                writer = csv.writer(csvout, delimiter = ' ')
                for last, first in res_list:
                    writer.writerow([first, last])
                csvout.close()
        csv_file.close()

        try:
            self.drive.upload_file(self.logger, self.temp_dir, 'residents.csv', self.google_drive_dir)
        except:
            raise ValueError(f"Failure uploading residents.csv")

    def process_staff_directory(self, dir_file):
        try:
            self.drive.download_file(self.logger, self.google_drive_dir, dir_file, self.temp_dir)
        except:
            raise ValueError(f"Failure downloading {dir_file}")

        try:
            res_date = pd.read_excel(self.temp_dir + dir_file, header=2)
            res_date.drop(res_date.columns[[0, 1, 2, 3]], axis=1, inplace=True)
            res_date.dropna(inplace=True)
            res_date.to_csv(self.temp_dir + "staff.csv", header=False, index=False)
        except:
            raise ValueError(f"Failure reading staff phone list")

        try:
            self.drive.upload_file(self.logger, self.google_drive_dir, "staff.csv", self.temp_dir)
        except:
            raise ValueError(f"Failure downloading {dir_file}")

