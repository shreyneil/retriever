"""Database Toolkit tools
Functions to create a database from a delimited text file.

Supported database engines: MySQL, PostgreSQL, SQLite

Usage: python dbtk_ernest2003.py [-e engine (mysql, postgresql, etc.)] [--engine=engine]
                                 [-u username] [--user=username] 
                                 [-p password] [--password=password]
                                 [-h {hostname} (default=localhost)] [--host=hostname] 
                                 [-o {port}] [--port=port]
                                 [-d {databasename}] [--db=databasename]

db variables:
    dbname - the name to use for the new database. If it exists, it will be dropped.
    drop - if the database already exists, should it be dropped?     
    opts - list of variables supplied from command line arguments or manually input
    engine - specifies the database engine (MySQL, PostgreSQL, etc.)    

table variables:
    tablename - the name to use for the new table.
    drop - if the table already exists, should it be dropped?
    pk - the name of the value to be used as primary key. If None, no primary key will
         be used. The primary key must be the first column in dbcolumns.
    hasindex - True if the database file already includes an index
    record_id - the number of rows already entered into a table
    source - the open file or url containing the data
    delimiter - the delimiter used in the text file. If None, whitespace will be assumed.
    header_rows - number of header rows to be skipped
    cleanup - the name of the cleanup function to be used (or no_cleanup for none)
    dbcolumns - a list of tuples, containing each column name and its data type.
                The number of values in each row of the text file must correspond with
                the number of columns defined.
                Data type is also a tuple, with the first value specifying the type.
                (The second part of the type specifies the length and is optional)
                    pk      - primary key
                    int     - integer
                    double  - double precision
                    char    - string
                    bit     - binary
                    skip    - ignore this row
                    combine - append this row's data to the data of the previous row 
"""

import getpass
import getopt
import urllib
import warnings
import os
import sys

warnings.filterwarnings("ignore")

def no_cleanup(value):
    """Default cleanup function, returns the unchanged value"""
    return value 

class Database:
    """Information about database to be passed to dbtk_tools.create_table"""
    dbname = ""
    drop = True
    opts = dict()
    
class Table:
    """Information about table to be passed to dbtk_tools.create_table"""
    tablename = ""
    pk = None
    hasindex = False
    record_id = 0
    lines = []
    delimiter = None
    columns = []
    drop = True
    header_rows = 1
    cleanup = no_cleanup
    nullindicators = set(["-999", "-999.00", -999])
    
