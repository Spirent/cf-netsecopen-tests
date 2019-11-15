import json
import logging
import time
import sys
import os
import numpy as np
import pandas as pd
import pathlib
import sys

project_dir = pathlib.Path().absolute().parent
sys.path.append(str(project_dir))

from cf_common.CfClient import *


class RollingStats:
    """Creates rolling window statistics object

    Inputs are sample window size and number of digits to round values too.
    For example:
    - transactions per second window size can be 2 or higher with 0 round digits
    - time to first byte can have 1 round digit, best is to use the same window size
    """

    def __init__(self, sample_window_size, round_digits):
        # initiate list with sample size count of zeros
        self.sample_size = sample_window_size
        self.round_digits = round_digits
        self.list = [0] * self.sample_size
        self.current_value = 0
        self.avg_val = 0
        self.avg_val_last = 0
        self.increase_avg = 0
        self.variance = 0.000
        self.avg_max_load_variance = 0.00
        self.new_high = False
        self.highest_value = 0
        self.not_high_count = 0
        self.stable = False
        self.stable_count = 0

    def update(self, new_value):
        """Updates Rolling List and returns current variance

        :param new_value: new single value of for example TPS or TTFB
        :return: variance
        """
        self.current_value = new_value
        if len(self.list) == self.sample_size:
            self.list.pop(0)
        self.list.append(self.current_value)
        self.avg_val = sum(self.list) / len(self.list)
        self.avg_val = round(self.avg_val, self.round_digits)
        if self.round_digits == 0:
            self.avg_val = int(self.avg_val)
        max_var = max(self.list) - min(self.list)
        self.variance = (max_var / self.avg_val) if self.avg_val != 0 else 0
        self.variance = round(self.variance, 3)
        # check if new value value is the new high for later use
        self.check_if_highest()
        return self.variance

    def reset(self):
        """Resets rolling window back to all 0

        Can be used after load increase on stat as current load that tracks if load is stable after increase
        Don't use on reported rolling stat as it will have high increase after its set to all 0

        :return: None
        """
        self.list = [0] * self.sample_size

    def check_if_stable(self, max_var_reference):
        """Checks if load is stable in current list

        If its stable also check the increase since a load change was last completed.

        :param max_var_reference: user/test configured reference value, e.g. 0.03 for 3%
        :return: True if stable, False if not
        """
        if self.variance <= max_var_reference:
            self.stable = True
            self.stable_count += 1
            self.increase_since_last_load_change()
            return True
        else:
            self.stable = False
            self.stable_count = 0
            return False

    def increase_since_last_load_change(self):
        """Sets increase_avg, the increase since last load

        This function can be called from check_if_stable. The set result can be used by a function to
        determine by how much to increase the load. After load change call load_increase_complete to
        set the value for the next round.
        :return: None
        """
        if self.avg_val_last != 0:
            self.increase_avg = (
                (self.avg_val - self.avg_val_last) / self.avg_val_last
            ) * 100
            self.increase_avg = round(self.increase_avg, 2)
        else:
            self.avg_val_last = 1

    def load_increase_complete(self):
        """set last load change value

        Use in combination with increase_since_last_load_change

        :return: None
        """
        self.avg_val_last = self.avg_val

    def check_if_highest(self):
        """Checks and sets highest value reference

        Can be called by update function to track if the current update is the new highest value

        :return: True if new high, False if not higher vs. previous
        """
        if self.highest_value < self.avg_val:
            self.highest_value = self.avg_val
            self.new_high = True
            self.not_high_count = 0
        else:
            self.new_high = False
            self.not_high_count += 1

        self.avg_max_load_variance = (
            (self.avg_val / self.highest_value) if self.highest_value != 0 else 0
        )
        self.avg_max_load_variance = round(self.avg_max_load_variance, 2)

        if self.new_high:
            return True
        if not self.new_high:
            return False


