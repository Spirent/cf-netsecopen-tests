import json
import logging
import time
import sys
import os
import numpy as np
import pandas as pd
import pathlib
import sys
import math

from dataclasses import dataclass

script_version = 1.80

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

@dataclass
class RunData:
    """Data class with default values used by RunTest"""
    test_id: str = 'test_id'
    type_v2: str = 'test_type'
    in_name: str = 'test_name'
    in_run: str = 'Y'
    in_load_type: str = 'loadspec_type'
    in_start_load: int = 7
    in_incr_low: int = 7
    in_incr_med: int = 5
    in_incr_high: int = 3
    in_duration: int = 1800
    in_startup: int = 5
    in_rampup: int = 10
    in_rampdown: int = 10
    in_shutdown: int = 10
    in_sustain_period: int = 30
    in_kpi_1: str = 'tps'
    in_kpi_2: str = 'cps'
    in_kpi_and_or: str = 'AND'
    in_threshold_low: float = 20.0
    in_threshold_med: float = 5.0
    in_threshold_high: float = 1.0
    variance_sample_size: int = 3
    in_max_variance: float = 0.03
    in_ramp_low: int = 60
    in_ramp_med: int = 40
    in_ramp_high: int = 20
    in_ramp_seek: bool = False
    in_ramp_seek_kpi: str = 'cps'
    in_ramp_seek_value: int = 1000
    in_ramp_step: int = 5
    ramp_seek_complete: bool = True

    living_simusers_max_bool: bool = False
    living_simusers_max: int = 1 
    simuser_birth_rate_max_bool: bool = False

    in_goal_seek: bool = False
    first_steady_interval: bool = True

    test_config: dict = None
    queue_id: str = 'id'
    queue_info: dict = None
    queue_capacity: int = 60
    core_count: int = 6
    port_count: int = 1
    client_port_count: int = 1
    server_port_count: int = 1
    client_core_count: int = 3
    client_portSystemId : str = ''
    in_capacity_adjust: any = 1
    load_constraints: dict = None

    test_run: dict = None
    test_run_update: dict = None

    id: dict = None
    score: str = ''
    grade: str = ''
    run_id: str = 'Test_name'
    status: str = 'status'  # main run status 'running'
    name: str = 'name'
    type_v1: str = 'type_v1'
    sub_status: str = None
    created_at: str = None
    updated_at: str = None
    started_at: str = None
    finished_at: str = None
    run_link: str = 'runlink'
    report_link = None
    sub_status = None  # subStatus -  none while running or not started
    progress: int = 0  # progress  -  0-100
    time_elapsed: int = 0  # timeElapsed  - seconds
    time_remaining: int = 0  # timeRemaining  - seconds

    c_rx_bandwidth: int = 0
    c_rx_packet_count: int = 0
    c_rx_packet_rate: int = 0
    c_rx_byte_rate: int = 0
    c_tx_bandwidth: int = 0
    c_tx_packet_count: int = 0
    c_tx_packet_rate: int = 0
    c_tx_byte_rate: int = 0
    c_total_byte_rate: int = 0
    c_total_packet_count: int = 0
    c_http_aborted_txns: int = 0
    c_http_aborted_txns_sec: int = 0
    c_http_attempted_txns: int = 0
    c_http_attempted_txns_sec: int = 0
    c_http_successful_txns: int = 0
    c_http_successful_txns_sec: int = 0
    c_http_unsuccessful_txns: int = 0
    c_http_unsuccessful_txns_sec: int = 0
    c_loadspec_avg_idle: int = 0
    c_loadspec_avg_cpu: int = 0
    c_memory_main_size: int = 0
    c_memory_main_used: int = 0
    c_memory_packetmem_used: int = 0
    c_memory_rcv_queue_length: int = 0
    c_simusers_alive: int = 0
    c_simusers_animating: int = 0
    c_simusers_blocking: int = 0
    c_simusers_sleeping: int = 0
    c_tcp_avg_ttfb: int = 0
    c_tcp_avg_tt_synack: int = 0
    c_tcp_cumulative_attempted_conns: int = 0
    c_tcp_cumulative_established_conns: int = 0
    c_url_avg_response_time: int = 0
    c_tcp_attempted_conn_rate: int = 0
    c_tcp_established_conn_rate: int = 0
    c_tcp_attempted_conns: int = 0
    c_tcp_established_conns: int = 0
    c_current_load: int = 0
    c_desired_load: int = 0
    c_total_bandwidth: int = 0
    c_memory_percent_used: int = 0
    c_current_desired_load_variance: float = 0.0
    c_current_max_load_variance: float = 0.0
    c_transaction_error_percentage: float = 0.0

    s_rx_bandwidth: int = 0
    s_rx_packet_count: int = 0
    s_rx_packet_rate: int = 0
    s_tx_bandwidth: int = 0
    s_tx_packet_count: int = 0
    s_tx_packet_rate: int = 0
    s_memory_main_size: int = 0
    s_memory_main_used: int = 0
    s_memory_packetmem_used: int = 0
    s_memory_rcv_queue_length: int = 0
    s_memory_avg_cpu: int = 0
    s_tcp_closed_error: int = 0
    s_tcp_closed: int = 0
    s_tcp_closed_reset: int = 0
    s_memory_percent_used: int = 0

    first_ramp_load_increase: bool = True
    first_goal_load_increase: bool = True
    minimum_goal_seek_count: int = 1
    goal_seek_count: int = 0
    max_load_reached: bool = False
    max_load: int = 0
    stop: bool = False  # test loop control
    phase: str = None  # time phase of test: ramp up, steady ramp down

    # rolling statistics
    rolling_sample_size: int = 3
    max_var_reference: float = 0.03
    rolling_tps: RollingStats = None
    rolling_ttfb: RollingStats = None
    rolling_current_load: RollingStats = None
    rolling_count_since_goal_seek: RollingStats = None
    rolling_cps: RollingStats = None
    rolling_conns: RollingStats = None
    rolling_bw: RollingStats = None

    kpi_1: any = None
    kpi_2: any = None
    kpi_1_stable: bool = True
    kpi_2_stable: bool = True
    kpi_1_list: list = None
    kpi_2_list: list = None
    ramp_seek_kpi: any = None

    start_time: any = None
    timer: any = None
    time_to_run: int = 0
    time_to_start: int = 0
    time_to_activity: int = 0
    time_to_stop_start: int = 0
    time_to_stop: int = 0
    test_started: bool = False

class CfOpenConns:
    def __init__(self, rt):
        self.rt = rt  # the CfRunTest object
        self.disabled = True
        self.got_startup_data = False
        self.first_new_load = True
        self.changed_load_highest = 0
        # power of 2 dividing the distance between starting open conns load and max load
        # (e.g.2**5 = 32 steps from current to max)
        self.steps_to_max = 3
        self.current_step = 1
        self.tracker_mapper = (
            ("setpoint", "c_desired_load"),
            ("load", "c_current_load"),
            ("memory", "c_memory_main_used"),
            ("cps", "c_tcp_established_conn_rate"),
        )
        self.tracker = {}

    def enable(self):
        self.disabled = False
        log.info("CfOpenConns enabled")

    def expect_unused(self, unused_point):
        log.warning(f"CfOpenConns surprise used: {unused_point}")

    def set_startup_data(self):
        if (
            self.disabled
            or self.got_startup_data
            or self.rt.rd.c_http_successful_txns_sec == 0
        ):
            return
        self.got_startup_data = True
        self.c_startup_mem = self.rt.rd.c_memory_main_used
        self.c_startup_load = self.rt.rd.c_current_load
        self.c_new_conns_mem = self.rt.rd.c_memory_main_size - self.c_startup_mem
        log.info(
            f"CfOpenConns -- c_startup_mem: {self.c_startup_mem}; c_startup_load: "
            f"{self.c_startup_load}; c_conns_mem: {self.c_new_conns_mem}"
        )

    def capture_goal_seek_iteration(self):
        if self.disabled:
            return
        t = time.time()
        self.tracker[t] = {}
        for key, data_name in self.tracker_mapper:
            exec(f"self.tracker[t]['{key}'] = self.rt.rd.{data_name}")
        log.debug(f"CfOpenConns -- {t-self.rt.rd.start_time:.2f}: {self.tracker[t]}")

    def skip_goal_seek(self):
        if self.disabled:
            return False
        if self.disabled:
            return False
        current = self.rt.rd.c_current_load
        desired = self.rt.rd.c_desired_load
        ratio = current / desired
        log.info(
            f"CfOpenConns -- current/desired load: {current:,}/{desired:,} "
            f"({ratio:.1%})"
        )
        diff = abs(ratio - 1)
        allowed = 0.015
        if diff > allowed:
            log.info(f"Skip load update, diff>allowed: {diff:.1%}>{allowed:.1%}")
            return True
        return False

    def dump_iteration_data(self, csv_file):
        if self.disabled:
            return
        field_names = ["time"] + [x[0] for x in self.tracker_mapper]
        dw = csv.DictWriter(csv_file, field_names)
        dw.writeheader()
        for time_key in self.tracker:
            row_dict = {"time": f"{time_key - self.rt.rd.start_time:.2f}"}
            row_dict.update(self.tracker[time_key])
            dw.writerow(row_dict)

    def is_load_type_conns(self):
        return not self.disabled

    def get_new_load(self):
        if (
            self.rt.rd.c_current_desired_load_variance >= 1.0
            and self.rt.rd.c_memory_percent_used < 100
            and self.rt.rd.s_memory_percent_used < 100
        ):
            pass
        else:
            self.rt.rd.max_load_reached = True
        if (
            self.rt.rd.rolling_conns.increase_avg == 0
            and self.rt.rd.c_memory_percent_used > 99.5
        ):
            self.rt.rd.max_load_reached = True
        if self.rt.rd.max_load_reached == True:
            log.info("CfOpenConns -- No more load increase; stop seeking.")
            return False
        if self.first_new_load:
            if self.rt.rd.c_current_load - self.c_startup_load > 0:
                self.c_mem_per_conn = (self.rt.rd.c_memory_main_used - self.c_startup_mem) / (
                    self.rt.rd.c_current_load - self.c_startup_load
                )
                self.inc_conns_within_c_mem = int(
                    0.95 * self.c_new_conns_mem / self.c_mem_per_conn
                )
                log.info(
                    f"CfOpenConns -- c_mem_per_conn: {self.c_mem_per_conn}; "
                    f"self.inc_conns_within_c_mem: {self.inc_conns_within_c_mem}"
                )
            self.first_new_load = False
        if self.rt.rd.c_memory_percent_used > 97:
            self.current_step = 0
            self.inc_conns_within_c_mem = self.rt.rd.in_incr_high * self.rt.rd.in_capacity_adjust
        elif self.current_step > self.steps_to_max and self.rt.rd.c_memory_percent_used <= 97:
            self.current_step = 1
            self.c_new_conns_mem = self.rt.rd.c_memory_main_size - self.rt.rd.c_memory_main_used
            self.inc_conns_within_c_mem = int(self.c_new_conns_mem / self.c_mem_per_conn)
        if self.current_step <= self.steps_to_max:
            binary_deductor = 1 / (2 ** self.current_step)
        # bincurrent_stepary deductor generates a progression like this: 1/2, 1/4, 1/8, ..., 0
        new_load = self.rt.rd.c_current_load +  int(binary_deductor * self.inc_conns_within_c_mem)
        log.info(
            f"CfOpenConns -- current_step: {self.current_step}; "
            f"cur load: {self.rt.rd.c_current_load}, new_load: {new_load}, add load: {binary_deductor * self.inc_conns_within_c_mem}"
        )
        self.current_step += 1
        if new_load < self.changed_load_highest:
            new_load = self.changed_load_highest
        else:
            self.changed_load_highest = new_load
        return new_load

