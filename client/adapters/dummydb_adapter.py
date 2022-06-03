from adapters.adapter import Adapter


class DummyDbAdapter(Adapter):

    def __init__(self, adapter_data):
        print("Initiating DummyDbAdapter")
        self.out_cnt = -1

    def get_output(self):
        print("Dummy get_output")
        self.out_cnt -= 1
        return self.out_cnt

    def restart(self):
        print("Dummy restart")

    def update_config(self, tuning_request):
        print("Dummy update config \n{}".format(tuning_request))
