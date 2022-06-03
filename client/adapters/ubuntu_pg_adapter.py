import os
import time
import datetime
import subprocess
import sys
import platform
from threading import Timer
import logging
from TuningError import TuningError
from adapters.adapter import Adapter
from adapters.utility import ensure_dir

LOG_LEVEL = os.getenv("PGTUNE_LOGGING", "NONE")
VERBOSE = "VERBOSE"

PG_CONFIG_UNITS = {
            "shared_buffers": "kB",
            "work_mem": "kB",
            "random_page_cost": "",
            "effective_io_concurrency": "",
            "max_wal_size": "kB",
            "max_parallel_workers_per_gather": "",
            "max_parallel_workers": "",
            "max_worker_processes": "",
            "checkpoint_completion_target": "",
            "checkpoint_timeout": "min",
            "bgwriter_lru_maxpages":""
        }

def get_connect():
    p1 = subprocess.Popen(["pg_isready"],stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    command_output, _ = p1.communicate()
    logging.debug(command_output.decode('ascii').strip())
    return p1.returncode

def wait_for_postgres_ready_for_connect():
    logging.info("UbuntuPgAdapter: Waiting for connect...")
    state = get_connect()
    while not state == 0 and not state == 2:
        print('.', end='', flush=True)
        time.sleep(1)
    return state

def total_mem():
    try:
        if platform.system() == "Windows":
            mem = Win32Memory()
        elif platform.system() == "Darwin":
            # Least ugly way to find the amount of RAM on OS X, tested on
            # 10.6
            cmd = 'sysctl hw.memsize'
            p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT,
                      close_fds=True)
            output = p.stdout.read()
            m = re.match(r'^hw.memsize[:=]\s*(\d+)$', output.strip())
            if m and m.groups():
                mem = int(m.groups()[0])
        else:
            # Should work on other, more UNIX-ish platforms
            physPages = os.sysconf("SC_PHYS_PAGES")
            pageSize = os.sysconf("SC_PAGE_SIZE")
            mem = physPages * pageSize
        return mem
    except:
        return None

def cpu_count():
    """
    Estimate CPU count from various probes
    """
    try:
        # Prefer online processor count sysconf if that's available.
        # Of course (sigh) there are two ways the parameter is commonly spelled.
        if hasattr(os, 'sysconf') and 'SC_NPROCESSORS_ONLN' in os.sysconf_names:
            return int(os.sysconf('SC_NPROCESSORS_ONLN'))
        if hasattr(os, 'sysconf') and '_SC_NPROCESSORS_ONLN' in os.sysconf_names:
            return int(os.sysconf('_SC_NPROCESSORS_ONLN'))

        # TODO Does the above work on FreeBSD, or should we spawn `sysctl hw.ncpu`?

        try:
            # All but ancient <2.6 Python have multiprocessing
            import multiprocessing
            return multiprocessing.cpu_count()
        except:
            # Windows may (should?) have 'NUMBER_OF_PROCESSORS
            #  environment variable
            if 'NUMBER_OF_PROCESSORS' in os.environ:
                return int(os.environ['NUMBER_OF_PROCESSORS'])
    except Exception as e:
        logging.error("Exception detecting CPU count:", e)
    return None


