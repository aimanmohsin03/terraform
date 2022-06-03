import math
import time
import logging
from stats.io_stats import IOStats
from stats.mem_stats import MemStats
from threading import Timer


class Stats:
    def __init__(self, config, job, db):
        #Default config
        self.duration = 60
        sample_rate = config["STATS_SAMPLE_RATE"]
        device_filter = ["^loop"]
        devices = []
        columns = ["%util", "rMB/s", "wMB/s", "dMB/s"]

        #Overrides
        if "STATS_SAMPLE_RATE" in config:
            sample_rate = config["STATS_SAMPLE_RATE"]
        if "STATS_IO_DEVICE_FILTER" in config:
            device_filter = config["STATS_IO_DEVICE_FILTER"]
        if "STATS_IO_DEVICES" in config:
            devices = config["STATS_IO_DEVICES"]
        if "STATS_IO_COLUMNS" in config:
            columns = config["STATS_IO_COLUMNS"]

        repetitions = math.floor(self.duration / sample_rate)
        self.memStats = MemStats(sample_rate, repetitions)
        self.ioStats = IOStats(sample_rate, repetitions, device_filter, devices, columns)
        self.dbStats = db.create_stats(sample_rate, repetitions, self)
        self.job = job
        self.timer = None

    def run(self):
        logging.debug("Stats running")
        self.memStats.run()
        self.ioStats.run()
        self.dbStats.run()
        self.timer = Timer(self.duration, self.flush)
        self.timer.daemon = True
        self.timer.start()

    def abort(self):
        if self.timer is not None:
            self.timer.cancel()
            self.timer.join()
            logging.debug("Stats aborted")
            self.memStats.abort()
            self.dbStats.abort()

    def flush(self):
        logging.debug("Stats flushing")
        mem_data = self.memStats.flush()
        io_data = self.ioStats.flush()
        db_data = self.dbStats.flush()
        self.run()
        self.job.post_stats({
            "mem": mem_data,
            "io": io_data,
            "db": db_data
        })



# Just a simple test
def main():
    stat_collector = Stats(3, 1)
    stat_collector.run()
    time.sleep(5)
    data = stat_collector.flush()
    print(data)
    print(len(data["mem"]))
    print(len(data["io"]))


if __name__ == '__main__':
    main()