class CfRunTest:
    def __init__(self, cf, test_details, result_file, temp_file_dir):
        self.cf = cf  # CfClient instance
        self.result_file = result_file
        self.temp_dir = temp_file_dir
        self.test_id = test_details["id"]
        self.type_v2 = test_details["type"]
        self.in_name = test_details["name"]
        self.in_run = test_details["run"]
        self.in_load_type = test_details["load_type"]
        self.in_start_load = test_details["start_load"]
        self.in_incr_low = int(test_details["incr_low"])
        self.in_incr_med = int(test_details["incr_med"])
        self.in_incr_high = int(test_details["incr_high"])
        self.in_duration = int(test_details["duration"])
        self.in_startup = int(test_details["startup"])
        self.in_rampup = int(test_details["rampup"])
        self.in_rampdown = int(test_details["rampdown"])
        self.in_shutdown = int(test_details["shutdown"])
        self.in_sustain_period = int(test_details["sustain_period"])
        self.in_threshold_low = float(test_details["low_threshold"])
        self.in_threshold_med = float(test_details["med_threshold"])
        self.in_threshold_high = float(test_details["high_threshold"])
        self.in_sustain_period = int(test_details["sustain_period"])
        self.variance_sample_size = int(test_details["variance_sample_size"])
        self.in_max_variance = float(test_details["max_variance"])
        # self.in_capacity_adjust = int(test_details["capacity_adj"])

        self.in_goal_seek = False
        self.first_steady_interval = True
        self.in_goal_seek = test_details["goal_seek"]
        if self.in_goal_seek.lower() in {"true", "y", "yes"}:
            self.in_goal_seek = True
            self.first_steady_interval = False
        else:
            self.in_goal_seek = False

        self.test_config = self.get_test_config()
        self.queue_id = self.test_config["config"]["queue"]["id"]
        self.queue_info = self.get_queue(self.queue_id)
        self.queue_capacity = int(self.queue_info["capacity"])
        log.info(f"queue_capacity: {self.queue_capacity}")
        self.core_count = self.core_count_lookup(self.queue_info)
        log.info(f"core_count: {self.core_count}")
        self.client_port_count = len(self.test_config["config"]["interfaces"]["client"])
        log.info(f"client_port_count: {self.client_port_count}")
        self.server_port_count = len(self.test_config["config"]["interfaces"]["server"])
        log.info(f"server_port_count: {self.server_port_count}")
        self.client_core_count = int(
            self.core_count
            / (self.client_port_count + self.server_port_count)
            * self.client_port_count
        )
        log.info(f"client_core_count: {self.client_core_count}")
        self.in_capacity_adjust = self.check_capacity_adjust(
            test_details["capacity_adj"],
            self.in_load_type,
            self.client_port_count,
            self.client_core_count,
        )
        log.info(f"in_capacity_adjust: {self.in_capacity_adjust}")
        # self.load_constraints = self.test_config["config"]["loadSpecification"][
        #     "constraints"]
        if not self.update_config_load():
            report_error = f"unknown load_type with test type"
            log.debug(report_error)
            print(report_error)
        self.test_config = self.get_test_config()

        self.test_run = self.start_test_run()
        if not self.test_started:
            report_error = f"test did not start\n{json.dumps(self.test_run, indent=4)}"
            log.debug(report_error)
            print(report_error)
        self.test_run_update = None

        self.id = self.test_run.get("id")
        self.queue_id = self.test_run.get("queueId")
        self.score = self.test_run.get("score")
        self.grade = self.test_run.get("grade")
        self.run_id = self.test_run.get("runId")
        self.status = self.test_run.get("status")  # main run status 'running'
        self.name = self.test_run.get("test", {}).get("name")
        self.type_v1 = self.test_run.get("test", {}).get("type")
        self.sub_status = self.test_run.get("subStatus")
        self.created_at = self.test_run.get("createdAt")
        self.updated_at = self.test_run.get("updatedAt")
        self.started_at = self.test_run.get("startedAt")
        self.finished_at = self.test_run.get("finishedAt")
        self.progress = self.test_run.get("progress")
        self.time_elapsed = self.test_run.get("timeElapsed")
        self.time_remaining = self.test_run.get("timeRemaining")

        self.run_link = (
            "https://"
            + self.cf.controller_ip
            + "/#livecharts/"
            + self.type_v1
            + "/"
            + self.id
        )
        print(f"Live charts: {self.run_link}")

        self.report_link = None
        self.sub_status = None  # subStatus -  none while running or not started
        self.progress = 0  # progress  -  0-100
        self.time_elapsed = 0  # timeElapsed  - seconds
        self.time_remaining = 0  # timeRemaining  - seconds
        self.started_at = None  # startedAt
        self.finished_at = None  # finishedAt

        self.c_rx_bandwidth = 0
        self.c_rx_packet_count = 0
        self.c_rx_packet_rate = 0
        self.c_tx_bandwidth = 0
        self.c_tx_packet_count = 0
        self.c_tx_packet_rate = 0
        self.c_http_aborted_txns = 0
        self.c_http_aborted_txns_sec = 0
        self.c_http_attempted_txns = 0
        self.c_http_attempted_txns_sec = 0
        self.c_http_successful_txns = 0
        self.c_http_successful_txns_sec = 0
        self.c_http_unsuccessful_txns = 0
        self.c_http_unsuccessful_txns_sec = 0
        self.c_loadspec_avg_idle = 0
        self.c_loadspec_avg_cpu = 0
        self.c_memory_main_size = 0
        self.c_memory_main_used = 0
        self.c_memory_packetmem_used = 0
        self.c_memory_rcv_queue_length = 0
        self.c_simusers_alive = 0
        self.c_simusers_animating = 0
        self.c_simusers_blocking = 0
        self.c_simusers_sleeping = 0
        self.c_tcp_avg_ttfb = 0
        self.c_tcp_avg_tt_synack = 0
        self.c_tcp_cumulative_attempted_conns = 0
        self.c_tcp_cumulative_established_conns = 0
        self.c_url_avg_response_time = 0
        self.c_tcp_attempted_conn_rate = 0
        self.c_tcp_established_conn_rate = 0
        self.c_tcp_attempted_conns = 0
        self.c_tcp_established_conns = 0
        self.c_current_load = 0
        self.c_desired_load = 0
        self.c_total_bandwidth = 0
        self.c_memory_percent_used = 0
        self.c_current_desired_load_variance = 0.0
        self.c_current_max_load_variance = 0.0
        self.c_transaction_error_percentage = 0.0

        self.s_rx_bandwidth = 0
        self.s_rx_packet_count = 0
        self.s_rx_packet_rate = 0
        self.s_tx_bandwidth = 0
        self.s_tx_packet_count = 0
        self.s_tx_packet_rate = 0
        self.s_memory_main_size = 0
        self.s_memory_main_used = 0
        self.s_memory_packetmem_used = 0
        self.s_memory_rcv_queue_length = 0
        self.s_memory_avg_cpu = 0
        self.s_tcp_closed_error = 0
        self.s_tcp_closed = 0
        self.s_tcp_closed_reset = 0
        self.s_memory_percent_used = 0

        self.first_load_increase = True
        self.max_load_reached = False
        self.max_load = 0
        self.stop = False  # test loop control
        self.phase = None  # time phase of test: ramp up, steady ramp down

        # rolling statistics
        self.rolling_sample_size = self.variance_sample_size
        self.max_var_reference = self.in_max_variance
        self.rolling_tps = RollingStats(self.rolling_sample_size, 0)
        self.rolling_ttfb = RollingStats(self.rolling_sample_size, 1)
        self.rolling_current_load = RollingStats(self.rolling_sample_size, 0)
        self.rolling_count_since_goal_seek = RollingStats(
            self.rolling_sample_size, 1
        )  # round to 1 for > 0 avg
        self.rolling_cps = RollingStats(self.rolling_sample_size, 0)
        self.rolling_conns = RollingStats(self.rolling_sample_size, 0)
        self.rolling_bw = RollingStats(self.rolling_sample_size, 0)

        self.start_time = time.time()
        self.timer = time.time() - self.start_time
        self.time_to_run = 0
        self.time_to_start = 0
        self.time_to_activity = 0
        self.time_to_stop_start = 0
        self.time_to_stop = 0
        self.test_started = False

        # create entry in result file at the start of test
        self.save_results()

    def get_test_config(self):
        try:
            response = self.cf.get_test(
                self.type_v2, self.test_id, self.temp_dir / "running_test_config.json"
            )
            log.debug(f"{json.dumps(response, indent=4)}")
        except Exception as detailed_exception:
            log.error(
                f"Exception occurred when retrieving the test: "
                f"\n<{detailed_exception}>"
            )
        return response

    def get_queue(self, queue_id):
        try:
            response = self.cf.get_queue(queue_id)
            log.debug(f"{json.dumps(response, indent=4)}")
        except Exception as detailed_exception:
            log.error(
                f"Exception occurred when retrieving test queue informationn: "
                f"\n<{detailed_exception}>"
            )
        return response

    @staticmethod
    def core_count_lookup(queue_info):
        cores = 0
        for cg in queue_info["computeGroups"]:
            cores = cores + int(cg["cores"])
        return cores

    @staticmethod
    def check_capacity_adjust(
        cap_adjust, load_type, client_port_count, client_core_count
    ):
        if cap_adjust.lower() == "auto":
            if load_type.lower() in {"simusers", "simusers/second"}:
                return client_core_count
            else:
                return client_port_count
        else:
            return int(cap_adjust)

    def update_config_load(self):
        load_type = self.in_load_type.lower()
        test_type = self.test_type()

        if test_type in {"tput", "emix"} and load_type == "simusers":
            load_key = "bandwidth"
            self.in_load_type = "SimUsers"
        elif test_type in {"tput", "emix"} and load_type == "bandwidth":
            load_key = "bandwidth"
            self.in_load_type = "Bandwidth"
        elif test_type == "tput" and load_type == "simusers/second":
            load_key = "bandwidth"
            self.in_load_type = "SimUsers/Second"
        elif test_type == "cps" and load_type == "connections/second":
            load_key = "connectionsPerSecond"
            self.in_load_type = "Connections/Second"
        elif test_type == "cps" and load_type == "simusers":
            load_key = "connectionsPerSecond"
            self.in_load_type = "SimUsers"
        elif test_type == "cps" and load_type == "simusers/second":
            load_key = "connectionsPerSecond"
            self.in_load_type = "SimUsers/Second"
        elif test_type == "conns" and load_type == "simusers":
            load_key = "connections"
            self.in_load_type = "SimUsers"
        elif test_type == "conns" and load_type == "connections":
            load_key = "connections"
            self.in_load_type = "Connections"
        else:
            return False

        self.in_start_load = int(self.in_start_load) * self.in_capacity_adjust

        load_update = {
            "config": {
                "loadSpecification": {
                    "duration": int(self.in_duration),
                    "startup": int(self.in_startup),
                    "rampup": int(self.in_rampup),
                    "rampdown": int(self.in_rampdown),
                    "shutdown": int(self.in_shutdown),
                    load_key: int(self.in_start_load),
                    "type": self.in_load_type,
                    # "constraints": self.load_constraints,
                    "constraints": {"enabled": False},
                }
            }
        }
        with open(self.temp_dir / "test_load_update.json", "w") as f:
            json.dump(load_update, f, indent=4)

        response = self.cf.update_test(
            self.type_v2, self.test_id, self.temp_dir / "test_load_update.json"
        )

        log.info(f"{json.dumps(response, indent=4)}")
        return True

    def test_type(self):
        if self.type_v2 == "http_throughput":
            test_type = "tput"
        elif self.type_v2 == "http_connections_per_second":
            test_type = "cps"
        elif self.type_v2 == "open_connections":
            test_type = "conns"
        elif self.type_v2 == "emix":
            test_type = "emix"
        else:
            test_type = "tput"
        return test_type

    def start_test_run(self):
        try:
            response = self.cf.start_test(self.test_id)
            log.info(f"{json.dumps(response, indent=4)}")
            self.test_started = True
        except Exception as detailed_exception:
            log.error(
                f"Exception occurred when starting the test: "
                f"\n<{detailed_exception}>"
            )
            self.test_started = False
        return response

    def update_test_run(self):
        self.test_run_update = self.cf.get_test_run(self.id)
        self.status = self.test_run_update.get("status")  # main run status 'running'
        self.sub_status = self.test_run_update.get("subStatus")
        self.score = self.test_run_update.get("score")
        self.grade = self.test_run_update.get("grade")
        self.started_at = self.test_run_update.get("startedAt")
        self.finished_at = self.test_run_update.get("finishedAt")
        self.progress = self.test_run_update.get("progress")
        self.time_elapsed = self.test_run_update.get("timeElapsed")
        self.time_remaining = self.test_run_update.get("timeRemaining")

        update_test_run_log = (
            f"Status: {self.status} sub status: {self.sub_status} "
            f" elapsed: {self.time_elapsed}  remaining: {self.time_remaining}"
        )
        log.debug(update_test_run_log)
        return True

    def update_phase(self):
        """updates test phase based on elapsed time vs. loadspec configuration

        If goal seeking is enabled and the test is in steady phase, the phase will be set to goalseek

        :return: None
        """
        phase = None
        steady_duration = self.in_duration - (
            self.in_startup + self.in_rampup + self.in_rampdown + self.in_shutdown
        )
        if 0 <= self.time_elapsed <= self.in_startup:
            phase = "startup"
        elif self.in_startup <= self.time_elapsed <= (self.in_startup + self.in_rampup):
            phase = "rampup"
        elif (
            (self.in_startup + self.in_rampup)
            <= self.time_elapsed
            <= (self.in_duration - (self.in_rampdown + self.in_shutdown))
        ):
            phase = "steady"
            if self.first_steady_interval:
                phase = "rampup"
                self.first_steady_interval = False
        elif (
            (self.in_startup + self.in_rampup + steady_duration)
            <= self.time_elapsed
            <= (self.in_duration - self.in_shutdown)
        ):
            phase = "rampdown"
        elif (
            (self.in_duration - self.in_shutdown)
            <= self.time_elapsed
            <= self.in_duration
        ):
            phase = "shutdown"
        elif self.in_duration <= self.time_elapsed:
            phase = "finished"

        log.info(f"test phase: {phase}")
        self.phase = phase

        # Override phase if goal seeking is enabled
        if self.in_goal_seek and self.phase == "steady":
            self.phase = "goalseek"

    def update_run_stats(self):
        get_run_stats = self.cf.fetch_test_run_statistics(self.id)
        # log.debug(f'{get_run_stats}')
        self.update_client_stats(get_run_stats)
        self.update_server_stats(get_run_stats)

    def update_client_stats(self, get_run_stats):
        client_stats = {}
        for i in get_run_stats["client"]:
            if "type" in i and "subType" in i and "value" in i:
                type = i["type"]
                sub_type = i["subType"]
                value = i["value"]
                if not type in client_stats:
                    client_stats[type] = {}
                client_stats[type][sub_type] = value
            elif "type" in i and "value" in i:
                type = i["type"]
                value = i["value"]
                client_stats[type] = value
        self.assign_client_run_stats(client_stats)

    def update_server_stats(self, get_run_stats):
        server_stats = {}
        for i in get_run_stats["server"]:
            if "type" in i and "subType" in i and "value" in i:
                type = i["type"]
                sub_type = i["subType"]
                value = i["value"]
                if not type in server_stats:
                    server_stats[type] = {}
                server_stats[type][sub_type] = value
            elif "type" in i and "value" in i:
                type = i["type"]
                value = i["value"]
                server_stats[type] = value
        self.assign_server_run_stats(server_stats)

    def assign_client_run_stats(self, client_stats):
        self.c_rx_bandwidth = client_stats.get("driver", {}).get("rxBandwidth", 0)
        self.c_rx_packet_count = client_stats.get("driver", {}).get("rxPacketCount", 0)
        self.c_rx_packet_rate = client_stats.get("driver", {}).get("rxPacketRate", 0)
        self.c_tx_bandwidth = client_stats.get("driver", {}).get("txBandwidth", 0)
        self.c_tx_packet_count = client_stats.get("driver", {}).get("txPacketCount", 0)
        self.c_tx_packet_rate = client_stats.get("driver", {}).get("txPacketRate", 0)
        self.c_http_aborted_txns = client_stats.get("http", {}).get("abortedTxns", 0)
        self.c_http_aborted_txns_sec = client_stats.get("http", {}).get(
            "abortedTxnsPerSec", 0
        )
        self.c_http_attempted_txns = client_stats.get("sum", {}).get("attemptedTxns", 0)
        self.c_http_attempted_txns_sec = client_stats.get("sum", {}).get(
            "attemptedTxnsPerSec", 0
        )
        self.c_http_successful_txns = client_stats.get("sum", {}).get(
            "successfulTxns", 0
        )
        self.c_http_successful_txns_sec = client_stats.get("sum", {}).get(
            "successfulTxnsPerSec", 0
        )
        self.c_http_unsuccessful_txns = client_stats.get("sum", {}).get(
            "unsuccessfulTxns", 0
        )
        self.c_http_unsuccessful_txns_sec = client_stats.get("sum", {}).get(
            "unsuccessfulTxnsPerSec", 0
        )
        self.c_loadspec_avg_idle = client_stats.get("loadspec", {}).get(
            "averageIdleTime", 0
        )
        self.c_loadspec_avg_cpu = round(
            client_stats.get("loadspec", {}).get("cpuUtilized", 0), 1
        )
        self.c_memory_main_size = client_stats.get("memory", {}).get("mainPoolSize", 0)
        self.c_memory_main_used = client_stats.get("memory", {}).get("mainPoolUsed", 0)
        self.c_memory_packetmem_used = client_stats.get("memory", {}).get(
            "packetMemoryUsed", 0
        )
        self.c_memory_rcv_queue_length = client_stats.get("memory", {}).get(
            "rcvQueueLength", 0
        )
        self.c_simusers_alive = client_stats.get("simusers", {}).get("simUsersAlive", 0)
        self.c_simusers_animating = client_stats.get("simusers", {}).get(
            "simUsersAnimating", 0
        )
        self.c_simusers_blocking = client_stats.get("simusers", {}).get(
            "simUsersBlocking", 0
        )
        self.c_simusers_sleeping = client_stats.get("simusers", {}).get(
            "simUsersSleeping", 0
        )
        self.c_current_load = client_stats.get("sum", {}).get("currentLoadSpecCount", 0)
        self.c_desired_load = client_stats.get("sum", {}).get("desiredLoadSpecCount", 0)
        self.c_tcp_avg_ttfb = round(
            client_stats.get("tcp", {}).get("averageTimeToFirstByte", 0), 1
        )
        self.c_tcp_avg_tt_synack = round(
            client_stats.get("tcp", {}).get("averageTimeToSynAck", 0), 1
        )
        self.c_tcp_cumulative_attempted_conns = client_stats.get("tcp", {}).get(
            "cummulativeAttemptedConns", 0
        )
        self.c_tcp_cumulative_established_conns = client_stats.get("tcp", {}).get(
            "cummulativeEstablishedConns", 0
        )
        self.c_url_avg_response_time = round(
            client_stats.get("url", {}).get("averageRespTimePerUrl", 0), 1
        )
        self.c_tcp_attempted_conn_rate = client_stats.get("sum", {}).get(
            "attemptedConnRate", 0
        )
        self.c_tcp_established_conn_rate = client_stats.get("sum", {}).get(
            "establishedConnRate", 0
        )
        self.c_tcp_attempted_conns = client_stats.get("sum", {}).get(
            "attemptedConns", 0
        )
        self.c_tcp_established_conns = client_stats.get("sum", {}).get(
            "currentEstablishedConns", 0
        )

        self.time_elapsed = client_stats.get("timeElapsed", 0)
        self.time_remaining = client_stats.get("timeRemaining", 0)

        self.c_total_bandwidth = self.c_rx_bandwidth + self.c_tx_bandwidth
        if self.c_memory_main_size > 0 and self.c_memory_main_used > 0:
            self.c_memory_percent_used = round(
                self.c_memory_main_used / self.c_memory_main_size, 1
            )
        if self.c_current_load > 0 and self.c_desired_load > 0:
            self.c_current_desired_load_variance = round(
                self.c_current_load / self.c_desired_load, 2
            )

        if self.c_http_successful_txns > 0:
            self.c_transaction_error_percentage = (
                self.c_http_unsuccessful_txns + self.c_http_aborted_txns
            ) / self.c_http_successful_txns
        return True

    def assign_server_run_stats(self, server_stats):
        self.s_rx_bandwidth = server_stats.get("driver", {}).get("rxBandwidth", 0)
        self.s_rx_packet_count = server_stats.get("driver", {}).get("rxPacketCount", 0)
        self.s_rx_packet_rate = server_stats.get("driver", {}).get("rxPacketRate", 0)
        self.s_tx_bandwidth = server_stats.get("driver", {}).get("txBandwidth", 0)
        self.s_tx_packet_count = server_stats.get("driver", {}).get("txPacketCount", 0)
        self.s_tx_packet_rate = server_stats.get("driver", {}).get("txPacketRate", 0)
        self.s_memory_main_size = server_stats.get("memory", {}).get("mainPoolSize", 0)
        self.s_memory_main_used = server_stats.get("memory", {}).get("mainPoolUsed", 0)
        self.s_memory_packetmem_used = server_stats.get("memory", {}).get(
            "packetMemoryUsed", 0
        )
        self.s_memory_rcv_queue_length = server_stats.get("memory", {}).get(
            "rcvQueueLength", 0
        )
        self.s_memory_avg_cpu = round(
            server_stats.get("memory", {}).get("cpuUtilized", 0), 1
        )
        self.s_tcp_closed_error = server_stats.get("sum", {}).get("closedWithError", 0)
        self.s_tcp_closed = server_stats.get("sum", {}).get("closedWithNoError", 0)
        self.s_tcp_closed_reset = server_stats.get("sum", {}).get("closedWithReset", 0)

        if self.s_memory_main_size > 0 and self.s_memory_main_used > 0:
            self.s_memory_percent_used = round(
                self.s_memory_main_used / self.s_memory_main_size, 1
            )
        return True

    def print_test_status(self):
        status = (
            f"{self.timer}s -status: {self.status} -sub status: {self.sub_status} "
            f"-progress: {self.progress} -seconds elapsed: {self.time_elapsed} "
            f"-remaining: {self.time_remaining}"
        )
        print(status)

    def print_test_stats(self):
        stats = (
            f"{self.time_elapsed}s {self.phase} -load: {self.c_current_load:,}/{self.c_desired_load:,} "
            f"-current/desired var: {self.c_current_desired_load_variance} "
            f"-current avg/max var: {self.rolling_tps.avg_max_load_variance} "
            f"\n-tps: {self.c_http_successful_txns_sec:,} -tps stable: {self.rolling_tps.stable} "
            f"-tps cur avg: {self.rolling_tps.avg_val:,} -tps prev: {self.rolling_tps.avg_val_last:,} "
            f"-delta tps: {self.rolling_tps.increase_avg} -tps list:{self.rolling_tps.list} "
            f"\n-cps: {self.c_tcp_established_conn_rate:,} -cps stable: {self.rolling_cps.stable} "
            f"-cps cur avg: {self.rolling_cps.avg_val:,} -cps prev: {self.rolling_cps.avg_val_last:,} "
            f"-delta cps: {self.rolling_cps.increase_avg} -cps list:{self.rolling_cps.list} "
            f"\n-conns: {self.c_tcp_established_conns:,} -conns stable: {self.rolling_conns.stable} "
            f"-conns cur avg: {self.rolling_conns.avg_val:,} -conns prev: {self.rolling_conns.avg_val_last:,} "
            f"-delta conns: {self.rolling_cps.increase_avg} -conns list:{self.rolling_conns.list} "
            f"\n-bw: {self.c_total_bandwidth:,} -bw stable: {self.rolling_bw.stable} "
            f"-bw cur avg: {self.rolling_bw.avg_val:,} -bw prev: {self.rolling_bw.avg_val_last:,} "
            f"-delta bw: {self.rolling_bw.increase_avg} -bw list:{self.rolling_bw.list} "
            f"\n-ttfb: {self.c_tcp_avg_ttfb:,} -ttfb stable: {self.rolling_ttfb.stable} "
            f"-ttfb cur avg: {self.rolling_ttfb.avg_val:,} -ttfb prev: {self.rolling_ttfb.avg_val_last:,} "
            f"-delta ttfb: {self.rolling_ttfb.increase_avg} -ttfb list:{self.rolling_ttfb.list} "
            # f"\n-total bw: {self.c_total_bandwidth:,} -rx bw: {self.c_rx_bandwidth:,}"
            # f" tx bw: {self.c_tx_bandwidth:,}"
            # f"\n-ttfb cur avg: {self.rolling_ttfb.avg_val} -ttfb prev: {self.rolling_ttfb.avg_val_last} "
            # f"-delta ttfb: {self.rolling_ttfb.increase_avg} -ttfb list:{self.rolling_ttfb.list}"
        )
        print(stats)
        log.debug(stats)

    def wait_for_running_status(self):
        """
        Wait for the current test to return a 'running' status.
        :return: True if no statements failed and there were no exceptions. False otherwise.
        """
        log.debug("Inside the RunTest/wait_for_running_status method.")
        i = 0
        while True:
            time.sleep(4)
            self.timer = int(round(time.time() - self.start_time))
            i += 4
            if not self.update_test_run():
                return False
            if self.status == "running":
                print(f"{self.timer}s - status: {self.status}")
                break

            print(
                f"{self.timer}s - status: {self.status}  sub status: {self.sub_status}"
            )
            if self.status in {"failed", "finished"}:
                log.error("Test failed")
                return False
            # check to see if another test with the same ID is running
            # (can happen due to requests retry)
            if i > 120 and self.status == "waiting":
                self.check_running_tests()
            # stop after 1800 seconds of waiting
            if i > 1800:
                log.error(
                    "Waited for 1800 seconds, test did not transition to a running status."
                )
                return False
        self.time_to_run = self.timer
        log.debug(f"Test {self.name} successfully went to running status.")
        log.debug(json.dumps(self.test_run_update, indent=4))
        self.run_id = self.test_run_update.get("runId")
        self.report_link = (
            "https://"
            + self.cf.controller_ip
            + "/#results/"
            + self.type_v1
            + "/"
            + self.run_id
        )
        return True

    def check_running_tests(self):
        """Checks if tests with same ID is running and changes control to this test
        This function can be triggered if waiting status is too long because the requests module retry mechanism has
        kicked off two duplicate tests in error. It will look for matching running tests and switch control over to the
        already running duplicate test.
        :return: None
        """
        # get list of run IDs and test IDs with status
        test_runs = self.cf.list_test_runs()
        # look for running status and compare ID
        for run in test_runs:
            if run["status"] == "running":
                log.debug(
                    f"check_running_tests found running test: {json.dumps(run, indent=4)}"
                )
                # if waiting and running test IDs match, change the running test
                if self.test_id == run["testId"]:
                    log.debug(
                        f"check_running_tests found matching test_id {self.test_id}"
                    )
                    # stop current waiting test
                    response = self.cf.stop_test(self.id)
                    log.debug(
                        f"change_running_test, stopped duplicate waiting test: {response}"
                    )
                    # change over to running test
                    self.id = run["id"]
                else:
                    log.debug(
                        f"check_running_tests test_id: {self.test_id} "
                        f"does not match running test_id: {run['testId']}"
                    )

    def wait_for_running_sub_status(self):
        """
        Wait for the current test to return a 'None' sub status.
        :return: True if no statements failed and there were no exceptions. False otherwise.
        """
        log.debug("Inside the RunTest/wait_for_running_sub_status method.")
        i = 0
        while True:
            time.sleep(4)
            self.timer = int(round(time.time() - self.start_time))
            i += 4
            if not self.update_test_run():
                return False
            print(
                f"{self.timer}s - status: {self.status}  sub status: {self.sub_status}"
            )
            if self.sub_status is None:
                break

            if self.status in {"failed", "finished"}:
                log.error("Test failed")
                return False
            # stop after 0 seconds of waiting
            if i > 360:
                log.error(
                    "Waited for 360 seconds, test did not transition to traffic state."
                )
                return False
        self.time_to_start = self.timer - self.time_to_run
        log.debug(f"Test {self.name} successfully went to traffic state.")
        log.debug(json.dumps(self.test_run_update, indent=4))
        return True

    def stop_wait_for_finished_status(self):
        """
        Stop and wait for the current test to return a 'finished' status.
        :return: True if no statements failed and there were no exceptions.
         False otherwise.
        """
        log.debug("Inside the stop_test/wait_for_finished_status method.")
        self.time_to_stop_start = self.timer
        if self.status == "running":
            self.cf.stop_test(self.id)

        i = 0
        while True:
            time.sleep(4)
            self.timer = int(round(time.time() - self.start_time))
            i += 4
            if not self.update_test_run():
                return False
            if self.status in {"stopped", "finished", "failed"}:
                print(f"{self.timer} status: {self.status}")
                break
            if self.status == "failed":
                print(f"{self.timer} status: {self.status}")
                return False

            print(
                f"{self.timer}s - status: {self.status}  sub status: {self.sub_status}"
            )
            if i > 1800:
                error_msg = (
                    "Waited for 1800 seconds, "
                    "test did not transition to a finished status."
                )
                log.error(error_msg)
                print(error_msg)
                return False
        self.time_to_stop = self.timer - self.time_to_stop_start
        log.debug(
            f"Test {self.name} successfully went to finished status in "
            f"{self.time_to_stop} seconds."
        )
        return True

    def wait_for_test_activity(self):
        """
        Wait for the current test to show activity - metric(s) different than 0.
        :return: True if no statements failed and there were no exceptions.
        False otherwise.
        """
        log.debug("Inside the RunTest/wait_for_test_activity method.")
        test_generates_activity = False
        i = 0
        while not test_generates_activity:
            time.sleep(4)
            i = i + 4
            self.timer = int(round(time.time() - self.start_time))
            self.update_test_run()
            self.update_run_stats()
            self.print_test_status()

            # moved to wait_for_running_sub_status function
            # if self.sub_status is None:
            #     self.print_test_stats()

            if self.c_http_successful_txns_sec > 0:
                test_generates_activity = True
            if self.status in {"failed", "finished"}:
                log.error("Test failed")
                return False
            if i > 180:
                error_msg = (
                    "Waited for 180 seconds, test did not have successful transactions"
                )
                log.error(error_msg)
                print(error_msg)
                return False
        self.time_to_activity = self.timer - self.time_to_start - self.time_to_run
        return True

    @staticmethod
    def countdown(t):
        """countdown function

        Can be used after load increase for results to update

        :param t: countdown in seconds
        :return: None
        """
        while t:
            mins, secs = divmod(t, 60)
            time_format = "{:02d}:{:02d}".format(mins, secs)
            print(time_format, end="\r")
            time.sleep(1)
            t -= 1

    def goal_seek(self):
        log.info(f"In goal_seek function")
        if self.c_current_load == 0:
            self.stop = True
            log.info(f"goal_seek stop, c_current_load == 0")
            return False
        if self.first_load_increase:
            self.first_load_increase = False
            new_load = self.c_current_load + (
                self.in_incr_low * self.in_capacity_adjust
            )
        else:
            if self.test_config["config"]["loadSpecification"]["type"].lower() in {
                "simusers",
                "simusers/second",
            }:
                new_load = self.goal_seek_set_simuser()
                log.info(f"new_load = {new_load}")
            elif self.test_config["config"]["loadSpecification"]["type"].lower() in {
                "bandwidth",
                "connections",
                "connections/second",
            }:
                new_load = self.goal_seek_set_default()
                log.info(f"new_load = {new_load}")
            else:
                report_error = f"Unknown load type: {self.test_config['config']['loadSpecification']['type']}"
                log.error(report_error)
                print(report_error)
                return False

        if new_load is False:
            log.info(
                f"Config load spec type: {self.test_config['config']['loadSpecification']['type']}"
            )
            log.info(f"Goal_seek return, new_load is False")
            return False

        log_msg = f"\nchanging load from: {self.c_current_load} to: {new_load}  status: {self.status}"
        log.info(log_msg)
        print(log_msg)
        try:
            self.cf.change_load(self.id, new_load)
            self.rolling_tps.load_increase_complete()
            self.rolling_ttfb.load_increase_complete()
            self.rolling_current_load.load_increase_complete()
            self.rolling_cps.load_increase_complete()
            self.rolling_conns.load_increase_complete()
            self.rolling_bw.load_increase_complete()
        except Exception as detailed_exception:
            log.error(
                f"Exception occurred when changing test: " f"\n<{detailed_exception}>"
            )
        self.countdown(20)
        return True

    def goal_seek_set_default(self):
        set_load = 0
        if self.c_current_desired_load_variance >= 0.97:
            if self.c_current_load <= self.in_threshold_low:
                set_load = self.c_current_load + (
                    self.in_incr_low * self.in_capacity_adjust
                )
            elif self.c_current_load <= self.in_threshold_med:
                set_load = self.c_current_load + (
                    self.in_incr_med * self.in_capacity_adjust
                )
            elif self.c_current_load <= self.in_threshold_high:
                set_load = self.c_current_load + (
                    self.in_incr_high * self.in_capacity_adjust
                )
            elif self.c_current_load > self.in_threshold_high:
                return False
        else:
            return False
        if self.in_threshold_high < set_load:
            if self.c_current_desired_load_variance > 0.99:
                return False
            else:
                set_load = self.in_threshold_high
        return set_load

    def goal_seek_set_simuser(self):
        log.info(f"in goal_seek_set_simuser function")
        set_load = 0
        if self.rolling_tps.increase_avg >= self.in_threshold_low:
            set_load = self.c_current_load + (
                self.in_incr_low * self.in_capacity_adjust
            )
        elif self.rolling_tps.increase_avg >= self.in_threshold_med:
            set_load = self.c_current_load + (
                self.in_incr_med * self.in_capacity_adjust
            )
        elif self.rolling_tps.increase_avg >= self.in_threshold_high:
            set_load = self.c_current_load + (
                self.in_incr_high * self.in_capacity_adjust
            )
        elif self.rolling_tps.increase_avg < self.in_threshold_high:
            log.info(
                f"rolling_tps.increase_avg < in_threshold_high, "
                f"{self.rolling_tps.increase_avg} < {self.in_threshold_high}"
            )
            return False
        if self.rolling_tps.avg_max_load_variance < 0.97:
            set_load = self.c_current_load
            self.max_load_reached = True
        log.info(
            f"set_load = {set_load}  rolling_tps.avg_max_load_variance: {self.rolling_tps.avg_max_load_variance}"
        )
        return set_load

    def update_rolling_averages(self):
        """Updates rolling statistics averages used to make test control decisions

        :return: None
        """
        self.rolling_tps.update(self.c_http_successful_txns_sec)
        self.rolling_tps.check_if_stable(self.max_var_reference)

        self.rolling_ttfb.update(self.c_tcp_avg_ttfb)
        self.rolling_ttfb.check_if_stable(self.max_var_reference)

        self.rolling_current_load.update(self.c_current_load)
        self.rolling_current_load.check_if_stable(self.max_var_reference)

        self.rolling_cps.update(self.c_tcp_established_conn_rate)
        self.rolling_cps.check_if_stable(self.max_var_reference)

        self.rolling_conns.update(self.c_tcp_established_conns)
        self.rolling_conns.check_if_stable(self.max_var_reference)

        self.rolling_bw.update(self.c_total_bandwidth)
        self.rolling_bw.check_if_stable(self.max_var_reference)

        self.rolling_count_since_goal_seek.update(1)
        self.rolling_count_since_goal_seek.check_if_stable(0)

    def control_test(self):
        """Main test control

        Runs test. Start by checking if test is in running state followed by checking
        for successful connections.
        First updates stats, checks the phase test is in based on elapsed time, then updates
        rolloing averages.

        :return: True if test completed successfully
        """
        # exit control_test if test does not go into running state
        if not self.wait_for_running_status():
            log.info(f"control_test end, wait_for_running_status False")
            return False
            # exit control_test if test does not go into running state
        if not self.wait_for_running_sub_status():
            log.info(f"control_test end, wait_for_running_sub_status False")
            return False
        # exit control_test if test does have successful transactions
        if not self.wait_for_test_activity():
            self.stop_wait_for_finished_status()
            log.info(f"control_test end, wait_for_test_activity False")
            return False
        # test control loop - runs until self.stop is set to True
        while not self.stop:
            self.update_run_stats()
            self.update_phase()
            # stop test if time_remaining returned from controller == 0
            if self.time_remaining == 0:
                self.phase = "timeout"
                log.info(f"control_test end, time_remaining == 0")
                self.stop = True
            # stop goal seeking test if time remaining is less than 30s
            if self.time_remaining < 30 and self.in_goal_seek:
                self.phase = "timeout"
                log.info(f"control_test end, time_remaining < 30")
                self.stop = True
            if self.phase == "finished":
                log.info(f"control_test end, over duration time > phase: finished")
                self.stop = True
            self.update_rolling_averages()
            # print stats if test is running
            if self.sub_status is None:
                self.print_test_stats()
                self.save_results()
            if self.in_goal_seek:  # checks if goal seeking is selected for a test
                self.control_test_goal_seek()
            print(f"")
            time.sleep(4)
        # if goal_seek is yes enter sustained steady phase
        if self.in_goal_seek and self.in_sustain_period > 0:
            self.sustain_test()
        # stop test and wait for finished status
        if self.stop_wait_for_finished_status():
            self.time_to_stop = self.timer - self.time_to_stop_start
            self.save_results()
            return True
        return False

    def control_test_goal_seek(self):
        log.info(
            f"rolling_count_list stable: {self.rolling_count_since_goal_seek.stable} "
            f"{self.rolling_count_since_goal_seek.list} "
            f"tps_list stable: {self.rolling_tps.stable} {self.rolling_tps.list}"
        )
        if self.phase is not "goalseek":
            log.info(f"phase {self.phase} is not 'goalseek', "
                     f"returning from contol_test_goal_seek")
            return
        elif self.rolling_tps.stable and self.rolling_count_since_goal_seek.stable:
            if self.max_load_reached:
                log.info(f"control_test end, max_load_reached")
                self.stop = True
            else:
                if self.goal_seek():
                    # reset rolling count > no load increase until
                    # at least the window size interval.
                    # allows stats to stabilize after an increase
                    self.rolling_count_since_goal_seek.reset()
                else:
                    log.info(f"control_test end, goal_seek False")
                    self.stop = True

    def sustain_test(self):
        self.phase = "steady"
        while self.in_sustain_period > 0:
            self.timer = int(round(time.time() - self.start_time))
            sustain_period_loop_time_start = time.time()
            self.update_run_stats()
            if self.time_remaining < 30 and self.in_goal_seek:
                self.phase = "timeout"
                self.in_sustain_period = 0
                log.info(f"sustain_test end, time_remaining < 30")
            # self.update_averages()
            print(f"sustain period time left: {int(self.in_sustain_period)}")

            # print stats if test is running
            if self.sub_status is None:
                self.print_test_stats()
                self.save_results()

            time.sleep(4)
            self.in_sustain_period = self.in_sustain_period - (
                time.time() - sustain_period_loop_time_start
            )
        self.phase = "stopping"
        # self.stop_wait_for_finished_status()
        return True

    def save_results(self):

        csv_list = [
            self.in_name,
            self.time_elapsed,
            self.phase,
            self.c_current_load,
            self.c_desired_load,
            self.c_http_successful_txns_sec,
            self.rolling_tps.stable,
            self.rolling_tps.increase_avg,
            self.c_http_successful_txns,
            self.c_http_unsuccessful_txns,
            self.c_http_aborted_txns,
            self.c_transaction_error_percentage,
            self.c_tcp_established_conn_rate,
            self.c_tcp_established_conns,
            self.c_tcp_avg_tt_synack,
            self.c_tcp_avg_ttfb,
            self.rolling_ttfb.increase_avg,
            self.c_url_avg_response_time,
            self.c_tcp_cumulative_established_conns,
            self.c_tcp_cumulative_attempted_conns,
            self.c_total_bandwidth,
            self.c_rx_bandwidth,
            self.c_tx_bandwidth,
            self.c_rx_packet_rate,
            self.c_tx_packet_rate,
            self.s_tcp_closed,
            self.s_tcp_closed_reset,
            self.s_tcp_closed_error,
            self.c_loadspec_avg_cpu,
            self.c_memory_percent_used,
            self.c_memory_packetmem_used,
            self.c_memory_rcv_queue_length,
            self.s_memory_avg_cpu,
            self.s_memory_percent_used,
            self.s_memory_packetmem_used,
            self.s_memory_rcv_queue_length,
            self.type_v1,
            self.type_v2,
            self.in_load_type,
            self.test_id,
            self.id,
            self.time_to_run,
            self.time_to_start,
            self.time_to_activity,
            self.time_to_stop,
            self.report_link,
        ]
        self.result_file.append_file(csv_list)