class UbuntuPgAdapter(Adapter):
    def __init__(self, adapter_data):
        self.pg_stats = None
        self.bestPointFound = None
        self.MODE = "pre-tuning"
        logging.info("Initiating UbuntuPgAdapter")
        if {"PORT"} <= adapter_data.keys():
            os.environ["PGPORT"] = adapter_data["PORT"]

        self.PASSWORD_AUTH = False
        if {"PASSWORD"} <= adapter_data.keys():
            os.environ["PGPASSWORD"] = adapter_data["PASSWORD"]
            self.PASSWORD_AUTH = True

        self.USERNAME = adapter_data["USERNAME"]
        self.DATABASE_NAME = adapter_data["DATABASE_NAME"]

        self.ALLOW_RESTART = adapter_data["ALLOW_RESTART"]
        self.OPTIMIZATION_OBJECTIVE = adapter_data["OPTIMIZATION_OBJECTIVE"]

        try:
            state = get_connect()
            while not state == 0:
                if state == 2:
                    self.abort()
            postgres_server_version = self.psql("-c \"show server_version;\"").readlines()[2].split(' ')[1]
            postgres_major_version = postgres_server_version.split('.')[0]
            postgres_client_version = self.psql("-V").read().split(' ')[2]
            self.db_version = postgres_server_version

            self.memory = total_mem()
            self.no_of_cpu = cpu_count()
            client_info_log_list = ["Hardware and DBMS information:"]
            client_info_log_list.append('No of CPU(s): '+ str(self.no_of_cpu))
            client_info_log_list.append('Memory: ' + "%.2f" %(self.memory/1024**3) + 'GB')
            client_info_log_list.append('PostgreSQL-major-version:'+ postgres_major_version)
            client_info_log_list.append('PostgreSQL-client-version:'+ postgres_client_version)
            client_info_log_list.append('PostgreSQL-server-version:'+ postgres_server_version)
            logging.info('\n'.join(client_info_log_list))
            if int(float(self.db_version)) > 12:
                self.pg_stat_col = "total_exec_time"
            else:
                self.pg_stat_col = "total_time"

            self.WARMUP_TIME = 0
            if {"WARMUP_TIME"} <= adapter_data.keys():
                self.WARMUP_TIME = adapter_data["WARMUP_TIME"]
            self.WHO = "main"
            if {"WHO"} <= adapter_data.keys():
                self.WHO = adapter_data["WHO"]
        except TuningError as e:
            postgres_major_version = 0
            self.CONF_PATH = "/etc/postgresql/{}/{}}/".format(postgres_major_version, self.WHO)
            while postgres_major_version < 15 and not os.path.isdir(self.CONF_PATH):
                postgres_major_version += 1
                self.CONF_PATH = "/etc/postgresql/{}/{}/".format(postgres_major_version, self.WHO)
            self.CONF_OVERRIDE_PATH = self.CONF_PATH + "conf.d/"
            ensure_dir(self.CONF_OVERRIDE_PATH)

            self.CONF_OVERRIDE_FILE = self.CONF_OVERRIDE_PATH + "99_dbtune.conf"
            self.CONF_OVERRIDE_FILE_PG_STATS = self.CONF_OVERRIDE_PATH + "99_dbtune_pg_stats.conf"
            os.system('touch ' + self.CONF_OVERRIDE_FILE)
            self.abort()
        self.CONF_PATH = "/etc/postgresql/{}/{}/".format(postgres_major_version, self.WHO)
        if not os.path.isdir(self.CONF_PATH):
            logging.error("Can't locate postgres main directory {}".format(self.CONF_PATH))
            raise

        self.CONF_OVERRIDE_PATH = self.CONF_PATH + "conf.d/"
        ensure_dir(self.CONF_OVERRIDE_PATH)
        self.CONF_OVERRIDE_FILE_PG_STATS = self.CONF_OVERRIDE_PATH + "99_dbtune_pg_stats.conf"
        if self.OPTIMIZATION_OBJECTIVE == "Latency":
            self.check_and_enable_pg_stat_statement()

        self.CONF_OVERRIDE_FILE = self.CONF_OVERRIDE_PATH + "99_dbtune.conf"
        os.system('touch ' + self.CONF_OVERRIDE_FILE)

        self.BASE_CONF_FILE = self.CONF_PATH + "postgresql.conf"
        if not os.path.exists(self.BASE_CONF_FILE):
            logging.error("Can't locate postgresql.conf: {}".format(self.BASE_CONF_FILE))
            raise

        self.LOG_PATH = "/var/log/postgresql/postgresql-{}-main.log".format(postgres_major_version)
        if not os.path.exists(self.LOG_PATH):
            logging.error("Can't locate postgresql log file: {}".format(self.LOG_PATH))
            raise

        self.units = PG_CONFIG_UNITS
        logging.info("End of initiating UbuntuPgAdapter")

    def get_xact_commit(self):
        output = self.psql("-c \"SELECT xact_commit FROM pg_stat_database WHERE datname='{}';\"".format(self.DATABASE_NAME)).read()
        try:
            commit = int(output.split('\n')[2].strip())
        except ValueError:
            logging.warning("Couldn't find anything in xaxt_commit")
            logging.warning("Defaulting to 0")
            commit = 0
        return commit


    def wait_for_commits(self):
        start_commit = end_commit = self.get_xact_commit()
        logging.info("Waiting for commits...")
        print(start_commit)
        while end_commit - start_commit < 100:
            #print('.', end='', flush=True)
            print(end_commit)
            time.sleep(1)
            end_commit = self.get_xact_commit()
        print(".")

    def check_and_enable_pg_stat_statement(self):
        existsLines = self.psql("-c \"SELECT name, setting FROM pg_settings WHERE name LIKE 'shared_preload_libraries';\"").readlines()[2]
        exists = existsLines.split('|')[1]
        if "pg_stat_statements" not in exists:
            logging.debug("pg_stat_statements does not exist")
            if self.ALLOW_RESTART == False:
                while True:
                    response = input("To optimize for latency database must be restarted at least once in order to enable pg_stat_statements. Would you like to continue the optimization? [Y] Restart once      [N] Abort optimization: ")
                    if response not in ['Y','y','N','n']:
                        response = input("To optimize for latency database must be restarted at least once in order to enable pg_stat_statements. Would you like to continue the optimization? [Y] Restart once      [N] Abort optimization: ")
                        continue
                    else:
                        break
                if response in ["Y", "y"]:
                    with open(self.CONF_OVERRIDE_FILE_PG_STATS, 'w') as pg_stat_file:
                        pg_stat_file.write("shared_preload_libraries = 'pg_stat_statements'")
                elif response in ["N", "n"]:
                    logging.info("Restart not allowed, aborting optimization!")
                    sys.exit(0)
            else:
                try:
                    with open(self.CONF_OVERRIDE_FILE_PG_STATS, 'w') as pg_stat_file:
                        pg_stat_file.write("shared_preload_libraries = 'pg_stat_statements'")
                except:
                    pass

        os.system("systemctl restart postgresql")
        installed = int(self.psql("-d {} -c  \"SELECT count(*) FROM pg_extension WHERE extname = 'pg_stat_statements';\"".format(self.DATABASE_NAME)).readlines()[2])
        if not installed:
            logging.debug("Installing pg_stat_statements extension")
            self.psql("-d {} -c \"CREATE EXTENSION pg_stat_statements;\"".format(self.DATABASE_NAME)).readlines()
        else:
            logging.debug("pg_stat_statements extension already installed")
            pass
        logging.debug("Resetting pg_stat_statements table")
        self.psql("-d {} -c \"SELECT pg_stat_statements_reset();\"".format(self.DATABASE_NAME)).readlines()

    @staticmethod
    def s():
        return time.time()

    def get_metric_stats(self):
        throughput_stats = self.get_xact_commit()
        query_runtime_stats = ""
        if self.OPTIMIZATION_OBJECTIVE == "Latency":
            query_runtime_stats = self.psql("-d {} -xc \"SELECT calls, queryid, {} FROM pg_stat_statements ORDER BY calls DESC;\"".format(self.DATABASE_NAME, self.pg_stat_col)).read()
        return throughput_stats, query_runtime_stats


    def restart(self):
        # We need to this here instead of in client since WARMUP_TIME is
        # handled here. We probably want to apply WARMUP_TIME even if we
        # don't restart.
        if self.ALLOW_RESTART:
            logging.info("UbuntuPgAdapter: Restarting Database")
            os.system("systemctl restart postgresql")
            logging.info("UbuntuPgAdapter: Database restarted")
        else:
            logging.info("Skipping restart")
            self.psql("-c \"SELECT pg_reload_conf();\"")
        if wait_for_postgres_ready_for_connect() == 2:
            self.abort()
        if self.WARMUP_TIME and self.WARMUP_TIME > 0:
            logging.info("UbuntuPgAdapter: Warming up the database for {}s after installing proposed configuration.".format(self.WARMUP_TIME))
            time.sleep(self.WARMUP_TIME)
        else:
            #print("UbuntuPgAdapter: Sleeping for safety")
            #time.sleep(30)
            self.wait_for_commits()
        self.start_time = self.s()
        self.start_commit = self.get_xact_commit()

    def get_client_info(self):
        logging.info("Getting client's system and DBMS information")
        client_info = {}
        #client_info["DBTYPE"] = "mixed" Todo: How to get the db_type? From the user?
        client_info["DBVERSION"] = self.db_version
        client_info["OSTYPE"] = "Ubuntu"
        client_info["NUMOFCPU"] = self.no_of_cpu
        #client_info["HDTYPE"] #Todo: Get the real hd type. How?
        client_info["MAXCONNECTIONS"] = int(self.psql("-c \"show max_connections;\"").readlines()[2].split(' ')[1].strip())
        client_info["TOTALMEMORY"] = self.memory
        client_info["AVAILABLEMEMORY"] = self.memory #Todo: How to get the real available memory?
        return client_info


    def update_config(self, tuning_request):
        logging.info("UbuntuPgAdapter: Installing proposed configuration")
        # write a temporary file to conf.d directory
        # 1. create conf.d directory if it not exists
        config_log_list = ["Proposed Configuration:"]
        ensure_dir(self.CONF_OVERRIDE_PATH)
        # 2. write the conf file in conf.d directory
        conf_file = open(self.CONF_OVERRIDE_FILE, "w")
        for tKey in tuning_request:
            t_value = tuning_request[tKey]
            conf_file.write(tKey + " = " + str(t_value) + self.units[tKey] + "\n")
            config_log_list.append(tKey + " = " + str(t_value) + self.units[tKey])
        conf_file.close()
        logging.debug('\n'.join(config_log_list))
        # 3. Make sure conf file is referenced at the end in the main conf file
        with open(self.BASE_CONF_FILE, "r+") as main_conf_file:
            include_line = "include_dir 'conf.d'\n"
            for line in main_conf_file:
                if include_line in line:
                    break
            else:  # not found, we are at the eof
                main_conf_file.write(include_line)  # append missing data

    def abort_signal_handler(self, sig, frame):
        self.abort_optimization()

    def revert_to_default(self):
        if os.path.exists(self.CONF_OVERRIDE_FILE_PG_STATS) or os.path.exists(self.CONF_OVERRIDE_FILE):
            try:
                os.remove(self.CONF_OVERRIDE_FILE_PG_STATS)
            except:
                # print(self.CONF_OVERRIDE_FILE_PG_STATS + " does not exist.")
                pass
            try:
                os.remove(self.CONF_OVERRIDE_FILE)
            except:
                logging.warning(self.CONF_OVERRIDE_FILE + " does not exist.")
        self.safely_abort()

    def pre_abort(self):
        if os.path.exists(self.CONF_OVERRIDE_FILE_PG_STATS):
            try:
                os.remove(self.CONF_OVERRIDE_FILE_PG_STATS)
            except:
                logging.warning(self.CONF_OVERRIDE_FILE_PG_STATS + " does not exist.")
        self.safely_abort()

    def abort_optimization(self, abort = False):
        if self.MODE == "pre-tuning":
            if abort:
                self.pre_abort()
            else:
                while True:
                    response = input("Do you want to abort the optimization?. [Y] Yes      [N] No: ")
                    if response not in ['Y','y','N','n']:
                        response = input("Do you want to abort the optimization?. [Y] Yes      [N] No: ")
                        continue
                    else:
                        break
                if response in ['Y','y']:
                    logging.info("Reverting back to default configuration!")
                    self.pre_abort()
                elif response in ['N','n']:
                    logging.info("Resuming Optimization!")

        if self.MODE == "tuning":
            if abort:
                self.revert_to_default()
            else:
                while True:
                    response = input("Do you want to abort the optimization?. [Y] Yes      [N] No: ")
                    if response not in ['Y','y','N','n']:
                        response = input("Do you want to abort the optimization?. [Y] Yes      [N] No: ")
                        continue
                    else:
                        break
                if response in ['Y','y']:
                    if self.bestPointFound:
                        while True:
                            next_response = input("[D] Revert back to default configuration    [I] Install best found configuration so far: ")
                            if next_response not in ['D','I']:
                                next_response = input("[D] Revert back to default configuration    [I] Install best found configuration so far: ")
                                continue
                            else:
                                break

                        if next_response == "D":
                            logging.info("Reverting back to default configuration!")
                            self.revert_to_default()

                        elif next_response == "I":
                            logging.info("Installing the best found configuration!")
                            self.update_config(self.bestPointFound)
                            self.safely_abort()
                    else:
                        logging.info("Reverting back to default configuration!")
                        self.revert_to_default()

                elif response in ['N','n']:
                    logging.info("Resuming Optimization!")


        if self.MODE == "post-tuning":
            if abort:
                self.revert_to_default()
            else:
                while True:
                    response = input("Do you want to abort the optimization?. [Y] Yes      [N] No: ")
                    if response not in ['Y','y','N','n']:
                        response = input("Do you want to abort the optimization?. [Y] Yes      [N] No: ")
                        continue
                    else:
                        break
                if response in ['Y','y']:
                    while True:
                        next_response = input("[D] Revert back to default configuration    [K] Keep the best found configuration: ")
                        if next_response not in ['D','K']:
                            next_response = input("[D] Revert back to default configuration    [K] Keep the best found configuration: ")
                            continue
                        else:
                            break
                    if next_response == "D":
                        logging.info("Reverting back to default configuration!")
                        self.revert_to_default()
                    elif next_response == "K":
                        logging.warning("Keeping the best found configuration!")
                        self.safely_abort()

                elif response in ['N','n']:
                    logging.info("Resuming Optimization!")

    def safely_abort(self):
        if self.stats is not None:
            self.stats.abort()
        if self.ALLOW_RESTART:
            logging.info("Restarting postgres")
            os.system("systemctl restart postgresql")
        state = get_connect()
        while not state == 0:
            if state == 2:
                raise TuningError("FATAL ERROR: Could not restart postgresql after restoring config")
        logging.info("Tuning aborted. Configuration set. Postgres running.")
        sys.exit(0)

    def create_stats(self, period, repetitions, stats):
        self.pg_stats = PgStats(period, repetitions, self)
        self.stats = stats
        return self.pg_stats

    def psql(self, command):
        if self.PASSWORD_AUTH:
            command = "psql -U {} -d {} -h localhost {}".format(self.USERNAME, self.DATABASE_NAME, command)
        else:
            command = "sudo -i -u postgres psql {}".format(command)
        logging.debug(command)
        return os.popen(command)


