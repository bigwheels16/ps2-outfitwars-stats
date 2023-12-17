import logging
from pkg_resources import parse_version
import re
import os
import time
import sqlalchemy
from google.cloud.sql.connector import Connector, IPTypes


class DB:
    def __init__(self):
        self.lastrowid = None
        self.logger = logging.getLogger(__name__)
        self.engine = None

    def connect(self, drivername, username, password, database, host, ip_type):
        if ":" in host:
            # https://github.com/GoogleCloudPlatform/cloud-sql-python-connector#how-to-use-this-connector
            # https://github.com/GoogleCloudPlatform/python-docs-samples/blob/main/cloud-sql/postgres/sqlalchemy/connect_connector_auto_iam_authn.py
            connector = Connector()

            enable_iam_auth = "@" in username

            def get_conn():
                conn = connector.connect(
                    host,
                    drivername,
                    user=username,
                    password=None if enable_iam_auth else password,
                    db=database,
                    ip_type=IPTypes[ip_type],
                    timeout=5,
                    enable_iam_auth=enable_iam_auth,
                )
                return conn

            self.engine = sqlalchemy.create_engine(
                f"postgresql+{drivername}://",
                creator=get_conn,
                # Pool size is the maximum number of permanent connections to keep.
                pool_size=5,
                # Temporarily exceeds the set pool_size if no connections are available.
                max_overflow=2,
                # The total number of concurrent connections for your application will be
                # a total of pool_size and max_overflow.
                # 'pool_timeout' is the maximum number of seconds to wait when retrieving a
                # new connection from the pool. After the specified amount of time, an
                # exception will be thrown.
                pool_timeout=5,  # 30 seconds
                # 'pool_recycle' is the maximum number of seconds a connection can persist.
                # Connections that live longer than the specified amount of time will be
                # re-established
                pool_recycle=1800,  # 30 minutes
                isolation_level = "AUTOCOMMIT",
            )
        else:
            self.engine = sqlalchemy.create_engine(
                sqlalchemy.engine.url.URL.create(
                    drivername=f"postgresql+{drivername}",
                    username=username,
                    password=password,
                    host=host,
                    port=5432,
                    database=database,
                ),
                # Pool size is the maximum number of permanent connections to keep.
                pool_size=5,
                # Temporarily exceeds the set pool_size if no connections are available.
                max_overflow=2,
                # The total number of concurrent connections for your application will be
                # a total of pool_size and max_overflow.
                # 'pool_timeout' is the maximum number of seconds to wait when retrieving a
                # new connection from the pool. After the specified amount of time, an
                # exception will be thrown.
                pool_timeout=5,  # 30 seconds
                # 'pool_recycle' is the maximum number of seconds a connection can persist.
                # Connections that live longer than the specified amount of time will be
                # re-established
                pool_recycle=1800,  # 30 minutes
                isolation_level = "AUTOCOMMIT",
            )

    def _execute_wrapper(self, db_conn, sql, params, callback):
        if db_conn:
            result = self._execute_query(db_conn, sql, params, callback)
        else:
            with self.get_connection() as db_conn:
                result = self._execute_query(db_conn, sql, params, callback)
                
        if callback:
            result = callback(result)

        return result

    def _execute_query(self, db_conn, sql, params, callback):
        start_time = time.time()
        try:
            result = db_conn.execute(sqlalchemy.text(sql), params)
        except Exception as e:
            raise SqlException("SQL Error: '%s' for '%s' [%s]" % (str(e), sql, params)) from e

        elapsed = time.time() - start_time

        if elapsed > 0.5:
            self.logger.warning("slow query (%fs) '%s' for params: %s" % (elapsed, sql, str(params)))

        return result

    def query_single(self, sql, params=None, db_conn=None):
        if params is None:
            params = []

        def map_result(result):
            return result.mappings().first()

        return self._execute_wrapper(db_conn, sql, params, map_result)

    def query(self, sql, params=None, db_conn=None):
        if params is None:
            params = []

        def map_result(result):
            return result.mappings().all()

        return self._execute_wrapper(db_conn, sql, params, map_result)

    def exec(self, sql, params=None, db_conn=None):
        if params is None:
            params = []

        def map_result(result):
            return result.rowcount

        row_count = self._execute_wrapper(db_conn, sql, params, map_result)
        return row_count

    def last_insert_id(self):
        return self.lastrowid

    def verify_connection(self):
        with self.get_connection_wrapper() as conn:
            self._execute_wrapper(conn, "SELECT 1", [], None)

    def get_connection_wrapper(self):
        return SqlConnectionWrapper(self.get_connection())

    def get_connection(self):
        return self.engine.connect()
        
    def table_exists(self, table_name):
        sql = "SELECT EXISTS ( SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = :table_name ) AS table_exists;"
        row = self.query_single(sql, {"table_name": table_name})
        return row.table_exists


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