class DetailedCsvReport:
    def __init__(self, report_location):
        log.debug("Initializing detailed csv result files.")
        self.time_stamp = time.strftime("%Y%m%d-%H%M")
        self.report_csv_file = report_location / f"{self.time_stamp}_Detailed.csv"
        self.columns = [
            "test_name",
            "seconds",
            "state",
            "current_load",
            "desired_load",
            "tps",
            "tps_stable",
            "tps_delta",
            "successful_txn",
            "unsuccessful_txn",
            "aborted_txn",
            "txn_error_rate",
            "cps",
            "open_conns",
            "tcp_avg_tt_synack",
            "tcp_avg_ttfb",
            "ttfb_delta",
            "url_response_time",
            "total_tcp_established",
            "total_tcp_attempted",
            "total_bandwidth",
            "rx_bandwidth",
            "tx_bandwidth",
            "rx_packet_rate",
            "tx_packet_rate",
            "tcp_closed",
            "tcp_reset",
            "tcp_error",
            "client_cpu",
            "client_mem",
            "client_pkt_mem",
            "client_rcv_queue",
            "server_cpu",
            "server_mem",
            "server_pkt_mem",
            "server_rcv_queue",
            "test_type_v1",
            "test_type_v2",
            "load_type",
            "test_id",
            "run_id",
            "t_run",
            "t_start",
            "t_tx",
            "t_stop",
            "report",
        ]

    def append_columns(self):
        """
        Appends the column headers to the detailed report file.
        :return: no specific return value.
        """
        try:
            csv_header = ",".join(map(str, self.columns)) + "\n"
            with open(self.report_csv_file, "a") as f:
                f.write(csv_header)
        except Exception as detailed_exception:
            log.error(
                f"Exception occurred  writing to the detailed report file: \n<{detailed_exception}>\n"
            )
        log.debug(
            f"Successfully appended columns to the detailed report file: {self.report_csv_file}."
        )

    def append_file(self, csv_list):
        """
        Appends the detailed report csv file with csv_line.
        :param csv_list: items to be appended as line to the file.
        :return: no specific return value.
        """
        try:
            csv_line = ",".join(map(str, csv_list)) + "\n"
            with open(self.report_csv_file, "a") as f:
                f.write(csv_line)
        except Exception as detailed_exception:
            log.error(
                f"Exception occurred  writing to the detailed report file: \n<{detailed_exception}>\n"
            )


