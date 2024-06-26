"""Methods to check and update the database files for sqlite."""

import json
import os.path
import re

from . import cm_table_info, mc


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
            schema_file += testtag
            inserts_file += testtag

        postgres_port = 5432
        if "POSTGRES_PORT" in os.environ:
            postgres_port = os.environ["POSTGRES_PORT"]

        with open(os.path.expanduser("~/.hera_mc/mc_config.json")) as f:
            config_data = json.load(f)
            db_name = config_data["default_db_name"]
            db_url = config_data["databases"][db_name]["url"]
            if self.testing:
                db_url = config_data["databases"]["testing"]["url"]

        subprocess.call(
            f"pg_dump -s -p {postgres_port} -d {db_url} > {schema_file}", shell=True
        )
        dump = (
            f"pg_dump --inserts --data-only  -p {postgres_port} -d {db_url} -t "
            "{} > {}".format(" -t ".join(self.cm_table_list), inserts_file)
        )
        subprocess.call(dump, shell=True)

        schema = ""
        creating_table = False
        with open(schema_file, "r") as f:
            lines = f.readlines()
            msg = f"Schema dump failed, schema file {schema_file} is empty. "
            assert len(lines) > 0, msg
            for line in lines:
                interline = line + ""
                if "[]" in line:
                    # want to convert any array column to a character varying column.
                    # first find the column name (must be a single word)
                    name_match = re.search(r"[\w]+", line)
                    column_name = name_match.group(0)
                    # then search after the column name for the type, which can be
                    # multiple words and ends in "[]"
                    type_match = re.search(
                        r"([a-zA-Z ]+)\[\]", line.split(column_name)[-1]
                    )
                    column_type = type_match.group(0).strip(" ")
                    interline = line.replace(column_type, "character varying")
                modline = interline.replace("public.", "")

                if "CREATE TABLE" in modline:
                    creating_table = True
                    schema += modline
                    continue
                if creating_table:
                    # The DEFAULT clause is apparently sometimes written this way and
                    # sometimes written differently (by defining the sequence and then
                    # assigning it to the column). Using a pragma because I cannot
                    # guarantee that this will be triggered.
                    if "DEFAULT" in modline:  # pragma: no cover
                        dat = modline.split()
                        schema += dat[0] + " " + dat[1] + "\n"
                    else:
                        schema += modline
                    if ");" in modline:
                        creating_table = False

        inserts = ""
        with open(inserts_file, "r") as f:
            lines = f.readlines()
            msg = f"Inserts dump failed, inserts file {inserts_file} is empty. "
            assert len(lines) > 0, msg
            for line in lines:
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
        os.remove(schema_file)
        os.remove(inserts_file)
        os.remove(sqlfile)


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