class Engine():
    name = ""
    def add_to_table(self):
        print "Inserting rows: "
    
        for line in self.table.source:
            
            line = line.strip()
            if line:
                self.table.record_id += 1            
                linevalues = []
                if (self.table.pk and self.table.hasindex == False):
                    column = 0
                else:
                    column = -1
                 
                for value in line.split(self.table.delimiter):
                    column += 1
                    thiscolumn = self.table.columns[column][1][0]
                    # If data type is "skip" ignore the value
                    if thiscolumn == "skip":
                        pass
                    elif thiscolumn == "combine":
                        # If "combine" append value to end of previous column
                        linevalues[len(linevalues) - 1] += " " + value 
                    else:
                        # Otherwise, add new value
                        linevalues.append(value) 
                            
                # Build insert statement with the correct # of values                
                cleanvalues = [self.format_insert_value(self.table.cleanup(value, self)) for value in linevalues]
                insertstatement = self.insert_statement(cleanvalues)
                print insertstatement 
                self.cursor.execute(insertstatement)
                
        print "\n Done!"
        self.connection.commit()
        self.table.source.close()    
    def convert_data_type(self, datatype):
        """Converts DBTK generic data types to db engine specific data types"""
        datatypes = dict()
        datatypes["pk"], datatypes["int"], datatypes["double"], datatypes["char"], datatypes["bit"] = range(5)
        datatypes["combine"], datatypes["skip"] = [-1, -1]        
        mydatatypes = self.datatypes
        thisvartype = datatypes[datatype[0]]
        if thisvartype > -1:
            type = mydatatypes[thisvartype]
            if len(datatype) > 1:
                type += "(" + str(datatype[1]) + ")"
        else:
            type = ""    
        return type    
    def create_db(self):
        """Creates a database based on settings supplied in db object"""
        print "Creating database " + self.db.dbname + " . . ."
        # Create the database    
        self.cursor.execute(self.create_db_statement())
    def create_db_statement(self):
        if self.db.drop:
            self.cursor.execute(self.drop_statement("DATABASE", self.db.dbname))
            createstatement = "CREATE DATABASE " + self.db.dbname
        else:
            createstatement = "CREATE DATABASE IF NOT EXISTS " + db.dbname
        return createstatement
    def create_table(self):
        createstatement = self.create_table_statement()
        print "Creating table " + self.table.tablename + " in database " + self.db.dbname + " . . ."
        self.cursor.execute(createstatement)
    def create_table_statement(self):
        if self.table.drop:
            self.cursor.execute(self.drop_statement("TABLE", self.tablename()))
            createstatement = "CREATE TABLE " + self.tablename() + " ("
        else:
            createstatement = "CREATE TABLE IF NOT EXISTS " + self.tablename() + " ("    
        for item in self.table.columns:
            if (item[1][0] != "skip") and (item[1][0] != "combine"):
                createstatement += item[0] + " " + self.convert_data_type(item[1]) + ", "    

        createstatement = createstatement.rstrip(', ')    
        createstatement += " );"
        return createstatement
    def drop_statement(self, objecttype, objectname):
        dropstatement = "DROP %s IF EXISTS %s" % (objecttype, objectname)
        return dropstatement
    def format_insert_value(self, value):
        if value:
            return "'" + str(value) + "'"
        else:
            return "null"    
    def get_insert_columns(self, join=True):
        columns = ""
        for item in self.table.columns:
            if (item[1][0] != "skip") and (item[1][0] !="combine") and (item[1][0] != 
                                                    "pk" or self.table.hasindex == True):
                columns += item[0] + ", "            
        columns = columns.rstrip(', ')
        if join:
            return columns
        else:
            return columns.lstrip("(").rstrip(")").split(", ")
    def insert_data_from_file(self, filename):
        self.table.source = self.skip_rows(self.table.header_rows, open(filename, "r"))
        self.add_to_table()        
    def insert_statement(self, values):
        columns = self.get_insert_columns()
        columncount = len(self.get_insert_columns(False))
        insertstatement = "INSERT INTO " + self.tablename()
        insertstatement += " (" + columns + ")"  
        insertstatement += " VALUES ("
        for i in range(0, columncount):
            insertstatement += "%s, "
        insertstatement = insertstatement.rstrip(", ") + ");"
        sys.stdout.write(str(self.table.record_id) + "\b" * len(str(self.table.record_id)))
        # Run correct_invalid_value on each value before insertion
        insertstatement %= tuple(values)
        return insertstatement
    def open_url(self, url):
        """Returns an opened file from a URL, skipping the header lines"""
        source = self.skip_rows(self.table.header_rows, urllib.urlopen(url))
        return source    
    def skip_rows(self, rows, source):
        """Skip over the header lines by reading them before processing"""
        if rows > 0:
            for i in range(rows):
                line = source.readline()
        return source
    def tablename(self):        
        return self.db.dbname + "." + self.table.tablename
    def connection(self):
        pass
    def cursor(self):
        pass


class MySQLEngine(Engine):
    name = "mysql"
    datatypes = ["INT(5) NOT NULL AUTO_INCREMENT", 
                 "INT", 
                 "DOUBLE", 
                 "VARCHAR", 
                 "BIT"]
    def create_table_statement(self):
        createstatement = Engine.create_table_statement(self)
        if self.table.pk:
            createstatement = createstatement.rstrip(");")
            createstatement += ", PRIMARY KEY (" + self.table.pk + ") )"
        return createstatement
    def insert_data_from_file(self, filename):
        print "Inserting data from " + filename + " . . ."
            
        columns = self.get_insert_columns()            
        statement = """        
LOAD DATA LOCAL INFILE '""" + filename + """'
INTO TABLE """ + self.tablename() + """
FIELDS TERMINATED BY ','
LINES TERMINATED BY '\\n'
IGNORE 1 LINES 
(""" + columns + ")"
        
        self.cursor.execute(statement)        
    
    def get_cursor(self):
        import MySQLdb as dbapi
                        
        # If any parameters are missing, input them manually
        if self.opts["username"] == "":
            self.opts["username"] = raw_input("Enter your MySQL username: ")
        if self.opts["password"] == "":
            print "Enter your MySQL password: "
            self.opts["password"] = getpass.getpass(" ")
        if self.opts["hostname"] == "":
            self.opts["hostname"] = raw_input("Enter your MySQL host or press Enter for the default (localhost): ")
        if self.opts["sqlport"] == "":
            self.opts["sqlport"] = raw_input("Enter your MySQL port or press Enter for the default (3306): ")
            
        # Set defaults
        if self.opts["hostname"] in ["", "default"]:
            self.opts["hostname"] = "localhost"
        if self.opts["sqlport"] in ["", "default"]:
            self.opts["sqlport"] = "3306"        
        self.opts["sqlport"] = int(self.opts["sqlport"])
            
        # Connect to database
        self.connection = dbapi.connect(host = self.opts["hostname"],
                                        port = self.opts["sqlport"],
                                        user = self.opts["username"],
                                        passwd = self.opts["password"])     
        self.cursor = self.connection.cursor()    


