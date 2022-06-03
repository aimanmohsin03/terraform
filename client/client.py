import os
import sys
import time
import traceback
import config
import signal
import logging

from dbms_adapter_factory import AdapterFactory
from job import Job
from stats.stats import Stats

API_ENDPOINT = config.ENDPOINT
if "DBTUNE_ENDPOINT" in os.environ:
    API_ENDPOINT = os.environ["DBTUNE_ENDPOINT"]


def run_job(api_key, job_id):
    try:
        job = Job(API_ENDPOINT, api_key, job_id)
        config = job.get_config()
        db = AdapterFactory.get_adapter(config)
        signal.signal(signal.SIGINT, db.abort_signal_handler)
        experiment_duration = config["EXPERIMENT_DURATION"]
        stats = Stats(config, job, db)
        stats.run()

        job.post_client_info(db.get_client_info())

        tuning_request = job.get_tuning_request()
        knobs = {}
        state = "not-started"
        while "endOfJob" not in tuning_request:
            knobs = tuning_request.get("knobs", tuning_request)
            db.bestPointFound = tuning_request.get("bestPointFound", tuning_request)
            client_data = tuning_request.get("clientData", {})
            state = client_data.get("state", "started")
            if state == "aborted":
                break
            iteration = tuning_request.get("iteration", None)
            if state == "started":
                db.MODE = "tuning"
                logging.info("Starting Iteration {}".format(iteration))
                db.update_config(knobs)
                db.restart()
                logging.info("Measuring database performance for {}s".format(experiment_duration))
                metric_stats = {}
                metric_stats['throughput_stats_start'], metric_stats['query_runtime_stats_start'] = db.get_metric_stats()
                time.sleep(experiment_duration)
                metric_stats['throughput_stats_end'], metric_stats['query_runtime_stats_end'] = db.get_metric_stats()
                logging.info("Iteration {} completed!".format(iteration))
                tuning_request = job.iterate(metric_stats)
            else:
                logging.info("Monitoring database performance, Waiting for optimization to be started from the web interface.")
                logging.debug("Waiting for new request.")
                time.sleep(60)
                tuning_request = job.get_tuning_request()

        logging.info("Tuning session is over")
        db.MODE = "post-tuning"
        if not state == "aborted":
            if "bestPointFound" in tuning_request:
                logging.info("Installing the best found configuration!")
                bestPointFound = tuning_request["bestPointFound"]
                db.update_config(bestPointFound)
                db.restart()
                # Monitoring after installing the best found configuration for 1 hour and then safely aborting the optimization.
                logging.disable(logging.DEBUG)
                logging.info("Monitoring after installing the best found configuration!")
                time.sleep(3600)
                db.safely_abort()
            else:
                logging.error("Error: Couldn't apply best point found")

        while not state == "ended" and not state == "aborted":
            time.sleep(60)
            tuning_request = job.get_tuning_request()
            client_data = tuning_request.get("clientData", {})
            state = client_data.get("state", "post-tuning")

        if state == "aborted":
            db.abort_optimization(abort=True)


    except Exception as e:
        if "Tuning aborted" in str(e):
            logging.info(str(e))
        else:
            logging.critical("Fatal error. Optimization stopped")
            traceback.print_exc()
        stats.abort()
    logging.info("Exit")


def main():
    API_KEY = sys.argv[1]
    JOB_ID = sys.argv[2]
    run_job(API_KEY, JOB_ID)


if __name__ == '__main__':
    main()
