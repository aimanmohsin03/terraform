import random

from adapters.adapter import Adapter


class RocksDbAdapter(Adapter):

    def __init__(self, adapter_data):
        print("Initiating RocksDbAdapter")

    def get_output(self):
        return random.randrange(-100, -1)