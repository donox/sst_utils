from utilities.run_log_command import run_shell_command
import shutil
import os
import pandas as pd
import tempfile as tf

# RClone config file in /home/don/.config/rclone/rclone.conf


class ManageGoogleDrive(object):
    def __init__(self):
        self.cmd_list_files = "rclone ls --max-depth 1 'sst_store:{}'"
        self.cmd_list_directories = "rclone lsd --max-depth 1 'sst_store:{}'"
        self.cmd_download_csv_file = "rclone -v --drive-formats csv copy 'sst_store:/'{} {}"
        self.cmd_download_file_or_directory = "rclone --max-depth {} -v copy  'sst_store:/{}' {}"
        self.cmd_upload_file_or_directory = "rclone -v copy '{}' 'sst_store:/'{}"

    @staticmethod
    def add_slash(folder):
        if type(folder) is tf.TemporaryDirectory:
            return folder
        if folder.endswith('/'):
            return folder
        else:
            return folder + '/'

    @staticmethod
    def split_directory_listing(result_string):
        items = result_string.split('\n')
        res = []
        for item in items:
            res.append(item.split(' ')[-1])
        return res

    def directory_list_files(self, logger, directory):
        try:
            ls_cmd = self.cmd_list_files.format(directory)
            res = run_shell_command(ls_cmd, logger, result_as_string=True)
            tmp = res.decode('utf-8')
            res = self.split_directory_listing(tmp)
            if res[-1] == '':
                res.pop()
            return res
        except Exception as e:
            logger.make_error_entry(f'Error listing files in directory: {directory}')
            raise e

    def directory_list_directories(self, logger, directory):
        try:
            ls_cmd = self.cmd_list_directories.format(directory)
            res = run_shell_command(ls_cmd, logger, result_as_string=True)
            res = res.decode('utf-8')
            res = self.split_directory_listing(res)
            if res[-1] == '':
                res.pop()
            return res
        except Exception as e:
            logger.make_error_entry(f'Error listing files in directory: {directory}')
            raise e

    def download_csv_file(self, logger, file, download_dir, dummy_source=None):
        '''Download Google Spreadsheet as csv file.'''
        try:
            if dummy_source:
                shutil.copy(dummy_source, download_dir)
            else:
                download_files_cmd = self.cmd_download_csv_file.format(file, download_dir)
                run_shell_command(download_files_cmd, logger)
        except Exception as e:
            logger.make_error_entry('Error downloading spreadsheet {}'.format(file))
            raise e

    def download_directory(self, logger, dir_to_download, target_dir, max_depth=1):
        """Download contents of specified directory to local directory.
        """
        try:
            download_files_cmd = self.cmd_download_file_or_directory.format(max_depth, dir_to_download, target_dir)
            run_shell_command(download_files_cmd, logger)
        except Exception as e:
            logger.make_error_entry('Error downloading file directory {}'.format(dir_to_download))
            raise e

    def download_file(self, logger, source_dir, file_to_download, target_dir):
        try:
            download_files_cmd = self.cmd_download_file_or_directory.format(1, self.add_slash(source_dir) +
                                                                            file_to_download, target_dir)
            run_shell_command(download_files_cmd, logger, outfile=file_to_download)
        except Exception as e:
            logger.make_error_entry('Error downloading file  {}'.format(file_to_download))
            raise e

    def upload_file(self, logger, target_dir, file_to_upload, source_dir):
        try:
            upload_files_cmd = self.cmd_upload_file_or_directory.format(self.add_slash(source_dir) +
                                                                        file_to_upload, target_dir)
            run_shell_command(upload_files_cmd, logger)
        except Exception as e:
            logger.make_error_entry('Error downloading file  {}'.format(file_to_upload))
            raise e


def copytree(src, dst, symlinks=False, ignore=None):
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)


def convert_directory_to_csv(src):
    '''Convert directory of spreadsheets to csv and delete originals'''
    for item in os.listdir(src):
        s = os.path.join(src, item)
        fn, tp = item.split('.')
        d = os.path.join(src, fn + '.csv')
        if tp == 'xls' or tp == 'xlsx' or tp == 'ods':
            data_xls = pd.read_excel(s, None, index_col=None)
            df = data_xls[list(data_xls)[0]]
            df.to_csv(d, encoding='utf-8', index=False)
