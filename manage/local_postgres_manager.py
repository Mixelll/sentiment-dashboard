import os
import subprocess
from warnings import warn


class LocalPostgresManager:
    def __init__(self, db_config, dump_restore_config_versions):
        self.db_config = db_config
        self.dump_restore_config_versions = dump_restore_config_versions

    def attach_utility_to_path(self, utility, pg_path=None):
        if not pg_path:
            pg_path = self.db_config['pg_path']
        if pg_path:
            if os.path.isdir(pg_path):
                pg_path = os.path.join(pg_path, utility + ('.exe' if os.name == 'nt' else ''))
        else:
            pg_path = utility
        return pg_path

    @staticmethod
    def rectify_command(command):
        if isinstance(command, str):
            return command
        return ' '.join([f'"{c}"' if '\\' in c else c for c in command])

    def create_temp_table(self, source_table, columns, temp_table_name, source_schema=None, temp_schema=None, port=None, pg_path=None):
        """
        Creates a temporary table locally within a specified schema.

        :param source_table: Name of the source table.
        :param columns: List of columns to include in the temporary table.
        :param temp_table_name: Name of the temporary table to create.
        :param source_schema: Schema of the source table.
        :param temp_schema: Schema of the temporary table.
        :param pg_path: Full path to the psql binary of the desired PostgreSQL version.
        :param port: Port number of the PostgreSQL server.
        """
        conn_string = self._get_conn_string(port=port)
        full_source_table = f"{source_schema}.{source_table}" if source_schema else source_table
        full_temp_table = f"{temp_schema}.{temp_table_name}" if temp_schema else temp_table_name
        sql_command = f"CREATE TABLE IF NOT EXISTS {full_temp_table} AS SELECT {', '.join(columns)} FROM {full_source_table};"

        pg_path = self.attach_utility_to_path('psql', pg_path)

        psql_command = [
            pg_path,
            '-d', conn_string,
            '-c', sql_command
        ]
        print(f"Executing command (subprocess): {self.rectify_command(psql_command)}")
        result = subprocess.run(psql_command, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.returncode == 0:
            print(f"Temporary table {full_temp_table} created with columns {columns} in schema {source_schema if source_schema else 'public'}.")
        else:
            print(f"Failed to create temporary table {full_temp_table}. Error: {result.stderr}")

    def dump_table(self, table_name, dump_file_path, schema=None, port=None, pg_path=None):
        # Ensure directory exists
        full_dump_path = os.path.join(os.getcwd(), dump_file_path)
        dump_dir = os.path.dirname(full_dump_path)
        os.makedirs(dump_dir, exist_ok=True)

        schema_option = f"-n {schema}" if schema else "-n public"
        conn_string = self._get_conn_string(port=port)
        pg_path = self.attach_utility_to_path('pg_dump', pg_path)
        dump_command = f'"{pg_path}" {schema_option} -d {conn_string} -t {table_name} -Fc -f {full_dump_path}'
        # dump_command = [
        #     pg_path,
        #     schema_option,
        #     "-d", conn_string,
        #     "-t", table_name,
        #     "-Fc",
        #     "-f", full_dump_path
        # ]

        # Execute the command without using shell=True for better security
        print(f"Executing command (subprocess): {self.rectify_command(dump_command)}")
        try:
            result = subprocess.run(dump_command, shell=True, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to dump table {table_name}. Error: {e.stderr}")

        print(f"Table {table_name} dumped from schema {schema if schema else 'public'} to {full_dump_path}.")
        print("STDOUT:", result.stdout)
        return full_dump_path

    def restore_table(self, dump_file_path, port, pg_path=None):
        """
        Restores a table from a dump file to a database using a specified port and optional specific PostgreSQL binary.

        :param dump_file_path: Path to the dump file.
        :param port: Port number of the PostgreSQL server where the table will be restored.
        :param pg_path: Full path to the pg_restore binary of the desired PostgreSQL version. If not provided, 'pg_restore' is assumed to be in the PATH.
        """
        conn_string = self._get_conn_string(port=port)
        pg_path = self.attach_utility_to_path('pg_restore', pg_path)

        restore_command = [
            pg_path,
            "-d", conn_string,
            "-c",  # Clean restore option to drop database objects before recreating them
            dump_file_path
        ]

        print(f"Executing command (subprocess): {self.rectify_command(restore_command)}")
        try:
            subprocess.run(restore_command, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            if "Command was: DROP TABLE" in e.stderr:
                warn("Attemtping to drop non-existent table. Continuing...")
            else:
                raise Exception(f"Failed to restore table. Error: {e.stderr}")

        print(f"Table restored to {self.db_config['dbname']} on port {port}.")

    def pg_dump_restore_between_versions(self, table_name, schema=None, source_port=None, target_port=None):
        ver_config = self.dump_restore_config_versions
        source_port = source_port if source_port else ver_config['source_port']
        target_port = target_port if target_port else ver_config['target_port']
        if not source_port or not target_port:
            print("Source and target ports must be provided for pg_dump_restore_between_versions.")
            return {}
        if source_port == target_port:
            print("Source and target ports must be different for pg_dump_restore_between_versions.")
            return {}
        pg_path = self.dump_restore_config_versions['pg_path']
        dump_file_path = fr"tmp\{table_name}_version_switch.dump"
        dumped_path = self.dump_table(table_name, dump_file_path, schema=schema, port=source_port, pg_path=pg_path)
        self.restore_table(dumped_path, port=target_port, pg_path=pg_path)
        return {'port': target_port, 'pg_path': ver_config['output_pg_path']}

    def _get_conn_string(self, port=None):
        if port:
            port_option = f":{port}"
        elif not port and 'port' in self.db_config:
            port_option = f":{self.db_config['port']}"
        else:
            port_option = ''

        return f"postgresql://{self.db_config['user']}:{self.db_config['password']}@{self.db_config['host']}{port_option}/{self.db_config['dbname']}"
