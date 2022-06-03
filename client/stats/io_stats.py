import os
import subprocess
import time
import re
import logging


# Parse a file collected like so:
#   iostat 5 10 -d -xm -t > iostatdata.txt
#
# Note that the first sample is "since last reboot"
# The following samples are "since previous sample"
def parse_iostat_data_file(file_path, device_filter = [], devices = [], data_filter=None):
    #print("parse_iostrat_data_file {} {}".format(devices, device_filter))
    samples = []
    labels = None
    data_point = None
    data_point_added = False
    with open(file_path) as f:
        content = [i.strip() for i in f.readlines()]
        for line in content:
            if len(line) < 1:
                data_point = None
                labels = None
                data_point_added = False
            elif data_point is None:
                data_point = {"timestamp": line, "iostat": {}}
            elif labels is None:
                labels = [j.strip() for j in line.split()]
            else:
                device_sample = [j.strip() for j in line.split()]
                device_name = device_sample[0]
                add_device = False
                if len(devices) > 0:
                    if device_name in devices:
                        add_device = True
                else:
                    add_device = True
                    for df in device_filter:
                        if re.match(df, device_name):
                            add_device = False
                if add_device:
                    data_point["iostat"][device_name] = {}
                    for k in range(len(device_sample)):
                        label = labels[k]
                        if data_filter is None or label in data_filter:
                            if label != "Device":
                                data_point["iostat"][device_name][label] = float(device_sample[k])
                                if not data_point_added:
                                    samples.append(data_point)
                                    data_point_added = True
    return samples


class IOStats:

    def __init__(self, period, repetitions, device_filter=[], devices=[], columns=[]):
        self.PERIOD = period
        self.REPETITIONS = repetitions
        self.result = None
        self.stat_file = "{}/iostatdata.txt".format(os.getcwd())
        self.device_filter = device_filter
        self.devices = devices
        self.columns = columns

    def run(self):
        cmd = "iostat {} {} -d -xm -t > {} &".format(self.PERIOD, self.REPETITIONS, self.stat_file)
        logging.debug(cmd)
        subprocess.call(cmd, shell=True)

    def flush(self):
        return parse_iostat_data_file(self.stat_file, device_filter=self.device_filter, data_filter=self.columns)


# Just a simple test
def main():
    #stat_collector = IOStats(period=1, repetitions=3, device_filter=["loop"], devices=["vda"], columns=["%util", "rMB/s", "wMB/s", "dMB/s"])
    stat_collector = IOStats(period=1, repetitions=3, columns=["%util", "rMB/s", "wMB/s", "dMB/s"])
    stat_collector.run()
    time.sleep(5)
    print(stat_collector.flush())


if __name__ == '__main__':
    main()