class CfRunTest:
    def __init__(self, cf, rd, test_details, result_file, temp_file_dir):
        log.info(f"script version: {script_version}")
        self.cf = cf  # CfClient instance
        self.rd = rd
        #log.info(f"self.rd is: {self.rd}")
        self.ocj = CfOpenConns(self)  # special behavior for open conns tests
        self.result_file = result_file
        self.temp_dir = temp_file_dir
        self.test = test_details

    def init_sequence(self, cf, rd, test_details):
        self.init_input_csv(rd, test_details)

        rd.test_config = self.get_test_config(cf, rd)
        rd.queue_id = rd.test_config["config"]["queue"]["id"]
        rd.queue_info = self.get_queue(cf, rd.queue_id)
        log.info(f"queue info: \n{json.dumps(rd.queue_info, indent=4)}")
        self.init_simuser_birth_rate_max(rd)

        if not self.init_capacity_adj(rd):
            return False

        self.software_version_lookup(rd.queue_info)
        self.get_report_info(rd)
        self.result_file.make_report_dir(self.report_dir)
        self.result_file.make_report_csv_file(self.report_name)
        self.init_update_config_load(rd)
        self.update_config_load_controller(cf, rd)

        rd.test_run = self.start_test_run(cf, rd)
        self.init_test_run(rd, cf.controller_ip)

        self.init_rolling_stats(rd)
        # create entry in result file at the start of test
        self.save_results(rd)
        return True

    def init_input_csv(self, rd, test_details):
        rd.test_id = test_details["id"]
        rd.type_v2 = test_details["type"]
        rd.in_name = test_details["name"]
        rd.in_run = test_details["run"]
        rd.in_load_type = test_details["load_type"]
        rd.in_start_load = test_details["start_load"]
        rd.in_incr_low = int(test_details["incr_low"])
        rd.in_incr_med = int(test_details["incr_med"])
        rd.in_incr_high = int(test_details["incr_high"])
        rd.in_duration = int(test_details["duration"])
        rd.in_startup = int(test_details["startup"])
        rd.in_rampup = int(test_details["rampup"])
        rd.in_rampdown = int(test_details["rampdown"])
        rd.in_shutdown = int(test_details["shutdown"])
        rd.in_sustain_period = int(test_details["sustain_period"])
        rd.in_kpi_1 = test_details.get("kpi_1", "tps")
        rd.in_kpi_2 = test_details.get("kpi_2", "cps")
        rd.in_kpi_and_or = self.return_bool_true(test_details.get("kpi_and_or"), "AND")
        rd.in_threshold_low = float(test_details["low_threshold"])
        rd.in_threshold_med = float(test_details["med_threshold"])
        rd.in_threshold_high = float(test_details["high_threshold"])
        rd.in_sustain_period = int(test_details["sustain_period"])
        rd.variance_sample_size = int(test_details["variance_sample_size"])
        rd.in_max_variance = float(test_details["max_variance"])
        rd.in_ramp_low = int(test_details.get("ramp_low", 60))
        rd.in_ramp_med = int(test_details.get("ramp_med", 40))
        rd.in_ramp_high = int(test_details.get("ramp_high", 20))
        rd.in_capacity_adjust = test_details.get("capacity_adj", 1)

        rd.in_ramp_seek = self.if_in_set_true(test_details, "ramp_seek",
                                                {"true", "y", "yes"})
        rd.in_ramp_seek_kpi = test_details.get("ramp_kpi", "tps")
        rd.in_ramp_seek_value = int(test_details.get("ramp_value", 1))
        rd.in_ramp_step = int(test_details.get("ramp_step", 1))

        if not rd.in_ramp_seek:
            rd.ramp_seek_complete = True
        else:
            rd.ramp_seek_complete = False

        rd.living_simusers_max_bool = int(self.check_if_number(
            test_details.get("living_simusers_max", False)))
        rd.living_simusers_max = self.return_int_if_present(
            rd.living_simusers_max_bool,
            test_details.get("living_simusers_max", False))

        rd.in_goal_seek = test_details["goal_seek"]
        if rd.in_goal_seek.lower() in {"true", "y", "yes"}:
            rd.in_goal_seek = True
            rd.first_steady_interval = False
        else:
            rd.in_goal_seek = False
        
        rd.start_time = time.time()
        rd.timer = time.time() - rd.start_time

    def init_simuser_birth_rate_max(self, rd):
        if not (rd.type_v2 == "open_connections" and rd.in_load_type == "simusers"):
            self.test["simuser_birth_rate_max"] = "none"
            return
        sslTls_enabled = rd.test_config.get("config", {}).get("protocol", {}).get("supplemental", {}).get("sslTls", {}).get("enabled", False)
        if sslTls_enabled:
            self.test["simuser_birth_rate_max"] = 30
        else:
            self.test["simuser_birth_rate_max"] = 450
        rd.simuser_birth_rate_max_bool = self.check_if_number(
            self.test.get("simuser_birth_rate_max", False))
        rd.simuser_birth_rate_max = self.return_int_if_present(
            rd.simuser_birth_rate_max_bool,
            self.test.get("simuser_birth_rate_max", False))

    def init_capacity_adj(self, rd):
        rd.queue_capacity = int(rd.queue_info["capacity"])
        log.info(f"queue_capacity: {rd.queue_capacity}")
        if len(rd.queue_info["computeGroups"]) > 0:
            rd.core_count,rd.port_count = self.core_count_lookup_cg(rd.queue_info)
            log.info(f"core_count cg and port count cg: {rd.core_count, rd.port_count}")
            # self.capacity_adj_cg(rd)
        else:
            rd.core_count,rd.port_count = self.core_count_lookup_spr(rd.queue_info)
            log.info(f"core_count cg and port count cg: {rd.core_count, rd.port_count}")
            # self.capacity_adj_spr(rd)
        if not self.check_config(rd):
            return False
        if self.test["type"] == "advanced_mixed_traffic":
            rd.client_port_count = len(rd.test_config["config"]["relationships"])
            rd.server_port_count = len(rd.test_config["config"]["relationships"])
            rd.client_portSystemId = rd.test_config["config"]["relationships"][0]["client"]["portSystemId"]
        else:
            rd.client_port_count = len(rd.test_config["config"]["interfaces"]["client"])
            rd.server_port_count = len(rd.test_config["config"]["interfaces"]["server"])
            rd.client_portSystemId = rd.test_config["config"]["interfaces"]["client"][0]["portSystemId"]
        self.device_ip = rd.client_portSystemId.split("/", 1)[0]    
        log.info(f"client_port_count: {rd.client_port_count}")
        log.info(f"server_port_count: {rd.server_port_count}")
        rd.client_core_count = int(
            rd.core_count
            / rd.port_count
            * rd.client_port_count
        )
        log.info(f"client_core_count: {rd.client_core_count}")
        rd.in_capacity_adjust = self.check_capacity_adjust(
            rd.in_capacity_adjust,
            rd.in_load_type,
            rd.client_port_count,
            rd.client_core_count,
        )
        log.info(f"in_capacity_adjust: {rd.in_capacity_adjust}")
        rd.load_constraints = {"enabled": False}
        return True
        
    def check_config(self, rd):
        if self.test["type"] == "advanced_mixed_traffic":
            interfaces = rd.test_config["config"]["relationships"]
            information = "relationships"
        else:
            interfaces = rd.test_config["config"]["interfaces"]
            information = "interfaces"
        if len(interfaces) == 0:
            errormsg = f"No subnets/{information} assigned in test"
            log.debug(errormsg)
            print(errormsg)
            return False
        return True

    # def capacity_adj_cg(self, rd):
    #     rd.core_count = self.core_count_lookup_cg(rd.queue_info)
    #     log.info(f"core_count: {rd.core_count}")
    #     rd.client_port_count = len(rd.test_config["config"]["interfaces"]["client"])
    #     log.info(f"client_port_count: {rd.client_port_count}")
    #     rd.server_port_count = len(rd.test_config["config"]["interfaces"]["server"])
    #     log.info(f"server_port_count: {rd.server_port_count}")
    #     rd.client_core_count = int(
    #         rd.core_count
    #         / (rd.client_port_count + rd.server_port_count)
    #         * rd.client_port_count
    #     )
    #     log.info(f"client_core_count: {rd.client_core_count}")
    #     rd.in_capacity_adjust = self.check_capacity_adjust(
    #         rd.in_capacity_adjust,
    #         rd.in_load_type,
    #         rd.client_port_count,
    #         rd.client_core_count,
    #     )
    #     log.info(f"in_capacity_adjust: {rd.in_capacity_adjust}")
    #     rd.load_constraints = {"enabled": False}
        
    def init_update_config_load(self, rd):    
        if not self.update_config_load(rd):
            report_error = f"unknown load_type with test type"
            log.debug(report_error)
            print(report_error)

    def init_test_run(self, rd, controller_ip):
        if not rd.test_started:
            report_error = f"test did not start\n{json.dumps(rd.test_run, indent=4)}"
            log.debug(report_error)
            print(report_error)
        rd.test_run_update = None

        rd.id = rd.test_run.get("id")
        rd.queue_id = rd.test_run.get("queueId")
        rd.score = rd.test_run.get("score")
        rd.grade = rd.test_run.get("grade")
        rd.run_id = rd.test_run.get("runId")
        rd.status = rd.test_run.get("status")  # main run status 'running'
        rd.name = rd.test_run.get("test", {}).get("name")
        rd.type_v1 = rd.test_run.get("test", {}).get("type")
        rd.sub_status = rd.test_run.get("subStatus")
        rd.created_at = rd.test_run.get("createdAt")
        rd.updated_at = rd.test_run.get("updatedAt")
        rd.started_at = rd.test_run.get("startedAt")
        rd.finished_at = rd.test_run.get("finishedAt")
        rd.progress = rd.test_run.get("progress")
        rd.time_elapsed = rd.test_run.get("timeElapsed")
        rd.time_remaining = rd.test_run.get("timeRemaining")

        rd.run_link = (
            "https://"
            + controller_ip
            + "/#livecharts/"
            + rd.type_v1
            + "/"
            + rd.id
        )
        print(f"Live charts: {rd.run_link}")

    def init_rolling_stats(self, rd):
        # rolling statistics
        rd.rolling_sample_size = rd.variance_sample_size
        rd.max_var_reference = rd.in_max_variance
        rd.rolling_tps = RollingStats(rd.rolling_sample_size, 0)
        rd.rolling_ttfb = RollingStats(rd.rolling_sample_size, 1)
        rd.rolling_current_load = RollingStats(rd.rolling_sample_size, 0)
        rd.rolling_count_since_goal_seek = RollingStats(
            rd.rolling_sample_size, 1
        )  # round to 1 for > 0 avg
        rd.rolling_cps = RollingStats(rd.rolling_sample_size, 0)
        rd.rolling_conns = RollingStats(rd.rolling_sample_size, 0)
        rd.rolling_bw = RollingStats(rd.rolling_sample_size, 0)

        rd.kpi_1 = rd.rolling_tps
        rd.kpi_2 = rd.rolling_cps
        rd.kpi_1_stable = True
        rd.kpi_2_stable = True
        rd.kpi_1_list = []
        rd.kpi_2_list = []
        rd.ramp_seek_kpi = rd.rolling_tps

    @staticmethod
    def if_in_set_true(dict_var, dict_key, in_set):
        if dict_key in dict_var:
            var = dict_var[dict_key]
            if var.lower() in in_set:
                return True
        return False

    @staticmethod
    def check_if_number(in_value):
        if in_value == False or in_value == None:
            return False
        if isinstance(in_value, int) or isinstance(in_value, float):
            return True
        if isinstance(in_value, str):
            if in_value.isdigit():
                return True
        return False

    @staticmethod
    def return_int_if_present(present, value):
        if present:
            return int(value)

    def get_test_config(self, cf, rd):
        response = None
        try:
            response = cf.get_test(
                rd.type_v2, rd.test_id, self.temp_dir / "running_test_config.json"
            )
            log.debug(f"{json.dumps(response, indent=4)}")
        except Exception as detailed_exception:
            log.error(
                f"Exception occurred when retrieving the test: "
                f"\n<{detailed_exception}>"
            )
        return response

    def get_queue(self, cf, queue_id):
        response = None
        try:
            response = cf.get_queue(queue_id)
            # log.debug(f"{json.dumps(response, indent=4)}")
        except Exception as detailed_exception:
            log.error(
                f"Exception occurred when retrieving test queue information: "
                f"\n<{detailed_exception}>"
            )
        return response

    @staticmethod
    def core_count_lookup_cg(queue_info):
        cores = 0
        ports = 0
        for cg in queue_info["computeGroups"]:
            cores = cores + int(cg["cores"])
            ports = ports + len(cg["ports"])
        return cores,ports

    @staticmethod
    def core_count_lookup_spr(queue_info):
        cores = 0
        ports = 0
        for port in queue_info["ports"]:
            cores = cores + int(port["cores"])
        ports = queue_info["portCount"]
        return cores,ports

    def software_version_lookup(self, queue_info):
        self.model = ""
        self.software_version = ""
        self.divide_by_1000 = True
        for device in queue_info["devices"]:
            if device["ip"] == self.device_ip:
                self.device_info = device
                self.software_version = device["slots"][0]["computeGroups"][0]["software"]
                break
        if "l4l7lxc" in self.software_version:
            self.software_version = self.software_version.split("l4l7lxc")[1]
            self.model = "lxc"
        software_version_list = self.software_version.split(".")
        software_version_list = [int(i) for i in software_version_list]
        if self.model == "lxc":
            if software_version_list[0] <= 4:
                self.divide_by_1000 = False
            elif software_version_list[0] == 5 and software_version_list[1] < 7:
                self.divide_by_1000 = False
        else:
            if software_version_list[0] <= 19:
                self.divide_by_1000 = False
            elif software_version_list[0] == 20:
                if software_version_list[1] == 0:
                    self.divide_by_1000 = False
                elif software_version_list[1] == 1 and software_version_list[2] == 0:
                    self.divide_by_1000 = False
        log.info(f"software version: {self.software_version}")
        log.info(f"divide_by_1000: {self.divide_by_1000}")
        print(f"software version: {self.software_version}")

    def get_report_info(self, rd):
        self.device_mode = ""
        self.device_description = self.device_info["description"][4:]
        self.device_profile = self.device_info["slots"][0]["profile"]
        self.device_model = self.device_info["slots"][0]["model"][4:]
        for profile_info in ["Functional-", "Performance-", "Maximum-"]:
            if profile_info in self.device_profile:
                self.device_profile = self.device_profile.split(profile_info)[-1].strip("\n")
                break
        if "cfv" in self.device_description.lower():
            #waiting for issue CF-17490 fixing
            self.device_model = f"{self.device_model.rsplit('-', 1)[0]}-vCores-{rd.client_core_count*2}"
            self.report_dir = self.device_model
        else:
            self.report_dir = "_".join((self.device_model, self.device_profile))
        self.report_name = "_".join((self.device_ip, self.software_version))

    def update_startload_rampup_for_ec_sha384_on_cfv(self, rd):
        update_flag = False
        sslTls_hash = []
        if "cfv" in self.device_description.lower():
            sslTls_hash = rd.test_config.get("config", {}).get("protocol", {}).get("supplemental", {}).get("sslTls", {}).get("ciphers", [])
        if sslTls_hash:
            for each_hash in sslTls_hash:
                if "SHA384" in each_hash and "ECDHE" in each_hash:
                    update_flag = True
                    break
        if update_flag:
            if int(rd.in_start_load) < 8:
                rd.in_start_load = 8
            if self.test_type == "cps":
                if int(rd.in_rampup) < 120:
                    rd.in_rampup = 120
            if self.test_type == "tput":
                if int(rd.in_rampup) < 180:
                    rd.in_rampup = 180
        return

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

    def update_config_load(self, rd):
        load_type = rd.in_load_type.lower()
        test_type = self.test_type(rd)

        if test_type in {"tput", "emix", "amt"} and load_type == "simusers":
            load_key = "bandwidth"
            rd.in_load_type = "SimUsers"
        elif test_type in {"tput", "emix", "amt"} and load_type == "bandwidth":
            load_key = "bandwidth"
            rd.in_load_type = "Bandwidth"
        elif test_type == "tput" and load_type == "simusers/second":
            load_key = "bandwidth"
            rd.in_load_type = "SimUsers/Second"
        elif test_type == "cps" and load_type == "connections/second":
            load_key = "connectionsPerSecond"
            rd.in_load_type = "Connections/Second"
        elif test_type == "cps" and load_type == "simusers":
            load_key = "connectionsPerSecond"
            rd.in_load_type = "SimUsers"
        elif test_type == "cps" and load_type == "simusers/second":
            load_key = "connectionsPerSecond"
            rd.in_load_type = "SimUsers/Second"
        elif test_type == "conns" and load_type == "simusers":
            self.ocj.expect_unused('test_type == "conns" and load_type == "simusers"')
            load_key = "connections"
            rd.in_load_type = "SimUsers"
        elif test_type == "conns" and load_type == "connections":
            load_key = "connections"
            rd.in_load_type = "Connections"
        else:
            return False

        if test_type == "conns" and rd.in_goal_seek:
            self.ocj.enable()
        self.update_startload_rampup_for_ec_sha384_on_cfv(rd)
        rd.in_start_load = int(rd.in_start_load) * rd.in_capacity_adjust
        self.update_load_constraints(rd)
        load_update = {
            "config": {
                "loadSpecification": {
                    "duration": int(rd.in_duration),
                    "startup": int(rd.in_startup),
                    "rampup": int(rd.in_rampup),
                    "rampdown": int(rd.in_rampdown),
                    "shutdown": int(rd.in_shutdown),
                    load_key: int(rd.in_start_load),
                    "type": rd.in_load_type,
                    "constraints": rd.load_constraints,
                    # "constraints": {"enabled": False},
                }
            }
        }
        with open((self.temp_dir / "test_load_update.json"), "w") as f:
            json.dump(load_update, f, indent=4)
        return True

    def update_config_load_controller(self, cf, rd):
        response = cf.update_test(
            rd.type_v2, rd.test_id, self.temp_dir / "test_load_update.json"
        )
        log.info(f"{json.dumps(response, indent=4)}")
        rd.test_config = self.get_test_config(cf, rd)

    def update_load_constraints(self, rd):
        living = {"enabled": False}
        open_connections = {"enabled": False}
        birth_rate = {"enabled": False}
        connections_rate = {"enabled": False}
        constraints = False

        if rd.living_simusers_max_bool:
            constraints = True
            living = {
                "enabled": True,
                "max": rd.living_simusers_max
            }
        if rd.simuser_birth_rate_max_bool:
            constraints = True
            birth_rate = {
                "enabled": True,
                "max": rd.simuser_birth_rate_max * rd.in_capacity_adjust
            }
        if constraints:
            rd.load_constraints = {
                "enabled": True,
                "living": living,
                "openConnections": open_connections,
                "birthRate": birth_rate,
                "connectionsRate": connections_rate,
            }

    def test_type(self, rd):
        if rd.type_v2 == "http_throughput":
            test_type = "tput"
        elif rd.type_v2 == "http_connections_per_second":
            test_type = "cps"
        elif rd.type_v2 == "open_connections":
            test_type = "conns"
        elif rd.type_v2 == "emix":
            test_type = "emix"
        elif rd.type_v2 == "advanced_mixed_traffic":
            test_type = "amt"
        else:
            test_type = "tput"
        self.test_type = test_type
        return test_type

    def start_test_run(self, cf, rd):
        try:
            response = cf.start_test(rd.test_id)
            log.info(f"{json.dumps(response, indent=4)}")
            rd.test_started = True
        except Exception as detailed_exception:
            log.error(
                f"Exception occurred when starting the test: "
                f"\n<{detailed_exception}>"
            )
            rd.test_started = False
        return response

    def update_test_run(self, cf, rd):
        rd.test_run_update = cf.get_test_run(rd.id)
        rd.status = rd.test_run_update.get("status")  # main run status 'running'
        rd.sub_status = rd.test_run_update.get("subStatus")
        rd.score = rd.test_run_update.get("score")
        rd.grade = rd.test_run_update.get("grade")
        rd.started_at = rd.test_run_update.get("startedAt")
        rd.finished_at = rd.test_run_update.get("finishedAt")
        rd.progress = rd.test_run_update.get("progress")
        rd.time_elapsed = rd.test_run_update.get("timeElapsed")
        rd.time_remaining = rd.test_run_update.get("timeRemaining")

        update_test_run_log = (
            f"Status: {rd.status} sub status: {rd.sub_status} "
            f" elapsed: {rd.time_elapsed}  remaining: {rd.time_remaining}"
        )
        log.debug(update_test_run_log)
        return True

    def update_phase(self, rd):
        """updates test phase based on elapsed time vs. loadspec configuration

        If goal seeking is enabled and the test is in steady phase, the phase will be set to goalseek

        :return: None
        """
        phase = None
        steady_duration = rd.in_duration - (
            rd.in_startup + rd.in_rampup + rd.in_rampdown + rd.in_shutdown
        )
        if 0 <= rd.time_elapsed <= rd.in_startup:
            phase = "startup"
        elif rd.in_startup <= rd.time_elapsed <= (rd.in_startup + rd.in_rampup):
            phase = "rampup"
        elif (
            (rd.in_startup + rd.in_rampup)
            <= rd.time_elapsed
            <= (rd.in_duration - (rd.in_rampdown + rd.in_shutdown))
        ):
            phase = "steady"
            if rd.first_steady_interval:
                phase = "rampup"
                rd.first_steady_interval = False
        elif (
            (rd.in_startup + rd.in_rampup + steady_duration)
            <= rd.time_elapsed
            <= (rd.in_duration - rd.in_shutdown)
        ):
            phase = "rampdown"
        elif (
            (rd.in_duration - rd.in_shutdown)
            <= rd.time_elapsed
            <= rd.in_duration
        ):
            phase = "shutdown"
        elif rd.in_duration <= rd.time_elapsed:
            phase = "finished"

        log.info(f"test phase: {phase}")
        rd.phase = phase

        # Override phase if ramp seek is enabled
        if rd.in_ramp_seek and rd.phase == "steady" and not rd.ramp_seek_complete:
            rd.phase = "rampseek"
            log.info(f"ramp seek phase: {rd.phase}")
        # Override phase if goal seeking is enabled
        elif rd.in_goal_seek and rd.phase == "steady":
            rd.phase = "goalseek"
            log.info(f"goal seek phase: {rd.phase}")

    def update_run_stats(self, cf, rd):
        get_run_stats = cf.fetch_test_run_statistics(rd.id)
        #log.debug(f'{get_run_stats}')
        #log.debug(json.dumps(get_run_stats, indent=4))
        self.update_client_stats(rd, get_run_stats)
        self.update_server_stats(rd, get_run_stats)

    def update_client_stats(self, rd, get_run_stats):
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
        self.assign_client_run_stats(rd, client_stats)

    def update_server_stats(self, rd, get_run_stats):
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
        self.assign_server_run_stats(rd, server_stats)

    def assign_client_run_stats(self, rd, client_stats):
        rd.c_rx_bandwidth = client_stats.get("driver", {}).get("rxBandwidth", 0)
        rd.c_rx_packet_count = client_stats.get("driver", {}).get("rxPacketCount", 0)
        rd.c_rx_packet_rate = client_stats.get("driver", {}).get("rxPacketRate", 0)
        rd.c_tx_bandwidth = client_stats.get("driver", {}).get("txBandwidth", 0)
        rd.c_tx_packet_count = client_stats.get("driver", {}).get("txPacketCount", 0)
        rd.c_tx_packet_rate = client_stats.get("driver", {}).get("txPacketRate", 0)
        rd.c_rx_byte_rate = client_stats.get("sum", {}).get("rxByteRate", 0)
        rd.c_tx_byte_rate = client_stats.get("sum", {}).get("txByteRate", 0)
        rd.c_http_aborted_txns = client_stats.get("http", {}).get("abortedTxns", 0)
        rd.c_http_aborted_txns_sec = client_stats.get("http", {}).get(
            "abortedTxnsPerSec", 0
        )
        rd.c_http_attempted_txns = client_stats.get("sum", {}).get("attemptedTxns", 0)
        rd.c_http_attempted_txns_sec = client_stats.get("sum", {}).get(
            "attemptedTxnsPerSec", 0
        )
        rd.c_http_successful_txns = client_stats.get("sum", {}).get(
            "successfulTxns", 0
        )
        rd.c_http_successful_txns_sec = client_stats.get("sum", {}).get(
            "successfulTxnsPerSec", 0
        )
        rd.c_http_unsuccessful_txns = client_stats.get("sum", {}).get(
            "unsuccessfulTxns", 0
        )
        rd.c_http_unsuccessful_txns_sec = client_stats.get("sum", {}).get(
            "unsuccessfulTxnsPerSec", 0
        )
        rd.c_loadspec_avg_idle = client_stats.get("loadspec", {}).get(
            "averageIdleTime", 0
        )
        rd.c_loadspec_avg_cpu = round(
            client_stats.get("loadspec", {}).get("cpuUtilized", 0), 1
        )
        rd.c_memory_main_size = client_stats.get("memory", {}).get("mainPoolSize", 0)
        rd.c_memory_main_used = client_stats.get("memory", {}).get("mainPoolUsed", 0)
        rd.c_memory_packetmem_used = client_stats.get("memory", {}).get(
            "packetMemoryUsed", 0
        )
        rd.c_memory_rcv_queue_length = client_stats.get("memory", {}).get(
            "rcvQueueLength", 0
        )
        rd.c_simusers_alive = client_stats.get("simusers", {}).get("simUsersAlive", 0)
        rd.c_simusers_animating = client_stats.get("simusers", {}).get(
            "simUsersAnimating", 0
        )
        rd.c_simusers_blocking = client_stats.get("simusers", {}).get(
            "simUsersBlocking", 0
        )
        rd.c_simusers_sleeping = client_stats.get("simusers", {}).get(
            "simUsersSleeping", 0
        )
        rd.c_simusers_suspending = client_stats.get("simusers", {}).get(
            "simUsersSuspending", 0
        )
        rd.c_current_load = client_stats.get("sum", {}).get("currentLoadSpecCount", 0)
        rd.c_desired_load = client_stats.get("sum", {}).get("desiredLoadSpecCount", 0)
        rd.c_tcp_avg_ttfb = round(
            client_stats.get("tcp", {}).get("averageTimeToFirstByte", 0), 1
        )
        rd.c_tcp_avg_tt_synack = round(
            client_stats.get("tcp", {}).get("averageTimeToSynAck", 0), 1
        )
        rd.c_tcp_cumulative_attempted_conns = client_stats.get("tcp", {}).get(
            "cummulativeAttemptedConns", 0
        )
        rd.c_tcp_cumulative_established_conns = client_stats.get("tcp", {}).get(
            "cummulativeEstablishedConns", 0
        )
        rd.c_url_avg_response_time = round(
            client_stats.get("url", {}).get("averageRespTimePerUrl", 0), 1
        )
        if self.divide_by_1000:
            rd.c_url_avg_response_time = round(rd.c_url_avg_response_time / 1000, 3)
        rd.c_tcp_attempted_conn_rate = client_stats.get("sum", {}).get(
            "attemptedConnRate", 0
        )
        rd.c_tcp_established_conn_rate = client_stats.get("sum", {}).get(
            "establishedConnRate", 0
        )
        rd.c_tcp_attempted_conns = client_stats.get("sum", {}).get(
            "attemptedConns", 0
        )
        rd.c_tcp_established_conns = client_stats.get("sum", {}).get(
            "currentEstablishedConns", 0
        )

        rd.time_elapsed = client_stats.get("timeElapsed", 0)
        rd.time_remaining = client_stats.get("timeRemaining", 0)

        rd.c_total_bandwidth = rd.c_rx_bandwidth + rd.c_tx_bandwidth
        rd.c_total_byte_rate = rd.c_rx_byte_rate + rd.c_tx_byte_rate
        rd.c_total_packet_count = rd.c_rx_packet_count + rd.c_tx_packet_count
        if rd.c_memory_main_size > 0 and rd.c_memory_main_used > 0:
            rd.c_memory_percent_used = round(100 *
                rd.c_memory_main_used / rd.c_memory_main_size, 2
            )
        if rd.c_current_load > 0 and rd.c_desired_load > 0:
            rd.c_current_desired_load_variance = round(
                rd.c_current_load / rd.c_desired_load, 2
            )

        if rd.c_http_successful_txns > 0:
            rd.c_transaction_error_percentage = (
                rd.c_http_unsuccessful_txns + rd.c_http_aborted_txns
            ) / rd.c_http_successful_txns
        if rd.phase in ["rampup", "goalseek"]:
            self.ocj.set_startup_data()
        return True

    def assign_server_run_stats(self, rd, server_stats):
        rd.s_rx_bandwidth = server_stats.get("driver", {}).get("rxBandwidth", 0)
        rd.s_rx_packet_count = server_stats.get("driver", {}).get("rxPacketCount", 0)
        rd.s_rx_packet_rate = server_stats.get("driver", {}).get("rxPacketRate", 0)
        rd.s_tx_bandwidth = server_stats.get("driver", {}).get("txBandwidth", 0)
        rd.s_tx_packet_count = server_stats.get("driver", {}).get("txPacketCount", 0)
        rd.s_tx_packet_rate = server_stats.get("driver", {}).get("txPacketRate", 0)
        rd.s_memory_main_size = server_stats.get("memory", {}).get("mainPoolSize", 0)
        rd.s_memory_main_used = server_stats.get("memory", {}).get("mainPoolUsed", 0)
        rd.s_memory_packetmem_used = server_stats.get("memory", {}).get(
            "packetMemoryUsed", 0
        )
        rd.s_memory_rcv_queue_length = server_stats.get("memory", {}).get(
            "rcvQueueLength", 0
        )
        rd.s_memory_avg_cpu = round(
            server_stats.get("memory", {}).get("cpuUtilized", 0), 1
        )
        rd.s_tcp_closed_error = server_stats.get("sum", {}).get("closedWithError", 0)
        rd.s_tcp_closed = server_stats.get("sum", {}).get("closedWithNoError", 0)
        rd.s_tcp_closed_reset = server_stats.get("sum", {}).get("closedWithReset", 0)

        if rd.s_memory_main_size > 0 and rd.s_memory_main_used > 0:
            rd.s_memory_percent_used = round(100 *
                rd.s_memory_main_used / rd.s_memory_main_size, 2
            )
        return True

    def print_test_status(self, rd):
        status = (
            f"{rd.timer}s -status: {rd.status} -sub status: {rd.sub_status} "
            f"-progress: {rd.progress} -seconds elapsed: {rd.time_elapsed} "
            f"-remaining: {rd.time_remaining}"
        )
        print(status)

    def print_test_stats(self, rd):
        stats = (
            f"{rd.time_elapsed}s {rd.phase} -load: {rd.c_current_load:,}/{rd.c_desired_load:,} "
            f"-current/desired var: {rd.c_current_desired_load_variance} "
            f"-current avg/max var: {rd.rolling_tps.avg_max_load_variance} "
            f"-seek ready: {rd.rolling_count_since_goal_seek.stable}"
            f"\n-tps: {rd.c_http_successful_txns_sec:,} -tps stable: {rd.rolling_tps.stable} "
            f"-tps cur avg: {rd.rolling_tps.avg_val:,} -tps prev: {rd.rolling_tps.avg_val_last:,} "
            f"-delta tps: {rd.rolling_tps.increase_avg} -tps list:{rd.rolling_tps.list} "
            f"\n-cps: {rd.c_tcp_established_conn_rate:,} -cps stable: {rd.rolling_cps.stable} "
            f"-cps cur avg: {rd.rolling_cps.avg_val:,} -cps prev: {rd.rolling_cps.avg_val_last:,} "
            f"-delta cps: {rd.rolling_cps.increase_avg} -cps list:{rd.rolling_cps.list} "
            f"\n-conns: {rd.c_tcp_established_conns:,} -conns stable: {rd.rolling_conns.stable} "
            f"-conns cur avg: {rd.rolling_conns.avg_val:,} -conns prev: {rd.rolling_conns.avg_val_last:,} "
            f"-delta conns: {rd.rolling_cps.increase_avg} -conns list:{rd.rolling_conns.list} "
            f"\n-bw: {rd.c_total_bandwidth:,} -bw stable: {rd.rolling_bw.stable} "
            f"-bw cur avg: {rd.rolling_bw.avg_val:,} -bw prev: {rd.rolling_bw.avg_val_last:,} "
            f"-delta bw: {rd.rolling_bw.increase_avg} -bw list:{rd.rolling_bw.list} "
            f"\n-ttfb: {rd.c_tcp_avg_ttfb:,} -ttfb stable: {rd.rolling_ttfb.stable} "
            f"-ttfb cur avg: {rd.rolling_ttfb.avg_val:,} -ttfb prev: {rd.rolling_ttfb.avg_val_last:,} "
            f"-delta ttfb: {rd.rolling_ttfb.increase_avg} -ttfb list:{rd.rolling_ttfb.list} "
            f"\n-cpu_c: {rd.c_loadspec_avg_cpu:6.1f}  -pktmemused_c: {rd.c_memory_packetmem_used:4.0f} "
            f" -memused_c: {rd.c_memory_main_used:5.0f}  -memusedpert_c: {rd.c_memory_percent_used:3.1f}"
            f" -mem_c: {rd.c_memory_main_size:5.0f}"
            f"\n-cpu_s: {rd.s_memory_avg_cpu:6.1f}  -pktmemUsed_s: {rd.s_memory_packetmem_used:4.0f} "
            f" -memused_s: {rd.s_memory_main_used:5.0f}  -memusedperc_s: {rd.s_memory_percent_used:3.1f}"
            f" -mem_s: {rd.s_memory_main_size:5.0f}"
            f"\n-attempt txn: {rd.c_http_attempted_txns:9.0f}  -success txns: {rd.c_http_successful_txns:9.0f} "
            f" -failed txns: {rd.c_http_unsuccessful_txns} (unsucc) + {rd.c_http_aborted_txns} (abort)"

            # f"\n-total bw: {rd.c_total_bandwidth:,} -rx bw: {rd.c_rx_bandwidth:,}"
            # f" tx bw: {rd.c_tx_bandwidth:,}"
            # f"\n-ttfb cur avg: {rd.rolling_ttfb.avg_val} -ttfb prev: {rd.rolling_ttfb.avg_val_last} "
            # f"-delta ttfb: {rd.rolling_ttfb.increase_avg} -ttfb list:{rd.rolling_ttfb.list}"
        )
        print(stats)
        log.debug(stats)

    def wait_for_running_status(self, cf, rd):
        """
        Wait for the current test to return a 'running' status.
        :return: True if no statements failed and there were no exceptions. False otherwise.
        """
        log.debug("Inside the RunTest/wait_for_running_status method.")
        i = 0
        while True:
            time.sleep(4)
            rd.timer = int(round(time.time() - rd.start_time))
            i += 4
            if not self.update_test_run(cf, rd):
                return False
            if rd.status == "running":
                print(f"{rd.timer}s - status: {rd.status}")
                break

            print(
                f"{rd.timer}s - status: {rd.status}  sub status: {rd.sub_status}"
            )
            if rd.status in {"failed", "finished"}:
                log.error("Test failed")
                return False
            # check to see if another test with the same ID is running
            # (can happen due to requests retry)
            if i > 120 and rd.status == "waiting":
                self.check_running_tests(cf, rd)
            # stop after 1800 seconds of waiting
            if i > 1800:
                log.error(
                    "Waited for 1800 seconds, test did not transition to a running status."
                )
                return False
        rd.time_to_run = rd.timer
        log.debug(f"Test {rd.name} successfully went to running status.")
        log.debug(json.dumps(rd.test_run_update, indent=4))
        rd.run_id = rd.test_run_update.get("runId")
        rd.report_link = (
            "https://"
            + cf.controller_ip
            + "/#results/"
            + rd.type_v1
            + "/"
            + rd.run_id
        )
        return True

    def check_running_tests(self, cf, rd):
        """Checks if tests with same ID is running and changes control to this test
        This function can be triggered if waiting status is too long because the requests module retry mechanism has
        kicked off two duplicate tests in error. It will look for matching running tests and switch control over to the
        already running duplicate test.
        :return: None
        """
        # get list of run IDs and test IDs with status
        test_runs = cf.list_test_runs()
        # look for running status and compare ID
        for run in test_runs:
            if run["status"] == "running":
                log.debug(
                    f"check_running_tests found running test: {json.dumps(run, indent=4)}"
                )
                # if waiting and running test IDs match, change the running test
                if rd.test_id == run["testId"]:
                    log.debug(
                        f"check_running_tests found matching test_id {rd.test_id}"
                    )
                    # stop current waiting test
                    response = cf.stop_test(rd.id)
                    log.debug(
                        f"change_running_test, stopped duplicate waiting test: {response}"
                    )
                    # change over to running test
                    rd.id = run["id"]
                else:
                    log.debug(
                        f"check_running_tests test_id: {rd.test_id} "
                        f"does not match running test_id: {run['testId']}"
                    )

    def wait_for_running_sub_status(self, cf, rd):
        """
        Wait for the current test to return a 'None' sub status.
        :return: True if no statements failed and there were no exceptions. False otherwise.
        """
        log.debug("Inside the RunTest/wait_for_running_sub_status method.")
        i = 0
        while True:
            time.sleep(4)
            rd.timer = int(round(time.time() - rd.start_time))
            i += 4
            if not self.update_test_run(cf, rd):
                return False
            print(
                f"{rd.timer}s - status: {rd.status}  sub status: {rd.sub_status}"
            )
            if rd.sub_status is None:
                break

            if rd.status in {"failed", "finished"}:
                log.error("Test failed")
                return False
            # stop after 0 seconds of waiting
            if i > 360:
                log.error(
                    "Waited for 360 seconds, test did not transition to traffic state."
                )
                return False
        rd.time_to_start = rd.timer - rd.time_to_run
        log.debug(f"Test {rd.name} successfully went to traffic state.")
        log.debug(json.dumps(rd.test_run_update, indent=4))
        return True

    def stop_wait_for_finished_status(self, cf, rd):
        """
        Stop and wait for the current test to return a 'finished' status.
        :return: True if no statements failed and there were no exceptions.
         False otherwise.
        """
        log.debug("Inside the stop_test/wait_for_finished_status method.")
        rd.time_to_stop_start = rd.timer
        if rd.status == "running":
            self.cf.stop_test(rd.id)

        i = 0
        while True:
            if rd.c_desired_load > 0:
                self.update_run_stats(cf, rd)
                self.save_results(rd)
            time.sleep(4)
            rd.timer = int(round(time.time() - rd.start_time))
            i += 4
            if not self.update_test_run(cf, rd):
                return False
            if rd.status in {"stopped", "finished", "failed"}:
                print(f"{rd.timer} status: {rd.status}")
                break
            if rd.status == "failed":
                print(f"{rd.timer} status: {rd.status}")
                return False

            print(
                f"{rd.timer}s - status: {rd.status}  sub status: {rd.sub_status}"
            )
            if i > 1800:
                error_msg = (
                    "Waited for 1800 seconds, "
                    "test did not transition to a finished status."
                )
                log.error(error_msg)
                print(error_msg)
                return False
        rd.time_to_stop = rd.timer - rd.time_to_stop_start
        log.debug(
            f"Test {rd.name} successfully went to finished status in "
            f"{rd.time_to_stop} seconds."
        )
        return True

    def wait_for_test_activity(self, cf, rd):
        """
        Wait for the current test to show activity - metric(s) different than 0.
        :return: True if no statements failed and there were no exceptions.
        False otherwise.
        """
        log.debug("Inside the RunTest/wait_for_test_activity method.")
        test_generates_activity = False
        i = 0
        while not test_generates_activity:
            rd.timer = int(round(time.time() - rd.start_time))
            self.update_test_run(cf, rd)
            self.update_run_stats(cf, rd)
            # self.print_test_status(rd)

            if rd.sub_status is None:
                self.print_test_stats(rd)
                self.save_results(rd)

            if rd.c_http_successful_txns_sec > 0:
                test_generates_activity = True
            if rd.status in {"failed", "finished"}:
                log.error("Test failed")
                return False
            if i > 180:
                error_msg = (
                    "Waited for 180 seconds, test did not have successful transactions"
                )
                log.error(error_msg)
                print(error_msg)
                return False
            time.sleep(4)
            i = i + 4
            print(f"")
        rd.time_to_activity = rd.timer - rd.time_to_start - rd.time_to_run
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

    def goal_seek(self, rd):
        log.info(f"In goal_seek function")
        if rd.c_current_load == 0:
            rd.stop = True
            log.info(f"goal_seek stop, c_current_load == 0")
            return False
        if rd.goal_seek_count >= rd.minimum_goal_seek_count:
            rd.first_goal_load_increase = False
        else:
            rd.first_goal_load_increase = True
        if rd.first_goal_load_increase:
            new_load = rd.c_current_load + (rd.in_incr_low *
                                              rd.in_capacity_adjust)
        else:
            if self.ocj.is_load_type_conns():
                new_load = self.ocj.get_new_load()
            elif self.check_if_load_type_simusers(rd):
                new_load = self.goal_seek_set_simuser_kpi(rd, rd.kpi_1)
                log.info(f"new_load = {new_load}")
            elif self.check_if_load_type_default(rd):
                new_load = self.goal_seek_set_default(rd)
                log.info(f"new_load = {new_load}")
            else:
                report_error = f"Unknown load type: " \
                    f"{rd.test_config['config']['loadSpecification']['type']}"
                log.error(report_error)
                print(report_error)
                return False

        if new_load is False:
            log.info(
                f"Config load spec type: {rd.test_config['config']['loadSpecification']['type']}"
            )
            log.info(f"Goal_seek return, new_load is False")
            return False

        if self.test_type == "conns":
            self.change_update_load(rd, new_load, 4)
        else:
            self.change_update_load(rd, new_load, 16)

        return True

    def ramp_seek(self, rd, ramp_kpi, ramp_to_value):
        log.info(f"In ramp_seek function")
        if rd.c_current_load == 0:
            rd.stop = True
            log.info(f"ramp_seek stop, c_current_load == 0")
            return False
        # if rd.first_ramp_load_increase:
        #     rd.first_ramp_load_increase = False
        #     new_load = rd.c_current_load * 2

        if rd.in_ramp_step < 1:
            rd.ramp_seek_complete = True
            return
        if ramp_kpi.current_value < ramp_to_value:
            load_increase_multiple = round(ramp_to_value / ramp_kpi.current_value, 3)
            load_increase = (rd.c_current_load * load_increase_multiple) - rd.c_current_load
            load_increase = round(load_increase / rd.in_ramp_step, 3)
            new_load = self.round_up_to_even(rd.c_current_load + load_increase)
            rd.in_ramp_step = rd.in_ramp_step - 1

            log.info(f"new load: {new_load}, current_load: {rd.c_current_load}"
                     f" * {load_increase} load_increase "
                     f"ramp_step left: {rd.in_ramp_step} "
                     f"\n ramp_to_value: {ramp_to_value} "
                     f"ramp_kpi.current_value: {ramp_kpi.current_value}"
                     )
            rd.in_incr_low = self.round_up_to_even(new_load * rd.in_ramp_low/100)
            rd.in_incr_med = self.round_up_to_even(new_load * rd.in_ramp_med/100)
            rd.in_incr_high = self.round_up_to_even(new_load * rd.in_ramp_high/100)
        else:
            rd.ramp_seek_complete = True
        self.change_update_load(rd, new_load, 8)
        return True

    @staticmethod
    def round_up_to_even(v):
        return math.ceil(v / 2.) * 2

    def check_if_load_type_simusers(self, rd):
        if rd.test_config["config"]["loadSpecification"]["type"].lower() in {
            "simusers",
            "simusers/second",
        }:
            return True
        return False

    def check_if_load_type_default(self, rd):
        if rd.test_config["config"]["loadSpecification"]["type"].lower() in {
            "bandwidth",
            "connections",
            "connections/second",
        }:
            return True
        return False

    def change_update_load(self, rd, new_load, count_down):
        new_load = self.round_up_to_even(new_load)
        log_msg = f"\nchanging load from: {rd.c_current_load} to: {new_load}  status: {rd.status}"
        log.info(log_msg)
        print(log_msg)
        try:
            self.cf.change_load(rd.id, new_load)
            rd.rolling_tps.load_increase_complete()
            rd.rolling_ttfb.load_increase_complete()
            rd.rolling_current_load.load_increase_complete()
            rd.rolling_cps.load_increase_complete()
            rd.rolling_conns.load_increase_complete()
            rd.rolling_bw.load_increase_complete()
        except Exception as detailed_exception:
            log.error(
                f"Exception occurred when changing test: " f"\n<{detailed_exception}>"
            )
        rd.goal_seek_count = rd.goal_seek_count + 1    
        self.countdown(count_down)
        return True

    def goal_seek_set_default(self, rd):
        set_load = 0
        if rd.c_current_desired_load_variance >= 0.97:
            if rd.c_current_load <= rd.in_threshold_low:
                set_load = rd.c_current_load + (
                    rd.in_incr_low * rd.in_capacity_adjust
                )
            elif rd.c_current_load <= rd.in_threshold_med:
                set_load = rd.c_current_load + (
                    rd.in_incr_med * rd.in_capacity_adjust
                )
            elif rd.c_current_load <= rd.in_threshold_high:
                set_load = rd.c_current_load + (
                    rd.in_incr_high * rd.in_capacity_adjust
                )
            elif rd.c_current_load > rd.in_threshold_high:
                return False
        else:
            return False
        if rd.in_threshold_high < set_load:
            if rd.c_current_desired_load_variance > 0.99:
                return False
            else:
                set_load = rd.in_threshold_high
        return set_load

    def goal_seek_set_simuser_kpi(self, rd, kpi):
        log.debug(f"in goal_seek_set_simuser_kpi function")
        set_load = 0
        if kpi.increase_avg >= rd.in_threshold_low:
            set_load = rd.c_current_load + (rd.in_incr_low *
                                              rd.in_capacity_adjust)
        elif kpi.increase_avg >= rd.in_threshold_med:
            set_load = rd.c_current_load + (rd.in_incr_med *
                                              rd.in_capacity_adjust)
        elif kpi.increase_avg >= rd.in_threshold_high:
            set_load = rd.c_current_load + (rd.in_incr_high *
                                              rd.in_capacity_adjust)
        elif kpi.increase_avg < rd.in_threshold_high:
            log.info(
                f"rolling_tps.increase_avg {kpi.increase_avg} < "
                f"{rd.in_threshold_high} in_threshold_high"
            )
            return False
        if kpi.avg_max_load_variance < 0.97:
            set_load = rd.c_current_load
            rd.max_load_reached = True
        log.info(
            f"set_load = {set_load}  "
            f"kpi_avg_max_load_variance: {kpi.avg_max_load_variance}"
        )
        return set_load

    def update_rolling_averages(self, rd):
        """Updates rolling statistics averages used to make test control decisions

        :return: None
        """
        rd.rolling_tps.update(rd.c_http_successful_txns_sec)
        rd.rolling_tps.check_if_stable(rd.max_var_reference)

        rd.rolling_ttfb.update(rd.c_tcp_avg_ttfb)
        rd.rolling_ttfb.check_if_stable(rd.max_var_reference)

        rd.rolling_current_load.update(rd.c_current_load)
        rd.rolling_current_load.check_if_stable(rd.max_var_reference)

        rd.rolling_cps.update(rd.c_tcp_established_conn_rate)
        rd.rolling_cps.check_if_stable(rd.max_var_reference)

        rd.rolling_conns.update(rd.c_tcp_established_conns)
        rd.rolling_conns.check_if_stable(rd.max_var_reference)

        rd.rolling_bw.update(rd.c_total_bandwidth)
        rd.rolling_bw.check_if_stable(rd.max_var_reference)

        rd.rolling_count_since_goal_seek.update(1)
        rd.rolling_count_since_goal_seek.check_if_stable(0)

    def check_kpi(self, rd):
        rd.in_kpi_1 = rd.in_kpi_1.lower()
        if rd.in_kpi_1 == "tps":
            rd.kpi_1 = rd.rolling_tps
        elif rd.in_kpi_1 == "cps":
            rd.kpi_1 = rd.rolling_cps
        elif rd.in_kpi_1 == "conns":
            rd.kpi_1 = rd.rolling_conns
        elif rd.in_kpi_1 == "bw":
            rd.kpi_1 = rd.rolling_bw
        elif rd.in_kpi_1 == "ttfb":
            rd.kpi_1 = rd.rolling_ttfb
        else:
            log.debug(f"check_kpi unknown kpi_1, setting to TPS")
            rd.kpi_1 = rd.rolling_tps

        rd.in_kpi_2 = rd.in_kpi_2.lower()
        if rd.in_kpi_2 == "tps":
            rd.kpi_2 = rd.rolling_tps
        elif rd.in_kpi_2 == "cps":
            rd.kpi_2 = rd.rolling_cps
        elif rd.in_kpi_2 == "conns":
            rd.kpi_2 = rd.rolling_conns
        elif rd.in_kpi_2 == "bw":
            rd.kpi_2 = rd.rolling_bw
        elif rd.in_kpi_2 == "ttfb":
            rd.kpi_2 = rd.rolling_ttfb
        else:
            log.debug(f"check_kpi unknown kpi_2, setting to CPS")
            rd.kpi_2 = rd.rolling_cps

    def check_ramp_seek_kpi(self, rd):
        if rd.in_ramp_seek_kpi == "tps":
            rd.ramp_seek_kpi = rd.rolling_tps
        elif rd.in_ramp_seek_kpi == "cps":
            rd.ramp_seek_kpi = rd.rolling_cps
        elif rd.in_ramp_seek_kpi == "conns":
            rd.ramp_seek_kpi = rd.rolling_conns
        elif rd.in_ramp_seek_kpi == "bw":
            rd.ramp_seek_kpi = rd.rolling_bw
        elif rd.in_ramp_seek_kpi == "ttfb":
            rd.ramp_seek_kpi = rd.rolling_ttfb
        else:
            log.debug(f"check_ramp_seek_kpi unknown kpi, setting to TPS")
            rd.ramp_seek_kpi = rd.rolling_tps

    @staticmethod
    def return_bool_true(check_if, is_value):
        if isinstance(check_if, bool):
            return check_if
        if isinstance(check_if, str) and check_if.lower() == is_value:
            return True
        return False

    def control_test(self, cf, rd):
        """Main test control

        Runs test. Start by checking if test is in running state followed by checking
        for successful connections.
        First updates stats, checks the phase test is in based on elapsed time, then updates
        rolloing averages.

        :return: True if test completed successfully
        """
        # exit control_test if test does not go into running state
        if not self.wait_for_running_status(cf, rd):
            log.info(f"control_test end, wait_for_running_status False")
            return False
        # exit control_test if test does not go into running state
        if not self.wait_for_running_sub_status(cf, rd):
            log.info(f"control_test end, wait_for_running_sub_status False")
            return False
        # exit control_test if test does not have successful transactions
        if not self.wait_for_test_activity(cf, rd):
            self.stop_wait_for_finished_status(cf, rd)
            log.info(f"control_test end, wait_for_test_activity False")
            return False
        self.check_ramp_seek_kpi(rd)
        self.check_kpi(rd)
        rd.rolling_count_since_goal_seek.reset()
        # self.countdown(12)
        # test control loop - runs until self.stop is set to True
        while not rd.stop:
            self.update_run_stats(cf, rd)
            self.update_phase(rd)
            self.check_stop_conditions(rd)
            self.update_rolling_averages(rd)

            # print stats if test is running
            if rd.sub_status is None:
                self.print_test_stats(rd)
                self.save_results(rd)

            if rd.in_ramp_seek and not rd.ramp_seek_complete:
                log.info(f"control_test going to ramp_seek")
                self.control_test_ramp_seek(rd, rd.ramp_seek_kpi, rd.in_ramp_seek_value)

            if rd.in_goal_seek and rd.ramp_seek_complete:
                log.info(f"control_test going to goal_seek")
                self.control_test_goal_seek_kpi(rd, rd.kpi_1, rd.kpi_2,
                                                rd.in_kpi_and_or)
            print(f"")
            time.sleep(4)
        # if goal_seek is yes enter sustained steady phase
        if rd.in_goal_seek and rd.in_sustain_period > 0:
            self.sustain_test(cf, rd)
        # stop test and wait for finished status
        if self.stop_wait_for_finished_status(cf, rd):
            rd.time_to_stop = rd.timer - rd.time_to_stop_start
            #self.save_results(rd)
            return True
        return False

    def check_stop_conditions(self, rd):
        log.debug(f"in check_stop_conditions method")
        # stop test if time_remaining returned from controller == 0
        if rd.time_remaining == 0:
            rd.phase = "timeout"
            log.info(f"control_test end, time_remaining == 0")
            rd.stop = True
        # stop goal seeking test if time remaining is less than 30s
        if rd.time_remaining < 30 and rd.in_goal_seek:
            rd.phase = "timeout"
            log.info(f"control_test end goal_seek, time_remaining < 30")
            rd.stop = True
        elif rd.time_remaining < 30 and rd.in_ramp_seek:
            rd.phase = "timeout"
            log.info(f"control_test end ramp_seek, time_remaining < 30")
            rd.stop = True
        if rd.phase == "finished":
            log.info(f"control_test end, over duration time > phase: finished")
            rd.stop = True

    def control_test_ramp_seek(self, rd, ramp_kpi, ramp_to_value):
        """
        Increases load to a configured tps, cps, conns or bandwidth level.
        :return: True if no statements failed and there were no exceptions.
        False otherwise.
        """
        ramp_seek_count = 1
        #log.debug("Inside the RunTest/ramp_to_seek method.")
        log.info(
            f"Inside the RunTest/ramp_to_seek method.\n"
            f"rolling_count_list stable: {rd.rolling_count_since_goal_seek.stable} "
            f"list: {rd.rolling_count_since_goal_seek.list} "
            f"\nramp_to_value: {ramp_to_value} ramp_kpi current: {ramp_kpi.current_value}"
            f" increase: {ramp_kpi.increase_avg}"
            f"\n current load: {rd.c_current_load}"
            f" desired_load: {rd.c_desired_load}"
        )
        if rd.phase != "rampseek":
            log.info(f"phase {rd.phase} is not 'rampseek', "
                     f"returning from contol_test_ramp_seek")
            return
        if not rd.rolling_count_since_goal_seek.stable:
            log.info(f"count since goal seek is not stable. "
                     f"count list: {rd.rolling_count_since_goal_seek.list}"
                     f"returning from control_test_ramp_seek")
            return
        if rd.max_load_reached:
            log.info(f"control_test_ramp_seek end, max_load_reached")
            rd.stop = True
            return
        # check if kpi avg is under set avg - if not, stop loop
        if ramp_to_value < ramp_kpi.current_value:
            log.info(f"ramp_to_value {ramp_to_value} < ramp_kpi.current_value {ramp_kpi.current_value}"
                     f"completed ramp_seek")
            rd.ramp_seek_complete = True
            rd.in_capacity_adjust = 1
            return

        if self.ramp_seek(rd, ramp_kpi, ramp_to_value):
            # reset rolling count > no load increase until
            # at least the window size interval.
            # allows stats to stabilize after an increase
            rd.rolling_count_since_goal_seek.reset()
        else:
            log.info(f"control_test_ramp_seek end, ramp_seek False")
            rd.ramp_seek_complete = True
            rd.in_capacity_adjust = 1
            return

        if (ramp_kpi.current_value / ramp_to_value) > 0.95:
            log.info(
                f"ramp_kpi.current_value {ramp_kpi.current_value} / "
                f"ramp_to_value {ramp_to_value} > 0.95 "
                f"increasing ramp_seek_count + 1")
            ramp_seek_count = ramp_seek_count + 1
            if ramp_seek_count == rd.in_ramp_step:
                log.info(f"ramp_seek_complete early")
                rd.ramp_seek_complete = True
                rd.in_capacity_adjust = 1
                return
        return

    def control_test_goal_seek_kpi(self, rd, kpi_1,
                                   kpi_2, kpis_and_bool):
        log.info(
            f"rolling_count_list stable: {rd.rolling_count_since_goal_seek.stable} "
            f"list: {rd.rolling_count_since_goal_seek.list} "
            f"\nKpi1 stable: {kpi_1.stable} list: {kpi_1.list}"
            f"\nKpi2 stable: {kpi_2.stable} list: {kpi_2.list}"
        )
        self.ocj.capture_goal_seek_iteration()
        if rd.phase != "goalseek":
            log.info(f"phase {rd.phase} is not 'goalseek', "
                     f"returning from contol_test_goal_seek")
            return
        if self.test_type == "conns":
            if rd.in_load_type == "Connections" :
                log.info(f"tps: {rd.c_http_successful_txns_sec} -cps: {rd.c_tcp_established_conn_rate}")
                if rd.c_http_successful_txns_sec == 0 or rd.c_tcp_established_conn_rate == 0:
                    log.info(f"Ready for Open Conns goal seeking")
                    pass
                else:
                    log.info(f"Not ready for Open Conns goal seeking, continue to add load")
                    return
            elif rd.in_load_type == "SimUsers":
                message = "Heap Memory state changed from OK to Throttled Free"
                log.info(f"rd.c_memory_percent_used is: {rd.c_memory_percent_used}")
                log.info(f"rd.c_simusers_suspending is: {rd.c_simusers_suspending}")
                if rd.c_memory_percent_used > 97:
                    eventlogs = self.cf.fetch_event_logs(rd.id)
                    for line in eventlogs["logs"]:
                        if message in line:
                            log.debug(f"eventLog: \n{json.dumps(eventlogs, indent=4)}")
                            message = line + f"\nSuspending Simusers: {rd.c_simusers_suspending}, stop goal seek"
                            print(message)
                            rd.max_load_reached = True
                            rd.stop = True
                            return
                if rd.c_simusers_suspending > 0:
                    message = f"Suspending Simusers: {rd.c_simusers_suspending}, stop goal seek"
                    log.debug(message)
                    print(message)
                    rd.max_load_reached = True
                    rd.stop = True
                    return
                if rd.c_tcp_established_conn_rate == 0:
                    log.info(f"cps: {rd.c_tcp_established_conn_rate}, ready for goal seek")
                    pass
                else:
                    log.info(f"cps: {rd.c_tcp_established_conn_rate}, not ready for goal seek, continue to add load")
                    return
        elif not rd.rolling_count_since_goal_seek.stable:
            log.info(f"count since goal seek is not stable. "
                     f"count list: {rd.rolling_count_since_goal_seek.list}")
            return
        if rd.max_load_reached:
            log.info(f"control_test end, max_load_reached")
            rd.stop = True
            return

        if rd.goal_seek_count < 3:
            if not kpi_1.stable or not kpi_2.stable:
                rd.minimum_goal_seek_count = 3

        if self.test_type == "conns":
            goal_seek = True
        elif rd.goal_seek_count < rd.minimum_goal_seek_count:
            goal_seek = True
        elif kpis_and_bool:
            if kpi_1.stable and kpi_2.stable:
                goal_seek = True
            else:
                goal_seek = False
        else:
            if kpi_1.stable or kpi_2.stable:
                goal_seek = True
            else:
                goal_seek = False

        if goal_seek:
            if self.goal_seek(rd):
                # reset rolling count > no load increase until
                # at least the window size interval.
                # allows stats to stabilize after an increase
                rd.rolling_count_since_goal_seek.reset()
            else:
                log.info(f"control_test end, goal_seek False")
                rd.stop = True

    def sustain_test(self, cf, rd):
        rd.phase = "steady"
        while rd.in_sustain_period > 0:
            rd.timer = int(round(time.time() - rd.start_time))
            sustain_period_loop_time_start = time.time()
            self.update_run_stats(cf, rd)
            if rd.time_remaining < 30 and rd.in_goal_seek:
                rd.phase = "timeout"
                rd.in_sustain_period = 0
                log.info(f"sustain_test end, time_remaining < 30")
            print(f"sustain period time left: {int(rd.in_sustain_period)}")

            # print stats if test is running
            if rd.sub_status is None:
                self.print_test_stats(rd)
                self.save_results(rd)

            time.sleep(4)
            rd.in_sustain_period = rd.in_sustain_period - (
                time.time() - sustain_period_loop_time_start
            )
        rd.phase = "stopping"
        # self.stop_wait_for_finished_status(cf, rd)
        return True

    def save_results(self, rd):

        csv_list = [
            rd.in_name,
            rd.time_elapsed,
            rd.phase,
            rd.c_current_load,
            rd.c_desired_load,
            rd.rolling_count_since_goal_seek.stable,
            rd.c_http_successful_txns_sec,
            rd.rolling_tps.stable,
            rd.rolling_tps.increase_avg,
            rd.c_http_successful_txns,
            rd.c_http_unsuccessful_txns,
            rd.c_http_aborted_txns,
            rd.c_transaction_error_percentage,
            rd.c_tcp_established_conn_rate,
            rd.rolling_cps.stable,
            rd.rolling_cps.increase_avg,
            rd.c_tcp_established_conns,
            rd.rolling_conns.stable,
            rd.rolling_conns.increase_avg,
            rd.c_tcp_avg_tt_synack,
            rd.c_tcp_avg_ttfb,
            rd.rolling_ttfb.stable,
            rd.rolling_ttfb.increase_avg,
            rd.c_url_avg_response_time,
            rd.c_tcp_cumulative_established_conns,
            rd.c_tcp_cumulative_attempted_conns,
            rd.c_total_bandwidth,
            rd.rolling_bw.stable,
            rd.rolling_bw.increase_avg,
            rd.c_rx_bandwidth,
            rd.c_tx_bandwidth,
            rd.c_total_byte_rate,
            rd.c_rx_byte_rate,
            rd.c_tx_byte_rate,
            rd.c_total_packet_count,
            rd.c_rx_packet_count,
            rd.c_tx_packet_count,
            rd.c_rx_packet_rate,
            rd.c_tx_packet_rate,
            rd.s_tcp_closed,
            rd.s_tcp_closed_reset,
            rd.s_tcp_closed_error,
            rd.c_simusers_alive,
            rd.c_simusers_animating,
            rd.c_simusers_blocking,
            rd.c_simusers_sleeping,
            rd.c_loadspec_avg_cpu,
            rd.c_memory_percent_used,
            rd.c_memory_packetmem_used,
            rd.c_memory_rcv_queue_length,
            rd.s_memory_avg_cpu,
            rd.s_memory_percent_used,
            rd.s_memory_packetmem_used,
            rd.s_memory_rcv_queue_length,
            rd.type_v1,
            rd.type_v2,
            rd.in_load_type,
            rd.test_id,
            rd.id,
            rd.time_to_run,
            rd.time_to_start,
            rd.time_to_activity,
            rd.time_to_stop,
            script_version,
            rd.report_link,
        ]
        self.result_file.append_file(csv_list)

