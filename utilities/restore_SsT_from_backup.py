#!/usr/bin/env python3

from pathlib import Path
from utilities.run_log_command import run_shell_command, OvernightLogger
import tempfile
import gzip
import zipfile
import shutil
import re
import os

from utilities.db_mgt import sst_db

table_pre_directives = [
    '/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;',
    "/*!40103 SET TIME_ZONE='+00:00' */;",
    '/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;',
    '/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;',
    '/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;',
    '/*!40101 SET NAMES utf8mb4 */;',
    '/*!40101 SET CHARACTER SET  UTF8MB4 */;',
    "/*!40101 SET SQL_MODE='ALLOW_INVALID_DATES' */;"]


table_post_directives = [
    '/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;',
    '/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;',
    '/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;',
    '/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */']


def download_backup(logger):
    '''Download latest backup from google drive to specified directory.

    :return: temporary directory with downloaded files
    '''
    logger.make_info_entry('Beginning SsT download')
    don_dir = Path('/home/don')
    wp_test_dir = Path('/var/www/html')
    don_devel = don_dir / 'devel'
    file_list = don_devel / 'foo'

    cmd_list_files_json = 'rclone ls gdriveremote:/UpdraftPlus/'
    cmd_download_file = 'rclone copy gdriveremote:/UpdraftPlus/{} {}'
    run_shell_command(cmd_list_files_json, logger, outfile=file_list)
    flist = {}
    max_date = 0
    try:
        with open(file_list, 'r') as fl:
            while not fl.closed:
                tmp = fl.readline()
                if len(tmp) > 10:
                    xx, ln = tmp.split()
                    dt = ln[7:17]
                    yr = int(dt[0:4]) * 12 * 31
                    mo = int(dt[5:7]) * 31
                    dy = int(dt[8:])
                    val = yr + mo + dy
                    if val in flist.keys():
                        flist[val].append(ln)
                    else:
                        flist[val] = [ln]
                    if val > max_date:
                        max_date = val
                else:
                    fl.close()
        files = flist[max_date]
    except Exception as e:
        logger.make_error_entry('Exception processing in download_backup')
        raise e
    tempdir = tempfile.mkdtemp()
    try:
        for file in files:
            last = file.split('-')[-1]
            last = tempdir + '/' + last          # last part of GDrive name is file name
            cmd = cmd_download_file.format(file, last)
            logger.make_info_entry('File {} being downloaded to {}'.format(file, last))
            run_shell_command(cmd, logger)
    except Exception as e:
        logger.make_error_entry('Exception downloading a file')
        raise e

    return tempdir


def process_zipped_files(tmpdir, wp_install):
    '''Find all zipped files, unzip them and relocate them to wp-content

    :param tmpdir:  Directory containing files including zip files to be processed.
    :param wp_install: Wordpress directory in which to create wp-content
    :return:
    '''
    # Delete wp-content if it exists, this may have problems on Windows (see Python docs)
    content_dir = wp_install+"/wp-content"
    shutil.rmtree(content_dir, ignore_errors=True)
    os.mkdir(content_dir, 0o777)

    for file_dir in os.listdir(tmpdir):
        if file_dir.endswith('.zip'):
            for file in os.listdir(tmpdir + '/' + file_dir):
                zip_ref = zipfile.ZipFile(tmpdir + '/' + file_dir + '/' + file, 'r')
                zip_ref.extractall(content_dir)
                zip_ref.close()


def _load_record(rec, fout, fl=None):
    if rec.startswith('#') or rec.startswith('\n') or rec.startswith('LOCK') or rec.startswith('UNLOCK'):
        pass
    elif rec.startswith('/*') or rec.startswith('DROP'):
        try:
            fout.writelines(rec)
        except:
            foo = 3
    elif rec.startswith('CREATE') or rec.startswith('INSERT'):
        query = rec
        for newrec in fl:
            query += newrec
            if ';' in newrec[-5:]:  # may be some blanks after end of query
                try:
                    fout.writelines(query)
                except:
                    foo = 3
                break


