"""Methods to check and update the database files for sqlite."""
from . import mc, cm_table_info
import os.path
import json


class SqliteHandling:
    """
    Database csv table hash info handler.

    Attributes
    ----------
    cm_csv_path : str or None
        Path containing the csv data files.  If None uses default in mc.
    cm_table_list : list of str or None
        List of files to be used in hash comparisons.  If None uses default.
    cm_table_hash_file : str
        Name of json file that archives the previous hash set.
    hash_dict : dict
        Dictionary containing the current hashes.
    testing : bool
        Flag to denote testing or not.
    """

    def __init__(
        self,
        cm_csv_path=None,
        cm_table_list=None,
        cm_table_hash_file="cm_table_file_hash.json",
        testing=False,
    ):
        """
        Initialize class by setting the class attributes to supplied or defaults.

        Parameters
        ----------
        cm_csv_path : str or None
            Path containing the csv data files.  If None uses default in mc.
        cm_table_list : list of str or None
            List of files to be used in hash comparisons.  If None uses default.
        cm_table_hash_file : str
            Name of json file that archives the previous hash set.
        testing : bool
            Flag to denote testing (sets directory and sql file generation)
        """
        if cm_csv_path is None:
            cm_csv_path = mc.get_cm_csv_path(testing=testing)
        self.cm_csv_path = cm_csv_path
        if cm_table_list is None:
            cm_table_list = cm_table_info.cm_tables.keys()
        self.cm_table_list = cm_table_list
        self.cm_table_hash_file = os.path.join(self.cm_csv_path, cm_table_hash_file)
        self.testing = testing
        self.hash_dict = None

    def different_table_hash_dict(self):
        """
        Check that the current and previous table file hashes are the different.

        Parameters
        ----------
        hash_dict : dict
            current table hash information as read from csv files
        previous_hash_file : str
            file containing previous table hash information

        Return
        ------
        bool
            True if they are the different.
        """
        if not os.path.exists(self.cm_table_hash_file):
            return True
        if self.hash_dict is None:
            self.get_table_hash_dict()
        with open(self.cm_table_hash_file, "r") as fp:
            previous_hash_dict = json.load(fp)
        if set(self.hash_dict.keys()) != set(previous_hash_dict.keys()):
            return True
        for key, val in self.hash_dict.items():
            if val != previous_hash_dict[key]:
                return True
        return False

    def get_table_hash_dict(self):
        """Compute the hash_dict for the data csv files."""
        self.hash_dict = {}
        for table in self.cm_table_list:
            fn = "{}{}.csv".format(cm_table_info.data_prefix, table)
            csv_file = os.path.join(self.cm_csv_path, fn)
            self.hash_dict[fn] = hash_file(csv_file)

    def write_table_hash_dict(self):
        """Write the hash of the csv data-files to json hash_file."""
        if self.hash_dict is None:
            self.get_table_hash_dict()
        with open(self.cm_table_hash_file, "w") as fp:
            json.dump(self.hash_dict, fp, indent=4)

    def update_sqlite(self, db_file="hera_mc.db"):
        """
        Dump the psql database to sqlite file.

        Parameter
        ---------
        table_dump_list : list of str
            List containing name of tables to dump to sqlite.
        """
        import subprocess

        schema_file = os.path.join(self.cm_csv_path, "schema.sql")
        inserts_file = os.path.join(self.cm_csv_path, "inserts.sql")
        testtag = ""
        if self.testing:
            testtag = "tst"

        subprocess.call(f"pg_dump -s hera_mc > {schema_file}{testtag}", shell=True)
        dump = "pg_dump --inserts --data-only hera_mc -t {} > {}{}".format(
            " -t ".join(self.cm_table_list), inserts_file, testtag
        )
        subprocess.call(dump, shell=True)

        schema = ""
        creating_table = False
        with open(schema_file, "r") as f:
            for line in f:
                modline = line.replace("public.", "")
                if "CREATE TABLE" in modline:
                    creating_table = True
                    schema += modline
                    continue
                if creating_table:
                    if "DEFAULT" in modline:
                        dat = modline.split()
                        schema += dat[0] + " " + dat[1] + "\n"
                    else:
                        schema += modline
                    if ");" in modline:
                        creating_table = False
        inserts = ""
        with open(inserts_file, "r") as f:
            for line in f:
                modline = line.replace("public.", "")
                if "INSERT" in modline:
                    inserts += modline

        sqlfile = os.path.join(self.cm_csv_path, "cm_hera.sql")
        dbfile_full = os.path.join(self.cm_csv_path, db_file)
        with open(sqlfile, "w") as f:
            f.write(schema)
            f.write(inserts)
            f.write(".save {}\n".format(dbfile_full))
        subprocess.call("sqlite3 < {}".format(sqlfile), shell=True)
        subprocess.call(f"rm -f {schema_file}{testtag}", shell=True)
        subprocess.call(f"rm -f {inserts_file}{testtag}", shell=True)
        subprocess.call(f"rm -f {sqlfile}", shell=True)


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
    with open(filename, "rb") as file:
        chunk = 0
        while chunk != b"":
            chunk = file.read(1024)
            h.update(chunk)
    return h.hexdigest()