def current_milli_time():
    return round(time.time() * 1000)

def get_timestamp():
    x = datetime.datetime.now()
    return x.strftime("%x %X")

class PgStats :

    def __init__(self, period, repetitions, db):
        self.PERIOD = period
        self.REPETITIONS = repetitions
        self.db = db
        self.data_points = []
        self.t = None
        self.start_time = None
        self.repetition_count = 0

    def collect(self):
        xact_commit, runtime = self.db.get_metric_stats()
        datapoint = {
            "timestamp": get_timestamp(),
            "pg": {
                "xact_commit": xact_commit,
                "query_runtime": runtime
            }
        }
        self.data_points.append(datapoint)
        self.repetition_count += 1

    def flush(self):
        if self.t is not None:
            self.t.cancel()
            self.t.join()
            self.start_time = None
        data_points = self.data_points
        self.data_points = []
        self.repetition_count = 0
        return data_points

    def run(self):
        try:
            self.collect()
        except:
            logging.warning("Couldn't collect xact_commit")
        next_time = self.PERIOD
        if self.start_time is not None:
            next_time = self.PERIOD - ((time.time() - self.start_time) % self.PERIOD)
        else:
            self.start_time = time.time()
        if self.repetition_count < self.REPETITIONS:
            self.t = Timer(next_time, self.run)
            self.t.daemon = True
            self.t.start()

    def abort(self):
        if self.t is not None:
            self.t.cancel()
            self.t.join()
        logging.debug("PgStats aborted")