def load_database_by_record(db_name, db_table, tmp_dir, outfile):
    '''load SsT database with backup data table record by record.

    This assumes the format of a file as a table taken from mysqldump.

    :param db_file:
    :return:
    '''
    fl_name = tmp_dir + '/' + db_table + '.sql'
    fl_out = tmp_dir + '/' + outfile + 'X.sql'
    with open(fl_out, 'w') as file_out:
        for rec in table_pre_directives:
            _load_record(rec, file_out)
        with open(fl_name, 'r', encoding='utf-8') as fl:
            for rec in fl:
                try:
                    _load_record(rec, file_out, fl=fl)
                except:
                    foo = 3
        for rec in table_post_directives:
            _load_record(rec, file_out)
        file_out.close()
    with sst_db(db_name) as cnx:
        tmp = db_table
        if tmp[-1] == '2':
            tmp = tmp[:-1]
        query_file = tmp_dir + '/' + tmp + "X.sql"
        query = open(query_file, 'r').read()
        for x in cnx.cmd_query_iter(query):         # Works by side effect - command breaks query into statements
            pass
        cnx.commit()



def parse_db_file(db_file, tmp_dir):
    '''Unzip, break-up db file into individual table files.

    The database file is downloaded as a folder containing the zipped file, so
    we need to remove the outer folder

    :param db_file:
    :return:
    '''
    if os.path.isdir(db_file):
        db_file += '/' + os.listdir(db_file)[0]     # contains only 1 file
    full_file = tmp_dir + '/out.txt'
    with gzip.open(db_file, 'rb') as f_in:
        with open(full_file, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

    with open(full_file, 'rt') as fl:
        all_lines = fl.readlines()

    table_start = []
    table_names = []

    mx_line = 0
    for line_no, line in enumerate(all_lines):
        if '# Table:' in line:
            table_start.append(line_no)
            st = line.find('`')
            table_names.append(line[st+1:-2])
        mx_line = line_no
    table_end = [ x-1 for x in table_start[1:]]
    table_end.append(mx_line)

    for name, st, end in zip(table_names, table_start, table_end):
        fl_name = tmp_dir + '/' + name + '.sql'
        with open(fl_name, 'w') as fl:
            fl.writelines(all_lines[st: end+1])
            fl.close()
    return table_names


def process_db_file(dbname, tmp_dir, logger):
    '''Process backup file for database, modify tables, and load database.

    :return: None
    '''
    xx = 'db.gz'
    # tmp_dir = '/home/don/devel/sst_backup'
    tables = parse_db_file(tmp_dir + '/' + xx, tmp_dir)
    logger.make_info_entry('Processing Database file')
    for table in tables:
        # print(table)
        if table == 'wp_options':
            new_table = process_wp_options(tmp_dir)
            load_database_by_record(dbname, new_table, tmp_dir, table)
        elif table == 'wp_posts':
            new_table = process_wp_posts(tmp_dir)
            load_database_by_record(dbname, new_table, tmp_dir, table)
        elif table == 'wp_users':
            new_table = process_wp_users(tmp_dir)
            load_database_by_record(dbname, new_table, tmp_dir, table)
        else:
            load_database_by_record(dbname, table,  tmp_dir, table)


def process_post(line):
    '''Process individual post  in table wp_posts.

    :param line:
    :return:
    '''
    xl = line.find('(')
    xr = line.rfind(')')
    ln = line[xl+1:xr]
    if xl > -1 and xr > -1:
        opt_val = replace_site(ln)
        new_line = line[:xl+1] + opt_val + line[xr:]
        return new_line
    else:
        return line


def process_wp_posts(tmp_dir):
    '''Update table wp_posts to support new instance of SsT

    :param tmp_dir:
    :return:
    '''
    fl_name = tmp_dir + '/wp_posts.sql'
    fl_out = tmp_dir + '/wp_posts2.sql'
    with open(fl_name, 'r') as fl:
        tmp = fl.readlines()
        with open(fl_out, 'w') as f_out:
            initial_lines = True
            for line in tmp:
                if initial_lines:
                    x = line.find('INSERT')
                    if x < 0:
                        f_out.write(line)
                    else:
                        initial_lines = False
                        f_out.write(process_post(line))
                else:
                    line = line.replace('0000-00-00', '2019-01-01')
                    f_out.write(process_post(line))
            f_out.close()
        fl.close()
    return 'wp_posts2'

def process_wp_users(tmp_dir):
    '''Update table wp_users to support new instance of SsT by correcting default dates

    :param tmp_dir:
    :return:
    '''
    fl_name = tmp_dir + '/wp_users.sql'
    fl_out = tmp_dir + '/wp_users2.sql'
    with open(fl_name, 'r') as fl:
        tmp = fl.readlines()
        with open(fl_out, 'w') as f_out:
            for line in tmp:
                line = line.replace('0000-00-00', '2019-01-01')
                f_out.write(process_post(line))
            f_out.close()
        fl.close()
    return 'wp_users2'



pattern_site = re.compile("(https?://)?(www\.)?sunnyside-times.com")


def replace_site(opt_val):
    occurs, count = pattern_site.subn('http://localhost', opt_val)
    if count:
        return occurs
    return opt_val


def do_substitute(opt_name, opt_val):
    '''Make changes to specific option.

    :param opt_name:
    :param opt_val:
    :return:
    '''
    return replace_site(opt_val)


def process_option(line):
    '''Process individual option value in table wp_options.

    :param line:
    :return:
    '''
    xl = line.find('(')
    xr = line.rfind(')')
    ln = line[xl+1:xr]
    if xl > -1 and xr > -1:
        res = [m.start() for m in re.finditer("'", ln)]     # Can't use re because of embedded single quotes.
        if not res:             # Should probably not occur -
            return line
        else:
            # return line
            opt_name = ln[res[0]+1:res[1]]
            opt_val = ln[res[2]+1:res[-3]]
            opt_val = do_substitute(opt_name, opt_val)
            opt_other = ln[res[-2]+1:]

            new_line = line[:xl+1] + ln[:res[0]] + "'" + opt_name + "', '" + opt_val + "', '" + opt_other + line[xr:]
            return new_line
    else:
        return line


def process_wp_options(tmp_dir):
    '''Update table wp_options to support new instance of SsT

    :param tmp_dir:
    :return:
    '''
    fl_name = tmp_dir + '/wp_options.sql'
    fl_out = tmp_dir + '/wp_options2.sql'
    with open(fl_name, 'r') as fl:
        tmp = fl.readlines()
        with open(fl_out, 'w') as f_out:
            initial_lines = True
            for line in tmp:
                if initial_lines:
                    x = line.find('INSERT')
                    if x < 0:
                        f_out.write(line)
                    else:
                        initial_lines = False
                        f_out.write(process_option(line))
                else:
                    f_out.write(process_option(line))
            f_out.close()
        fl.close()
    return 'wp_options2'


def print_diff_files(dcmp):
    for name in dcmp.diff_files:
        print("diff_file %s found in %s and %s" % (name, dcmp.left, dcmp.right))
        for sub_dcmp in dcmp.subdirs.values():
            print_diff_files(sub_dcmp)


def find_diff_tables_usermeta(db1, db2):
    '''Compare a table in two databases for diffs.'''
    query = ''
    with sst_db(db1) as cnx1:
        cursor1 = cnx1.cursor(buffered=True)
        with sst_db(db2) as cnx2:
            cursor2 = cnx2.cursor(buffered=True)
            query = 'SELECT * FROM wp_usermeta'
            cursor1.execute(query)
            cursor2.execute(query)
            for x,y in zip(cursor1.fetchall(), cursor2.fetchall()):
                if x[1] == 1 and y[1] == 1:
                    if x[2] == y[2]:
                        if x[3] != y[3]:
                            print(x[2], x[3], y[3])
                    else:
                        print("DIFF KEYS", x[2], y[2])

def find_diff_tables_postmeta(db1, db2):
    '''Compare a table in two databases for diffs.'''
    query = ''
    with sst_db(db1) as cnx1:
        cursor1 = cnx1.cursor(buffered=True)
        with sst_db(db2) as cnx2:
            cursor2 = cnx2.cursor(buffered=True)
            query = 'SELECT post_id FROM wp_postmeta'
            cursor1.execute(query)
            post1 = set(cursor1.fetchall())
            cursor2.execute(query)
            post2 = set(cursor2.fetchall())
            query = 'SELECT meta_key FROM wp_postmeta'
            cursor1.execute(query)
            key1 = set(cursor1.fetchall())
            cursor2.execute(query)
            key2 = set(cursor2.fetchall())
            keydel = key1.intersection(key2)
            key1unique = key1 - key2
            key2unique = key2 - key1
            umkeys = [x[0] for x in keydel if x[0].startswith('_um')]
            query = 'SELECT post_id FROM wp_postmeta where meta_key = "_um_can_access_wpadmin"';
            cursor1.execute(query)
            cursor2.execute(query)
            wp_admin_posts1 = set(cursor1.fetchall())
            wp_admin_posts2 = set(cursor2.fetchall())
            wp_admin_same = wp_admin_posts1.intersection(wp_admin_posts2)
            wp_admin_diff = wp_admin_posts1.union(wp_admin_posts2) - wp_admin_same
            for xx in wp_admin_same:
                query = 'SELECT * from wp_posts WHERE id={}'.format(xx[0])
                cursor1.execute(query)
                cursor2.execute(query)
                p1 = cursor1.fetchone()
                p2 = cursor2.fetchone()
                s1 = list(p1[4:14]).append(list(p1[16:]))
                s2 = list(p2[4:14]).append(list(p2[16:]))
                if s1 != s2:
                    print(s1)
                    print(s2)

            cursor2.execute(query)
            for x, y in zip(cursor1.fetchall(), cursor2.fetchall()):
                if x[1] == 1 and y[1] == 1:
                    if x[2] == y[2]:
                        if x[3] != y[3]:
                            print(x[2], x[3], y[3])
                    else:
                        print("DIFF KEYS", x[2], y[2])
            foo = 3


def find_diff_tables_options(db1, db2):
    repl_list = ['wp_user_roles']
    with sst_db(db1) as cnx1:
        cursor1 = cnx1.cursor(buffered=True)
        with sst_db(db2) as cnx2:
            cursor2 = cnx2.cursor(buffered=True)
            query = 'SELECT * FROM wp_options'
            cursor1.execute(query)
            for idx, name, value, other in cursor1.fetchall():
                query = 'SELECT option_value FROM wp_options where option_name="{}"'.format(name)
                cursor2.execute(query)
                if cursor2.rowcount == 1:
                    val = cursor2.fetchone()[0]
                    if val != value:
                        # print('opt: {}, foo: {}, sst {}'.format(name, value, val))
                        if name in repl_list:
                            query = "UPDATE wp_options SET option_value = '{}' WHERE option_id  = {}".format(val, idx)
                            cursor1.execute(query)
                            cnx1.commit()



def parse_php_array(val):
    '''Convert PHP array to Python dictionary.

    Does not handle all cases (I, N, ..)

    :param val:
    :return:
    '''
    if len(val) == 0:
        return None, None
    if val[0] == '}' or val[0] == ';':
        return None, val[1:]
    if val[0] == 'b':       # Boolean
        return int(val[2]), val[4:]
    if val[0] == 'a':       # Array
        result = dict()
        left, right = val[2:].split(':', 1)
        nbr_entries = int(left)
        right = right[1:]
        while nbr_entries > 0:
            if nbr_entries == 111:
                foo = 3
            key, right = parse_php_array(right)
            value, right = parse_php_array(right)
            result[key] = value
            if right:
                nbr_entries -= 1
        return result, right
    if val[0] == 's':       # String
        left, right = val[2:].split(':', 1)
        sl = int(left) + 3
        entry = right[0: sl-1]
        # print(entry)
        return entry, right[sl:]


def install_SsT_backup(logger, dbname):
    # tmpdir = '/tmp/tmpa3tdk9fi'
    tmpdir = download_backup(logger)              #comment to use existing tmpdir
    process_db_file(dbname, tmpdir, logger)
    # tmpdir = '/home/don/devel/sst_backup'
    wp_install = '/var/www/html'
    process_zipped_files(tmpdir, wp_install)                    # comment to avoid installing files
    # foo = filecmp.dircmp('/var/www/html/wp-content', '/var/www/html/wp-content_OLD')
    # print_diff_files(foo)
    find_diff_tables_options('foo', 'sst')


if __name__ == '__main__':
    logger = OvernightLogger('sst_backup')
    install_SsT_backup(logger)