class PostgreSQLEngine(Engine):
    name = "postgresql"
    datatypes = ["SERIAL PRIMARY KEY", 
                 "integer", 
                 "double precision", 
                 "varchar", 
                 "bit"]    
    def create_db_statement(self):
        """Creates a schema based on settings supplied in db object"""
        return Engine.create_db_statement(self).replace(" DATABASE ", " SCHEMA ")
    def drop_statement(self, objecttype, objectname):
        dropstatement = Engine.drop_statement(self, objecttype, objectname) + " CASCADE;"
        return dropstatement.replace(" DATABASE ", " SCHEMA ")
    def insert_data_from_file(self, filename):
        print "Inserting data from " + filename + " . . ."
            
        columns = self.get_insert_columns()    
        filename = os.path.abspath(filename)
        statement = """
COPY """ + self.tablename() + " (" + columns + """)
FROM '""" + filename + """'
WITH DELIMITER ','
CSV HEADER"""
        self.cursor.execute(statement)
        self.connection.commit()        
    def get_cursor(self):
        import psycopg2 as dbapi    
        
        # If any parameters are missing, input them manually
        if self.opts["username"] == "":
            self.opts["username"] = raw_input("Enter your PostgreSQL username: ")
        if self.opts["password"] == "":
            print "Enter your PostgreSQL password: "
            self.opts["password"] = getpass.getpass(" ")
        if self.opts["hostname"] == "":
            self.opts["hostname"] = raw_input("Enter your PostgreSQL host or press Enter for the default (localhost): ")
        if self.opts["sqlport"] == "":
            self.opts["sqlport"] = raw_input("Enter your PostgreSQL port or press Enter for the default (5432): ")
        if self.opts["database"] == "":
            self.opts["database"] = raw_input("Enter your PostgreSQL database name or press Enter for the default (postgres): ")
        
        # Set defaults
        if self.opts["hostname"] in ["", "default"]:
            self.opts["hostname"] = "localhost"
        if self.opts["sqlport"] in ["", "default"]:
            self.opts["sqlport"] = "5432"        
        self.opts["sqlport"] = int(self.opts["sqlport"])
        if self.opts["database"] in ["", "default"]:
            self.opts["database"] = "postgres"
            
        # Connect to database
        self.connection = dbapi.connect(host = self.opts["hostname"],
                                        port = self.opts["sqlport"],
                                        user = self.opts["username"],
                                        password = self.opts["password"],
                                        database = self.opts["database"])        
        self.cursor = self.connection.cursor()    


class SQLiteEngine(Engine):
    name = "sqlite"
    datatypes = ["INTEGER PRIMARY KEY",
                 "INTEGER",
                 "REAL",
                 "TEXT",
                 "INTEGER"]
    def create_db(self):
        return None
    def tablename(self):        
        return "'" + self.table.tablename + "'"    
    def get_cursor(self):
        import sqlite3 as dbapi    
            
        # If any parameters are missing, input them manually
        if self.opts["database"] == "":
            self.opts["database"] = raw_input("Enter the filename of your SQLite database: ")
        
        # Set defaults
        if self.opts["database"] in ["", "default"]:
            self.opts["database"] = "sqlite.db"        
        
        # Connect to database
        self.connection = dbapi.connect(self.opts["database"])
        self.cursor = self.connection.cursor()               


def get_opts():
    """Checks for command line arguments"""
    optsdict = dict()
    for i in ["engine", "username", "password", "hostname", "sqlport", "database"]:
        optsdict[i] = ""
    try:
        opts, args = getopt.getopt(sys.argv[1:], "e:u:p:hod", ["engine=", "user=", "password=", "host=", "port=", "database="])        
        for opt, arg in opts:            
            if opt in ("-e", "--engine"):      
                optsdict["engine"] = arg                            
            if opt in ("-u", "--user"):      
                optsdict["username"] = arg                            
            elif opt in ("-p", "--password"):     
                optsdict["password"] = arg
            elif opt in ("-h", "--host"):                 
                if arg == "":
                    optsdict["hostname"] = "default"
                else:
                    optsdict["hostname"] = arg
            elif opt in ("-o", "--port"): 
                try:
                    optsdict["sqlport"] = int(arg)
                except ValueError:
                    optsdict["sqlport"] = "default"                 
            elif opt in ("-d", "--database"): 
                if arg == "":
                    optsdict["database"] = "default"
                else:
                    optsdict["database"] = arg                                 
                 
    except getopt.GetoptError:
        pass
    
    return optsdict   


def choose_engine(opts):
    """Prompts the user to select a database engine"""    
    engine = opts["engine"]
    
    if engine == "":
        print "Choose a database engine:"
        print "    (m) MySQL"
        print "    (p) PostgreSQL"
        print "    (s) SQLite"
        engine = raw_input(": ")
        engine = engine.lower()
    
    if engine == "mysql" or engine == "m" or engine == "":
        return MySQLEngine()
    elif engine == "postgresql" or engine == "p":
        return PostgreSQLEngine()
    elif engine == "sqlite" or engine == "s":
        return SQLiteEngine()