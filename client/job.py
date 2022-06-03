import json
import time
import datetime
import logging
import requests
from requests.exceptions import HTTPError


class Job:
    def __init__(self, endpoint, api_key, job_id):
        logging.info("Connecting to job {} {}".format(api_key, job_id))
        self.api_key = api_key
        self.job_id = job_id
        self.request = endpoint + self.job_id + '/request?v=2'
        self.response = endpoint + self.job_id + '/response?v=2'
        self.adapter = endpoint + self.job_id + '/adapter'
        self.stats = endpoint + self.job_id + "/stats"
        self.client_info = endpoint + self.job_id + "/client-info"
        self.iteration = None

    def post_client_info(self, client_info):
        try:
            requests.post(self.client_info, json=client_info, headers={'X-HYPER-API-KEY': self.api_key}, )
        except HTTPError as http_err:
            logging.error(f'HTTP error occurred: {http_err}')  # Python 3.6
        except Exception as err:
            logging.exception(f'Other error occurred: {err}')  # Python 3.6


    def get_tuning_request(self):
        try:
            response = requests.get(self.request,
                                    headers={'X-HYPER-API-KEY': self.api_key}, )
            response.raise_for_status()
        except HTTPError as http_err:
            logging.error(f'HTTP error occurred: {http_err}')  # Python 3.6
        except Exception as err:
            logging.exception(f'Other error occurred: {err}')  # Python 3.6
        else:
            data = response.json()
            #print(json.dumps(data, indent=2, sort_keys=True))
            self.iteration = data.get("iteration", None)
            if self.iteration is not None:
                logging.debug("Iteration {}".format(self.iteration))
            return data

    def post_stats(self, stats_data):
        try:
            response = requests.post(self.stats,
                                 json=stats_data,
                                 headers={'X-HYPER-API-KEY': self.api_key}, )
        except HTTPError as http_err:
            logging.error(f'HTTP error occurred: {http_err}')  # Python 3.6
        except Exception as err:
            logging.exception(f'Other error occurred: {err}')  # Python 3.6

    def iterate(self, metric_stats, stats_data=None):
        #print("output:")
        #print(json.dumps(metric_stats, indent=2, sort_keys=True))
        try:
            response = requests.post(self.response, json={"metric_stats": metric_stats, "stats_data": stats_data, "iteration": self.iteration, "timestamp": get_timestamp()},
                                     headers={'X-HYPER-API-KEY': self.api_key}, )
            response.raise_for_status()
        except HTTPError as http_err:
            logging.error(f'HTTP error occurred: {http_err}')  # Python 3.6
            logging.info("Backing of for 30s and trying to get the new request again...")
            time.sleep(30)
            return self.get_tuning_request()
        except Exception as err:
            logging.exception(f'Other error occurred: {err}')  # Python 3.6
        else:

            data = response.json()
            if "knobs" in data:
                tuning_request = data["knobs"]
                self.iteration = data["iteration"]
                if self.iteration is not None:
                    logging.debug("Iteration {}".format(self.iteration))
            elif "error" in data:
                raise Exception(data)
            return data

    def get_config(self):
        try:
            response = requests.get(self.adapter,
                                    headers={'X-HYPER-API-KEY': self.api_key}, )
            response.raise_for_status()
        except HTTPError as http_err:
            logging.error(f'HTTP error occurred: {http_err}')  # Python 3.6
        except Exception as err:
            logging.exception(f'Other error occurred: {err}')  # Python 3.6
        else:
            adapter_data = response.json()
            #print("adapter_data:")
            #print(json.dumps(adapter_data, indent=2, sort_keys=True))
            return adapter_data

def get_timestamp():
    x = datetime.datetime.now()
    return x.strftime("%x %X")