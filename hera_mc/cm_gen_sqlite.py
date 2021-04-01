"""Methods to check and update the database files for csv and sqlite."""
from . import mc, cm_table_info
import os.path

CM_CSV_PATH = mc.get_cm_csv_path(None)
CM_TABLE_LIST = cm_table_info.cm_tables.keys()
CM_TABLE_HASH_FILE = 'cm_table_file_hash.csv'


def same_table_hash_info(hash_dict, previous_hash_file=CM_TABLE_HASH_FILE):
    """
    Check that the current and previous table file hashes are the same.

    Parameters
    ----------
    hash_dict : dict
        current table hash information as read from csv files
    previous_hash_file : str
        file containing previous table hash information

    Return
    ------
    bool
        True if they are the same
    """
    previous_hash_dict = {}
    fnfp = os.path.join(CM_CSV_PATH, previous_hash_file)
    if not os.path.exists(fnfp):
        return False
    with open(fnfp, 'r') as fp:
        for line in fp:
            data = line.strip().split(',')
            if len(data) == 2:
                previous_hash_dict[data[0]] = data[1]
    current_set = set(hash_dict.keys())
    if current_set != set(previous_hash_dict.keys()):
        return False
    for key in current_set:
        if hash_dict[key] != previous_hash_dict[key]:
            return False
    return True


def get_table_hash_info(table_list=CM_TABLE_LIST):
    """
    Compute the hash_dict for the data csv files.

    Parameter
    ---------
    table_list : list
        list of tables to use

    Return
    ------
    dict
        dictionary containing hash information
    """
    hash_dict = {}
    for table in table_list:
        fn = "{}{}.csv".format(cm_table_info.data_prefix, table)
        fnfp = os.path.join(CM_CSV_PATH, fn)
        hash_dict[fn] = hash_file(fnfp)
    return hash_dict


def write_table_hash_info(hash_dict, hash_file=CM_TABLE_HASH_FILE):
    """
    Write the hash of the csv data-files to hash_file.

    Parameters
    ----------
    hash_dict : dict
        current table hash information
    hash_file : str
        file containing previous table hash information
    """
    with open(os.path.join(CM_CSV_PATH, hash_file), 'w') as fp:
        for fn, hsh in hash_dict.items():
            print("{},{}".format(fn, hsh), file=fp)


def hash_file(filename):
    """
    Compute and return the MD5 hash of the file passed into it.

    Parameter
    ---------
    filename : str
        Name of file to use to compute hash

    Return
    ------
    str
        string containing the hexdigest of the hash for the file
    """
    import hashlib
    h = hashlib.md5()
    if not os.path.exists(filename):
        return None
    with open(filename, 'rb') as file:
        chunk = 0
        while chunk != b'':
            chunk = file.read(1024)
            h.update(chunk)
    return h.hexdigest()


def update_sqlite(table_dump_list=CM_TABLE_LIST):
    """
    Dump the psql database to sqlite file.

    Parameter
    ---------
    table_dump_list : list of str
        List containing name of tables to dump to sqlite.
    """
    import subprocess

    subprocess.call('pg_dump -s hera_mc > schema.sql', shell=True)
    dump = ('pg_dump --inserts --data-only hera_mc -t {} > inserts.sql'
            .format(' -t '.join(table_dump_list)))
    subprocess.call(dump, shell=True)

    schema = ''
    creating_table = False
    with open('schema.sql', 'r') as f:
        for line in f:
            modline = line.replace('public.', '')
            if 'CREATE TABLE' in modline:
                creating_table = True
                schema += modline
                continue
            if creating_table:
                if 'DEFAULT' in modline:
                    dat = modline.split()
                    schema += (dat[0] + ' ' + dat[1] + '\n')
                else:
                    schema += modline
                if ');' in modline:
                    creating_table = False

    inserts = ''
    with open('inserts.sql', 'r') as f:
        for line in f:
            modline = line.replace('public.', '')
            if 'INSERT' in modline:
                inserts += modline

    sqlfile = os.path.join(CM_CSV_PATH, 'cm_hera.sql')
    dbfile = os.path.join(CM_CSV_PATH, 'hera_mc.db')
    with open(sqlfile, 'w') as f:
        f.write(schema)
        f.write(inserts)
        f.write(".save {}\n".format(dbfile))
    subprocess.call('sqlite3 < {}'.format(sqlfile), shell=True)

    subprocess.call('rm -f schema.sql', shell=True)
    subprocess.call('rm -f inserts.sql', shell=True)
    subprocess.call('rm -f {}'.format(sqlfile), shell=True)
