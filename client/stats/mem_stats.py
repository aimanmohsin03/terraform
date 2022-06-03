import os
from threading import Timer
import time
import datetime
import logging


def get_free_memory():
    output = os.popen("free -m").read()
    lines = output.split('\n')

    labels = list(map(str.strip, lines[0].split()))
    values = list(map(str.strip, lines[1].split()))
    info = {}
    for i in range(len(labels)):
        info[labels[i]] = int(values[i + 1])

    return info


def current_milli_time():
    return round(time.time() * 1000)

def get_timestamp():
    x = datetime.datetime.now()
    return x.strftime("%x %X")


class MemStats:

    def __init__(self, period, repetitions):
        self.PERIOD = period
        self.REPETITIONS = repetitions
        self.data_points = []
        self.t = None
        self.start_time = None
        self.repetition_count = 0

    def collect(self):
        datapoint = {
            "timestamp": get_timestamp(),
            "free_m": get_free_memory()
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
            next_time = self.PERIOD
            if self.start_time is not None:
                next_time = self.PERIOD - ((time.time() - self.start_time) % self.PERIOD)
            else:
                self.start_time = time.time()
            if self.repetition_count < self.REPETITIONS:
                self.t = Timer(next_time, self.run)
                self.t.daemon = True
                self.t.start()
        except:
            logging.exception("Can't run free -m")

    def abort(self):
        if self.t is not None:
            self.t.cancel()
            self.t.join()
        logging.debug("mem_stats aborted")
