import os
import time
import argparse


LOG_PATH = "/var/log/postgresql/postgresql-14-main.log"
parser = argparse.ArgumentParser()
parser.add_argument("--benchmark", help="Select a benchmark from tpcc, wikipedia and chbenchmark.", default="tpcc")
args = parser.parse_args()
benchmark = args.benchmark

def psql(command):
    os.system("sudo -u postgres psql -c \"{}\"".format(command))


def bench(commands):
    if benchmark == "chbenchmark":
        os.system("./oltpbenchmark -b tpcc, {} -c config/{}_config_postgres.xml {} -s 5 -o outputfile".format(benchmark,benchmark,commands))
    else:
        os.system("./oltpbenchmark -b {} -c config/{}_config_postgres.xml {} -s 5 -o outputfile".format(benchmark,benchmark,commands))

def db_restart():
    os.system("sudo service postgresql restart")


def get_connect():
    command = "pg_isready"
    output = os.popen(command).read()
    return "accepting connections" in output


def wait_for_postgres_ready_for_connect():
    print("Waiting for connect...", end='', flush=True)
    while not get_connect():
        print('.', end='', flush=True)
        time.sleep(1)
    print('.')

psql("DROP DATABASE IF EXISTS {}".format(benchmark))
psql("CREATE DATABASE {}".format(benchmark))
db_restart()
wait_for_postgres_ready_for_connect()
bench("--create=true --load=true")
#wait_for_postgres_ready_for_connect()
#os.system("sudo -u postgres pg_dump -F t tpcc > ./tpcc-backup.tar")
wait_for_postgres_ready_for_connect()
print("Done")