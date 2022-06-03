class Adapter:
    def get_output(self):
        print("Must bo overridden by subclass")

    def restart(self):
        print("Must bo overridden by subclass")

    def update_config(self, tuning_request):
        print("Must bo overridden by subclass")

    def createStats(self):
        print("Must be overridden by subclass")
