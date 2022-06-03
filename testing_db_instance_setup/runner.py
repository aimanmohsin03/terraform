import os
import time
import argparse

LOG_PATH = "/var/log/postgresql/postgresql-14-main.log"
RESTORE_DATA_DIR = "/mnt/data/rsync"
DATA_DIR = "/mnt/data/postgresql"
parser = argparse.ArgumentParser()
parser.add_argument("--benchmark", help="Select a benchmark from tpcc, wikipedia and ch-benchmark.", default="tpcc")
args = parser.parse_args()
benchmark = args.benchmark


def stop_database():
    os.system("sudo service postgresql stop")

def start_database():
    os.system("sudo service postgresql start")

def restore_database(source_data_dir, dest_data_dir):
    # os.system('sudo rm -r {}/postgresql/12/main/base'.format(dest_data_dir))
    os.system('sudo rsync -av -c --delete --delete-excluded {} {}'.format(source_data_dir, dest_data_dir))


def create_database_backup(source_data_dir, dest_data_dir):
    os.system('sudo rsync -av -c  {} {}'.format(source_data_dir, dest_data_dir))

def psql(command):
    os.system("sudo -u postgres psql -c \"{}\"".format(command))


def get_connect():
    command = "pg_isready"
    output = os.popen(command).read()
    return "accepting connections" in output


def bench(commands):
    if benchmark == "chbenchmark":
        os.system("./oltpbenchmark -b tpcc, {} -c config/{}_config_postgres.xml {} -s 5 -o outputfile".format(benchmark,benchmark,commands))
    else:
        os.system("./oltpbenchmark -b {} -c config/{}_config_postgres.xml {} -s 5 -o outputfile".format(benchmark,benchmark,commands))


def wait_for_postgres_ready_for_connect():
    print("Waiting for connect...", end='', flush=True)
    while not get_connect():
        print('.', end='', flush=True)
        time.sleep(1)
    print('.')


while True:
    drop_time = time.time()
    print("Wait a little to make it easier to interrupt...")
    time.sleep(2)
    #wait_for_postgres_ready_for_connect()
    #print("Starting restore")
    #print("Stopping database")
    #stop_database()
    #print("syncing")
    #restore_database(RESTORE_DATA_DIR, DATA_DIR)
    #print("starting database")
    #start_database()
    #os.system("sudo -u postgres pg_restore --clean -d tpcc ./tpcc-backup.tar")
    wait_for_postgres_ready_for_connect()
    done_time = time.time()
    print("Reload time: {}s".format(done_time - drop_time))
    bench("--execute=true")