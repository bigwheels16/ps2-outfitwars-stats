import logging
from pkg_resources import parse_version
import mysql.connector
import sqlite3
import re
import os
import time
import sqlalchemy.pool as pool
from sqlalchemy.dialects.mysql import mysqlconnector


class DB:
    SQLITE = "sqlite"
    MYSQL = "mysql"

    def __init__(self):
        self.enhanced_like_regex = re.compile(r"(\s+)(\S+)\s+<EXTENDED_LIKE=(\d+)>\s+\?(\s*)", re.IGNORECASE)
        self.lastrowid = None
        self.logger = logging.getLogger(__name__)
        self.type = None
        self.pool = None

    def sqlite_row_factory(self, cursor: sqlite3.Cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    def connect_mysql(self, host, port, username, password, database_name):
        def connect():
            conn = mysql.connector.connect(user=username, password=password, host=host, port=port, database=database_name, charset="utf8", autocommit=True)
            self._execute_wrapper(conn, "SET collation_connection = 'utf8_general_ci'", [], None)
            self._execute_wrapper(conn, "SET sql_mode = 'TRADITIONAL,ANSI'", [], None)
            return conn

        self.type = self.MYSQL

        # https://docs.sqlalchemy.org/en/14/core/pooling.html
        # https://docs.sqlalchemy.org/en/14/dialects/mysql.html
        self.pool = pool.QueuePool(connect, max_overflow=10, pool_size=5, dialect=mysqlconnector.dialect(dbapi=mysqlconnector.dialect.dbapi()), pre_ping=True)
        self.create_db_version_table()

    def connect_sqlite(self, filename):
        def connect():
            conn = sqlite3.connect(filename, isolation_level=None, check_same_thread=False)
            conn.row_factory = self.sqlite_row_factory
            return conn

        self.type = self.SQLITE

        self.pool = pool.QueuePool(connect, max_overflow=0, pool_size=1)
        self.create_db_version_table()

    def create_db_version_table(self):
        self.exec("CREATE TABLE IF NOT EXISTS db_version (file VARCHAR(255) NOT NULL, version VARCHAR(255) NOT NULL, verified SMALLINT NOT NULL)")

    def _execute_wrapper(self, db_conn, sql, params, callback):
        if db_conn:
            return self._execute_query(db_conn, sql, params, callback)
        else:
            with self.get_connection_wrapper() as db_conn:
                return self._execute_query(db_conn, sql, params, callback)

    def _execute_query(self, db_conn, sql, params, callback):
        if self.type == self.MYSQL:
            # buffered=True - https://stackoverflow.com/a/33632767/280574
            cur = db_conn.cursor(dictionary=True, buffered=True)
        else:
            cur = db_conn.cursor()

        start_time = time.time()
        try:
            cur.execute(sql if self.type == self.SQLITE else sql.replace("?", "%s"), params)
        except Exception as e:
            raise SqlException("SQL Error: '%s' for '%s' [%s]" % (str(e), sql, ", ".join(map(lambda x: str(x), params)))) from e

        elapsed = time.time() - start_time

        #if elapsed > 0.5:
        #    self.logger.warning("slow query (%fs) '%s' for params: %s" % (elapsed, sql, str(params)))

        if callback:
            result = callback(cur)
        else:
            result = None

        cur.close()

        return result

    def query_single(self, sql, params=None, extended_like=False, db_conn=None):
        if params is None:
            params = []

        if extended_like:
            sql, params = self.handle_extended_like(sql, params)

        sql, params = self.format_sql(sql, params)

        def map_result(cur):
            row = cur.fetchone()
            return row

        return self._execute_wrapper(db_conn, sql, params, map_result)

    def query(self, sql, params=None, extended_like=False, db_conn=None):
        if params is None:
            params = []

        if extended_like:
            sql, params = self.handle_extended_like(sql, params)

        sql, params = self.format_sql(sql, params)

        def map_result(cur):
            return cur.fetchall()

        return self._execute_wrapper(db_conn, sql, params, map_result)

    def exec(self, sql, params=None, extended_like=False, db_conn=None):
        if params is None:
            params = []

        if extended_like:
            sql, params = self.handle_extended_like(sql, params)

        sql, params = self.format_sql(sql, params)

        def map_result(cur):
            return [cur.rowcount, cur.lastrowid]

        row_count, last_row_id = self._execute_wrapper(db_conn, sql, params, map_result)
        self.last_row_id = last_row_id
        return row_count, last_row_id

    def last_insert_id(self):
        return self.lastrowid

    def format_sql(self, sql, params=None):
        if self.type == self.SQLITE:
            sql = sql.replace("AUTO_INCREMENT", "AUTOINCREMENT")
            sql = sql.replace(" INT ", " INTEGER ")
            sql = sql.replace("INSERT IGNORE", "INSERT OR IGNORE")

        return sql, params

    def handle_extended_like(self, sql, params):
        original_params = params.copy()
        params = list(map(lambda x: [x], params))

        for match in self.enhanced_like_regex.finditer(sql):
            field = match.group(2)
            index = int(match.group(3))

            extra_sql, vals = self._get_extended_params(field, original_params[index].split(" "))

            sql = self.enhanced_like_regex.sub(match.group(1) + "(" + " AND ".join(extra_sql) + ")" + match.group(4), sql, 1)

            # remove current param and add generated params in its place
            del params[index]
            params.insert(index, vals)

        return sql, [item for sublist in params for item in sublist]

    def _get_extended_params(self, field, params):
        extra_sql = []
        vals = []
        for p in params:
            if p.startswith("-") and p != "-":
                vals.append("%" + p[1:] + "%")
                extra_sql.append(field + " NOT LIKE ?")
            else:
                vals.append("%" + p + "%")
                extra_sql.append(field + " LIKE ?")
        return extra_sql, vals

    def load_sql_file(self, sqlfile, force_update=False):
        filename = sqlfile.replace("/", os.sep)

        db_version = self.get_db_version(filename)
        file_version = self.get_file_version(filename)

        if db_version:
            if parse_version(file_version) > parse_version(db_version) or force_update:
                self.logger.info(f"Updating sql file '{sqlfile}' to version '{file_version}'")
                self._load_file(filename)
            self.exec("UPDATE db_version SET version = ?, verified = 1 WHERE file = ?", [int(file_version), filename])
        else:
            self.logger.info(f"Adding sql file '{sqlfile}' with version '{file_version}'")
            self._load_file(filename)
            self.exec("INSERT INTO db_version (file, version, verified) VALUES (?, ?, 1)", [filename, int(file_version)])

    def get_file_version(self, filename):
        return str(int(os.path.getmtime(filename)))

    def get_db_version(self, filename):
        row = self.query_single("SELECT version FROM db_version WHERE file = ?", [filename])
        if row:
            return row.version
        else:
            return None

    def get_type(self):
        return self.type

    def verify_connection(self):
        with self.get_connection_wrapper() as conn:
            self._execute_wrapper(conn, "SELECT 1", [], None)

    def get_connection_wrapper(self):
        return SqlConnectionWrapper(self.get_connection())

    def get_connection(self):
        return self.pool.connect()


class SqlException(Exception):
    def __init__(self, message):
        super().__init__(message)


class SqlConnectionWrapper:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        # called when exiting `with` code block
        # if exc_type, exc_val or exc_tb is not None, there was an exception
        # otherwise the code block exited normally
        self.conn.close()

        # False here indicates that if there was an exception, it should not be suppressed but instead propagated
        return False