class DetailedCsvReport:
    def __init__(self, report_location):
        log.debug("Initializing detailed csv result files.")
        self.time_stamp = time.strftime("%Y%m%d-%H%M")
        log.debug(f"Current time stamp: {self.time_stamp}")
        self.report_location_parent = report_location
        #self.report_csv_file = report_location / f"{self.time_stamp}_Detailed.csv"
        self.columns = [
            "test_name",
            "seconds",
            "state",
            "current_load",
            "desired_load",
            "seek_ready",
            "tps",
            "tps_stable",
            "tps_delta",
            "successful_txn",
            "unsuccessful_txn",
            "aborted_txn",
            "txn_error_rate",
            "cps",
            "cps_stable",
            "cps_delta",
            "open_conns",
            "conns_stable",
            "conns_delta",
            "tcp_avg_tt_synack",
            "tcp_avg_ttfb",
            "ttfb_stable",
            "ttfb_delta",
            "url_response_time",
            "total_tcp_established",
            "total_tcp_attempted",
            "total_bandwidth",
            "bw_stable",
            "bw_delta",
            "rx_bandwidth",
            "tx_bandwidth",
            "total_byte_rate",
            "rx_byte_rate",
            "tx_byte_rate",
            "total_packet_count",
            "rx_packet_count",
            "tx_packet_count",
            "rx_packet_rate",
            "tx_packet_rate",
            "tcp_closed",
            "tcp_reset",
            "tcp_error",
            "simusers_alive",
            "simusers_animating",
            "simusers_blocking",
            "simusers_sleeping",
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
            "version",
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
    def make_report_csv_file(self, new_report_csv_name):
        new_report_csv_name = self.report_location / f"{new_report_csv_name}_{self.time_stamp}_Detailed.csv"
        print(new_report_csv_name)
        if new_report_csv_name.is_file():
            return
        else:
            self.report_csv_file = new_report_csv_name
            self.append_columns()

    def make_report_dir(self, report_dir_name):
        report_dir = self.report_location_parent / report_dir_name
        if report_dir.is_dir():
            pass
        else:
            report_dir.mkdir(parents=False, exist_ok=True)
        self.report_location = report_dir


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
            total_pkt_count_sum = self.df_base.loc[self.df_base["test_name"] == name, "total_packet_count"].sum()
            total_byte_rate_sum = self.df_base.loc[self.df_base["test_name"] == name, "total_byte_rate"].sum()
            if total_pkt_count_sum > 0:
                d["avg_pkt_size"] = int(total_byte_rate_sum / total_pkt_count_sum)
            else:
                d["avg_pkt_size"] = 0
            # get script version from test
            d["version"] = self.df_base.loc[self.df_base["test_name"] == name, "version"].iloc[0]

            # get report link for current test - changed to take from last row in test
            # d["report"] = self.df_base.loc[self.df_base["tps"] == d["tps_max"], "report"].iloc[0]
            d["report"] = self.df_base.loc[self.df_base["test_name"] == name, "report"].iloc[-1]

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
                    "avg_pkt_size",
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
            "avg_pkt_size": {
                "width": "7em",
                "min-width": "6em",
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
            "version": {"width": "3em", "min-width": "3em", "text-align": "right"},
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