class Report:
    def __init__(self, report_csv_file, column_order):
        self.report_csv_file = report_csv_file
        self.col_order = column_order
        self.df_base = pd.read_csv(self.report_csv_file)
        self.df_steady = self.df_base[self.df_base.state == "steady"].copy()
        self.unique_tests = self.df_base["test_name"].unique().tolist()
        self.results = []
        self.process_results()
        self.format_results()
        self.df_results = pd.DataFrame(self.results)
        self.df_results = self.df_results.reindex(columns=self.col_order)
        self.df_filter = pd.DataFrame(self.df_results)

    def process_results(self):
        for name in self.unique_tests:
            d = {}
            d["test_name"] = name

            # get mean values from steady state
            mean_cols = [
                "cps",
                "tps",
                "total_bandwidth",
                "open_conns",
                "tcp_avg_tt_synack",
                "tcp_avg_ttfb",
                "url_response_time",
                "client_cpu",
                "client_pkt_mem",
                "client_rcv_queue",
                "server_cpu",
                "server_pkt_mem",
                "server_rcv_queue",
            ]
            for col in mean_cols:
                d[col] = self.df_steady.loc[
                    self.df_steady["test_name"] == name, col
                ].mean()

            # get maximum values for all states
            max_cols = [
                "successful_txn",
                "unsuccessful_txn",
                "aborted_txn",
                "total_tcp_established",
                "total_tcp_attempted",
                "seconds",
                "current_load",
                "t_run",
                "t_start",
                "t_tx",
                "t_stop",
            ]
            for col in max_cols:
                d[col] = self.df_base.loc[self.df_base["test_name"] == name, col].max()

            max_steady_cols = ["seconds"]
            for col in max_steady_cols:
                d[col] = self.df_steady.loc[
                    self.df_steady["test_name"] == name, col
                ].max()

            # checks steady vs. all state max, add _max to column name
            max_compare_cols = ["cps", "tps", "total_bandwidth"]
            for col in max_compare_cols:
                col_name = col + "_max"
                d[col_name] = self.df_base.loc[
                    self.df_base["test_name"] == name, col
                ].max()
            # find current_load and seconds for max tps
            d["max_tps_load"] = self.df_base.loc[
                self.df_base["tps"] == d["tps_max"], "current_load"
            ].iloc[0]
            d["max_tps_seconds"] = self.df_base.loc[
                self.df_base["tps"] == d["tps_max"], "seconds"
            ].iloc[0]
            # get report link for current test
            d["report"] = self.df_base.loc[
                self.df_base["tps"] == d["tps_max"], "report"
            ].iloc[0]

            # find min and max tps from steady phase
            max_steady_compare = ["tps"]
            for col in max_steady_compare:
                col_name_min = col + "_stdy_min"
                col_name_max = col + "_stdy_max"
                col_name_delta = col + "_stdy_delta"
                d[col_name_min] = self.df_steady.loc[
                    self.df_steady["test_name"] == name, col
                ].min()
                d[col_name_max] = self.df_steady.loc[
                    self.df_steady["test_name"] == name, col
                ].max()

                if d[col_name_min] != 0:
                    d[col_name_delta] = (
                        (d[col_name_max] - d[col_name_min]) / d[col_name_min]
                    ) * 100

                    d[col_name_delta] = round(d[col_name_delta], 3)
                else:
                    d[col_name_delta] = 0

            self.results.append(d)

    def reset_df_filter(self):
        self.df_filter = pd.DataFrame(self.df_results)

    def filter_rows_containing(self, test_name_contains):
        if test_name_contains is not None:
            self.df_filter = self.df_filter[
                self.df_filter.test_name.str.contains(test_name_contains)
            ].copy()

    def filter_columns(self, filtered_columns):
        if filtered_columns is not None:
            self.df_filter.drop(
                self.df_filter.columns.difference(filtered_columns), 1, inplace=True
            )

    def format_results(self):
        for row_num, row in enumerate(self.results):
            for key, value in row.items():
                if key in {
                    "cps",
                    "tps",
                    "total_bandwidth",
                    "open_conns",
                    "successful_txn",
                    "unsuccessful_txn",
                    "aborted_txn",
                    "total_tcp_established",
                    "total_tcp_attempted",
                    "tps_stdy_min",
                    "tps_stdy_max",
                    "cps_max",
                    "tps_max",
                    "total_bandwidth_max",
                    "max_tps_load",
                    "client_mem",
                    "client_pkt_mem",
                    "client_rcv_queue",
                    "server_mem",
                    "server_pkt_mem",
                    "server_rcv_queue",
                    "t_run",
                    "t_start",
                    "t_tx",
                    "t_stop",
                }:
                    self.results[row_num][key] = f"{value:,.0f}"
                elif key in {
                    "tcp_avg_ttfb",
                    "url_response_time",
                    "tcp_avg_tt_synack",
                    "client_cpu",
                    "server_cpu",
                }:
                    self.results[row_num][key] = f"{value:,.1f}"
                elif key in {"tps_stdy_delta"}:
                    self.results[row_num][key] = f"{value:,.2f}"
                elif key in {"report"}:
                    self.results[row_num][key] = f'<a href="{value}">link</a>'

    @staticmethod
    def style_a():
        styles = [
            # table properties
            dict(
                selector=" ",
                props=[
                    ("margin", "0"),
                    ("width", "100%"),
                    ("font-family", '"Helvetica", "Arial", sans-serif'),
                    ("border-collapse", "collapse"),
                    ("border", "none"),
                    ("border", "2px solid #ccf"),
                    # ("min-width", "600px"),
                    ("overflow", "auto"),
                    ("overflow-x", "auto"),
                ],
            ),
            # header color - optional
            dict(
                selector="thead",
                props=[
                    ("background-color", "SkyBlue"),
                    ("width", "100%")
                    # ("display", "table") # adds fixed scrollbar
                    # ("position", "fixed")
                ],
            ),
            # background shading
            dict(
                selector="tbody tr:nth-child(even)",
                props=[("background-color", "#fff")],
            ),
            dict(
                selector="tbody tr:nth-child(odd)", props=[("background-color", "#eee")]
            ),
            # cell spacing
            dict(selector="td", props=[("padding", ".5em")]),
            # header cell properties
            dict(
                selector="th",
                props=[
                    ("font-size", "100%"),
                    ("text-align", "center"),
                    ("min-width", "25px"),
                    ("max-width", "50px"),
                    ("word-wrap", "break-word"),
                ],
            ),
            # render hover last to override background-color
            dict(selector="tbody tr:hover", props=[("background-color", "SkyBlue")]),
        ]
        return styles

    def html_table(self, selected_style):
        # Style
        props = {
            "test_name": {"width": "20em", "min-width": "14em", "text-align": "left"},
            "cps": {"width": "6em", "min-width": "5em", "text-align": "right"},
            "tps": {"width": "6em", "min-width": "5em", "text-align": "right"},
            "cps_max": {"width": "6em", "min-width": "5em", "text-align": "right"},
            "tps_max": {"width": "6em", "min-width": "5em", "text-align": "right"},
            "total_bandwidth": {
                "width": "8em",
                "min-width": "7em",
                "text-align": "right",
            },
            "total_bandwidth_max": {
                "width": "8em",
                "min-width": "7em",
                "text-align": "right",
            },
            "open_conns": {"width": "8em", "min-width": "7em", "text-align": "right"},
            "tcp_avg_tt_synack": {
                "width": "3.7em",
                "min-width": "3.7em",
                "text-align": "right",
            },
            "tcp_avg_ttfb": {
                "width": "3.7em",
                "min-width": "3.7em",
                "text-align": "right",
            },
            "url_response_time": {
                "width": "3.7em",
                "min-width": "3.7em",
                "text-align": "right",
            },
            "report": {"width": "3.7em", "min-width": "3.7em", "text-align": "right"},
            "successful_txn": {
                "width": "8em",
                "min-width": "7em",
                "text-align": "right",
            },
            "total_tcp_established": {
                "width": "5em",
                "min-width": "5em",
                "text-align": "right",
            },
            "total_tcp_attempted": {
                "width": "5em",
                "min-width": "5em",
                "text-align": "right",
            },
            "seconds": {"width": "3.7em", "min-width": "3.7em", "text-align": "right"},
            "tps_stdy_min": {"width": "3.2em", "min-width": "3.2em", "text-align": "right"},
            "tps_stdy_max": {"width": "3.2em", "min-width": "3.2em", "text-align": "right"},
            "tps_stdy_delta": {
                "width": "3.2em",
                "min-width": "3.2em",
                "text-align": "right",
            },
            "client_cpu": {"width": "3em", "min-width": "3em", "text-align": "right"},
            "server_cpu": {"width": "3em", "min-width": "3em", "text-align": "right"},
            "client_pkt_mem": {
                "width": "3.5em",
                "min-width": "3.5em",
                "text-align": "right",
            },
            "client_rcv_queue": {
                "width": "3.5em",
                "min-width": "3.5em",
                "text-align": "right",
            },
            "server_pkt_mem": {
                "width": "3.9em",
                "min-width": "3.9em",
                "text-align": "right",
            },
            "server_rcv_queue": {
                "width": "3.9em",
                "min-width": "3.9em",
                "text-align": "right",
            },
            "current_load": {
                "width": "3.7em",
                "min-width": "3.7em",
                "text-align": "right",
            },
            "unsuccessful_txn": {
                "width": "3.8em",
                "min-width": "3.8em",
                "text-align": "right",
            },
            "aborted_txn": {
                "width": "3.5em",
                "min-width": "3.5em",
                "text-align": "right",
            },
            "max_tps_seconds": {
                "width": "3.7em",
                "min-width": "3.7em",
                "text-align": "right",
            },
            "max_tps_load": {
                "width": "3.7em",
                "min-width": "3.7em",
                "text-align": "right",
            },
            "t_run": {"width": "3em", "min-width": "3.7em", "text-align": "right"},
            "t_start": {"width": "3em", "min-width": "3em", "text-align": "right"},
            "t_tx": {"width": "3em", "min-width": "3em", "text-align": "right"},
            "t_stop": {"width": "3em", "min-width": "3em", "text-align": "right"},
        }

        # html = ''
        all_columns = set(self.df_filter.columns)
        html = self.df_filter.style.set_properties(
            subset="test_name", **props["test_name"]
        )
        for k, v in props.items():
            if k in all_columns:
                html = html.set_properties(subset=k, **v)
        html = html.set_table_styles(selected_style).hide_index().render()

        return html
