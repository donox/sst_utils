import pysftp
import os


class Manage1and1(object):
    def __init__(self, hostname, username, password):
        self.hostname = hostname
        self.username = username
        self.password = password

    def upload_single_file(self, filename, local_dir, remote_dir):
        with pysftp.Connection(host=self.hostname, username=self.username, password=self.password, port=22) as sftp:
            sftp.put(local_dir + filename, remote_dir + filename)

    def upload_file_directory(self, local_dir, remote_dir, delete_first=True):
        with pysftp.Connection(host=self.hostname, username=self.username, password=self.password, port=22) as sftp:
            if delete_first:         # THIS DOES NOT WORK - and there is no (working??) rmdir method though rmdir exists
                sftp.execute('rm -rf ' + remote_dir[:-1])
                sftp.mkdir(remote_dir)
            for entry in os.listdir(local_dir):
                fl = local_dir + entry
                if os.path.isfile(fl):
                    try:
                        sftp.put(fl, remote_dir + entry)
                    except Exception as e:
                        print(e)