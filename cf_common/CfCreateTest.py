import json
import logging
import pathlib
import csv

from cf_common.CfClient import *


class BaseTest:
    def __init__(self, base):
        try:
            self.id = base["id"]
            self.projectId = base["projectId"]
            self.queue = base["config"]["queue"]
            self.debug = base["config"]["debug"]
            self.subnets = base["config"]["subnets"]
            self.criteria = base["config"]["criteria"]
            self.networks = base["config"]["networks"]
            self.interfaces = base["config"]["interfaces"]
            self.protocol = base["config"]["protocol"]
            self.virtualRouters = base["config"]["virtualRouters"]
            self.trafficPattern = base["config"]["trafficPattern"]
            self.testType = base["config"]["testType"]
            self.loadSpecification = base["config"]["loadSpecification"]
        except Exception as e:
            print(f"\nBase test missing data \n{e}")


class CfCreateTest(BaseTest):
    def __init__(self, base, test_info, test_template, cf_ver):
        super().__init__(base)
        self.name = test_info["name"]
        self.type = test_info["type"]
        self.connection_type = test_info["connection_type"]
        self.keep_alive = test_info["keep_alive"]
        self.transactions = self.chk_none(test_info["transactions_connection"])
        self.delay_time = self.chk_none(test_info["delay_time"])
        self.delay_time_unit = self.chk_none(test_info["delay_unit"])
        self.object_type = self.chk_none(test_info["object_type"])
        self.object_size = self.chk_none(test_info["object_size"])
        self.delayed_ack = self.chk_none(test_info["delayed_ack"])
        self.initial_congestion_window = self.chk_none(test_info["icw"])
        self.rx_window = self.chk_none(test_info["rx_window"])
        self.ipV4SegmentSize = self.chk_none(test_info["ipV4SegmentSize"])
        self.ipV6SegmentSize = self.chk_none(test_info["ipV6SegmentSize"])
        self.retries = self.chk_none(test_info["retries"])
        self.tls = self.chk_none(test_info["sslTls"])
        self.tls_version = self.chk_none(test_info["tls_version"])
        self.certificate = self.chk_none(test_info["certificate"])
        self.ciphers = self.chk_none(test_info["ciphers"])
        self.supportedGroups = self.chk_none(test_info["supportedGroups"])
        self.signature_hash = self.chk_none(test_info["signature_hash"])
        self.tls_record = self.chk_none(test_info["tls_record"])
        self.payload_encryption_offload = test_info["payloadEncryptionOffload"]
        self.http_method = self.chk_none(test_info["http_method"])
        self.post_size = self.chk_none(test_info["post_size"])
        self.name_suffix = test_info["name_suffix"]
        self.name = self.name + "_" + self.name_suffix

        self.existing_certificate = self.protocol["supplemental"]["sslTls"][
            "certificate"
        ]
        self.protocol = test_template["config"]["protocol"]
        self.existing_load_constraints = self.loadSpecification["constraints"]
        self.loadSpecification = test_template["config"]["loadSpecification"]

        self.cf_version = int("".join(i for i in cf_ver if i.isdigit()))

    def complete_test(self):
        comp_test = {}
        comp_test["name"] = self.name
        comp_test["projectId"] = self.projectId
        comp_test["config"] = {}
        comp_test["config"]["queue"] = self.queue
        comp_test["config"]["debug"] = self.debug
        comp_test["config"]["subnets"] = self.subnets
        comp_test["config"]["criteria"] = self.criteria
        comp_test["config"]["networks"] = self.networks
        comp_test["config"]["interfaces"] = self.interfaces
        comp_test["config"]["protocol"] = self.protocol
        comp_test["config"]["virtualRouters"] = self.virtualRouters
        comp_test["config"]["trafficPattern"] = self.trafficPattern
        comp_test["config"]["testType"] = self.testType
        comp_test["config"]["loadSpecification"] = self.loadSpecification
        return comp_test

    def save_test(self, outfile):
        with open(outfile, "w") as f:
            json.dump(self.complete_test(), f, indent=4)

    def update_network_settings(self):
        try:
            self.networks["client"]["initialCongestionWindow"] = int(
                self.initial_congestion_window
            )
            self.networks["client"]["receiveWindow"] = int(self.rx_window)
            self.networks["client"]["delayedAcks"]["bytes"] = int(self.delayed_ack)
            self.networks["client"]["retries"] = int(self.retries)
            self.networks["client"]["inactivityTimer"] = 0
            self.networks["server"]["initialCongestionWindow"] = int(
                self.initial_congestion_window
            )
            self.networks["server"]["receiveWindow"] = int(self.rx_window)
            self.networks["server"]["delayedAcks"]["bytes"] = int(self.delayed_ack)
            self.networks["server"]["retries"] = int(self.retries)
            self.networks["server"]["inactivityTimer"] = 0
        except Exception as e:
            print(f"\nUnable to set network settings \n{e}")
        try:
            self.networks["client"]["ipV4SegmentSize"] = int(self.ipV4SegmentSize)
            self.networks["client"]["ipV6SegmentSize"] = int(self.ipV6SegmentSize)
            self.networks["server"]["ipV4SegmentSize"] = int(self.ipV4SegmentSize)
            self.networks["server"]["ipV6SegmentSize"] = int(self.ipV6SegmentSize)
        except Exception as e:
            print(f"\nUnable to set MSS in network settings \n{e}")

    def update_criteria_settings(self):
        try:
            self.criteria["enabled"] = False
        except Exception as e:
            print(f"\nUnable to set criteria settings \n{e}")

    def update_load_constraints(self):
        try:
            self.loadSpecification["constraints"] = self.existing_load_constraints
        except Exception as e:
            print(f"\nUnable to set load constraints\n{e}")

    def update_close_with_fin(self):
        try:
            self.protocol["connectionTermination"] = "FIN"
            self.networks["client"]["closeWithFin"] = True
        except Exception as e:
            print(f"\nUnable to set close tcp connection close with fin settings \n{e}")

    def update_transactions(
        self, connection_type, keep_alive, count, delay_time, delay_time_unit
    ):
        if keep_alive.lower() in {"true"}:
            keep_alive = True
        elif keep_alive.lower() in {"false"}:
            keep_alive = False
        if connection_type.lower() in {"keepalive"}:
            connection_type = "keepAlive"
        elif connection_type.lower() in {"separateconnections", "separate"}:
            connection_type = "separateConnections"

        try:
            self.protocol["connection"]["type"] = connection_type
        except Exception as e:
            print(f"\nUnable to set connection_type \n{e}")
        try:
            self.protocol["keepAlive"]["enabled"] = keep_alive
        except Exception as e:
            print(f"\nUnable to set keepAlive \n{e}")
        try:
            self.protocol["keepAlive"]["count"] = int(count)
        except Exception as e:
            print(f"\nUnable to set transaction count \n{e}")
        try:
            self.protocol["keepAlive"]["delayTime"] = int(delay_time)
            self.protocol["keepAlive"]["delayTimeUnit"] = delay_time_unit
        except Exception as e:
            print(f"\nUnable to set per request delay_time and unit \n{e}")

    def update_http_method(self, http_method, post_size):
        if http_method.lower() == "post":
            http_method = "POST"
            try:
                self.protocol["method"] = http_method
            except Exception as e:
                print(f"\nUnable to set POST method \n{e}")
            try:
                self.protocol["bodySizeInBytes"] = int(post_size)
            except Exception as e:
                print(f"\nUnable to set POST bodySizeInBytes \n{e}")

    def update_object_size(self, object_type, byte_size):
        if object_type == "fixed":
            # print(f'Changing object size to: {byte_size}')
            try:
                self.protocol["responseBodyType"]["type"] = "fixed"
                self.protocol["responseBodyType"]["config"] = {}
                self.protocol["responseBodyType"]["config"]["type"] = "default"
                self.protocol["responseBodyType"]["config"]["bytes"] = int(byte_size)
            except Exception as e:
                print(f"\nUnable to set responseBodyType\n{e}")
        elif object_type == "fixed-random":
            # print(f'Changing object size to: {byte_size}')
            if int(byte_size) <= 16000:
                random_length = int(byte_size)
            else:
                random_length = 16000
            try:
                self.protocol["responseBodyType"]["type"] = "fixed"
                self.protocol["responseBodyType"]["config"] = {}
                self.protocol["responseBodyType"]["config"]["type"] = "random"
                self.protocol["responseBodyType"]["config"]["pseudoRandom"] = True
                self.protocol["responseBodyType"]["config"]["length"] = int(
                    random_length
                )
                self.protocol["responseBodyType"]["config"]["bytes"] = int(byte_size)
            except Exception as e:
                print(f"\nUnable to set responseBodyType\n{e}")
        elif object_type == "mixed":
            # print(f'Changing object size to: {byte_size}')
            try:
                self.protocol["responseBodyType"]["type"] = "mixed"
                self.protocol["responseBodyType"]["config"] = {}
                self.protocol["responseBodyType"]["config"]["type"] = "default"
                self.protocol["responseBodyType"]["config"]["distributions"] = [
                    200,
                    6000,
                    8000,
                    9000,
                    10000,
                    25000,
                    26000,
                    35000,
                    59000,
                    347000,
                ]
            except Exception as e:
                print(f"\nUnable to set responseBodyType\n{e}")
        elif object_type == "mixed-random":
            # print(f'Changing object size to: {byte_size}')
            try:
                self.protocol["responseBodyType"]["type"] = "mixed"
                self.protocol["responseBodyType"]["config"] = {}
                self.protocol["responseBodyType"]["config"]["type"] = "random"
                self.protocol["responseBodyType"]["config"]["pseudoRandom"] = True
                self.protocol["responseBodyType"]["config"]["length"] = 16000
                self.protocol["responseBodyType"]["config"]["distributions"] = [
                    200,
                    6000,
                    8000,
                    9000,
                    10000,
                    25000,
                    26000,
                    35000,
                    59000,
                    347000,
                ]
            except Exception as e:
                print(f"\nUnable to set responseBodyType\n{e}")
        else:
            # print(f'Changing object size to: {byte_size}')
            try:
                self.protocol["responseBodyType"]["config"]["bytes"] = int(byte_size)
            except Exception as e:
                print(f"\nUnable to set responseBodyType bytes\n{e}")

    def update_tls(
        self,
        tls,
        tls_version,
        certificate,
        ciphers,
        supported_groups,
        signature_hash,
        tls_record,
        payload_encryption_offload,
    ):
        if tls.lower() in {"true"}:
            tls = True
        elif tls.lower() in {"false"}:
            tls = False
        try:
            self.protocol["supplemental"]["sslTls"]["enabled"] = tls
        except Exception as e:
            print(f"\nUnable to set sslTls enabled state \n{e}")
        if tls:
            self.update_tls_base_setting(tls_version, tls_record)
        if certificate is not None:
            self.update_tls_certificate(certificate, self.existing_certificate)
        if ciphers is not None:
            self.update_tls_ciphers(ciphers)
        if supported_groups is not None:
            self.update_tls_supported_groups(supported_groups)
        if signature_hash is not None:
            self.update_tls_signature_hash(signature_hash)

        self.update_tls_payload_encryption_offload(payload_encryption_offload)

    def update_tls_base_setting(self, tls_version, tls_record):
        try:
            self.protocol["port"] = 443
        except Exception as e:
            print(f"\nUnable to set sslTls enabled state \n{e}")
        if self.tls_version is not None:
            try:
                # using tls_version as var to set right tls key to true
                self.protocol["supplemental"]["sslTls"][tls_version] = True
            except Exception as e:
                print(f"\nUnable to set tls_version \n{e}")
        if tls_record is not None:
            try:
                self.protocol["supplemental"]["sslTls"]["bytes"] = int(tls_record)
            except Exception as e:
                print(f"\nUnable to set certificate \n{e}")

    def update_tls_certificate(self, certificate, existing_certificate):
        if certificate == "custom":
            try:
                self.protocol["supplemental"]["sslTls"][
                    "certificate"
                ] = existing_certificate
            except Exception as e:
                print(f"\nUnable to set custom certificate \n{e}")
        else:
            try:
                self.protocol["supplemental"]["sslTls"]["certificate"] = certificate
            except Exception as e:
                print(f"\nUnable to set certificate \n{e}")

    def update_tls_ciphers(self, ciphers):
        cipher_list = []
        if isinstance(ciphers, list):
            cipher_list = ciphers
        else:
            cipher_list.append(ciphers)
        try:
            self.protocol["supplemental"]["sslTls"]["ciphers"] = cipher_list
        except Exception as e:
            print(f"\nUnable to set ciphers \n{e}")

    def update_tls_supported_groups(self, supported_groups):
        if self.cf_version < 19300000:
            log.info(f"Not setting TLS supported group. CF version is below {19300000}")
            return
        # check if supportedGroups exists in test config
        # set all supportedGroup options to False
        if "supportedGroups" in self.protocol["supplemental"]["sslTls"]:
            for k, v in self.protocol["supplemental"]["sslTls"][
                "supportedGroups"
            ].items():
                self.protocol["supplemental"]["sslTls"]["supportedGroups"][k] = False
            try:
                # using supportedGroups as var to set right group key to true
                self.protocol["supplemental"]["sslTls"]["supportedGroups"][
                    supported_groups
                ] = True
            except Exception as e:
                print(f"\nUnable to set supportedGroups \n{e}")

    def update_tls_signature_hash(self, signature_hash):
        if self.cf_version < 19300000:
            log.info(f"Not setting TLS signature hash. CF version is below {19300000}")
            return
        signature_hash_list = []
        if isinstance(signature_hash, list):
            signature_hash_list = signature_hash
        else:
            signature_hash_list.append(signature_hash)
        try:
            self.protocol["supplemental"]["sslTls"][
                "signatureHashAlgorithmsList"
            ] = signature_hash_list
        except Exception as e:
            print(f"\nUnable to set TLS signature hash \n{e}")

    def update_tls_payload_encryption_offload(self, payload_encryption_offload):
        if self.cf_version < 19400000:
            log.info(
                f"Not setting payloadEncryptionOffload. "
                f"CF version is below {19400000}"
            )
            return
        if payload_encryption_offload.lower() in {"true"}:
            payload_encryption_offload = True
        elif payload_encryption_offload.lower() in {"false"}:
            payload_encryption_offload = False
        try:
            self.protocol["supplemental"]["sslTls"][
                "payloadEncryptionOffload"
            ] = payload_encryption_offload
        except Exception as e:
            print(f"\nUnable to set payloadEncryptionOffload state \n{e}")

    @staticmethod
    def chk_none(value):
        if isinstance(value, (int, float)):
            return value
        elif value.lower() in {"none"}:
            return None
        else:
            return value

    def update_config_changes(self):
        self.update_network_settings()
        self.update_criteria_settings()
        # self.update_load_constraints()
        self.update_close_with_fin()
        if 19300000 < self.cf_version:
            self.update_http_method(self.http_method, self.post_size)
        if self.object_size is not None:
            self.update_object_size(self.object_type, self.object_size)
        if self.keep_alive is not None:
            self.update_transactions(
                self.connection_type,
                self.keep_alive,
                self.transactions,
                self.delay_time,
                self.delay_time_unit,
            )
        if self.tls is not None:
            self.update_tls(
                self.tls,
                self.tls_version,
                self.certificate,
                self.ciphers,
                self.supportedGroups,
                self.signature_hash,
                self.tls_record,
                self.payload_encryption_offload,
            )


class TestsToRun:
    def __init__(self, reference_to_run_csv_file, test_to_run_csv_file):
        self.test_to_run_csv_file = test_to_run_csv_file
        with open(reference_to_run_csv_file, "r") as f:
            self.reference_tests = list(csv.DictReader(f))
        # write headers to tests to run csv file
        with open(self.test_to_run_csv_file, "w") as f:
            # self.tests_to_run_headers = (f'name, id, type, run, goal_seek, duration, startup, rampup, rampdown,	'
            #                  f'shutdown, sustain_period, load_type, start_load, incr_low, incr_med, incr_high, '
            #                  f'low_threshold, med_threshold, high_threshold')
            f.write(self.test_header_csv_line(self.reference_tests))

    def add_test(self, new_test_dict, test_type):
        test_ref_match = False
        for test in self.reference_tests:
            if new_test_dict["name"].startswith(test["name"]):
                test_csv_info = self.test_csv_line_values(
                    test, new_test_dict, test_type
                )
                test_ref_match = True
                print(f"{test['name']}\n{test_csv_info}")
                with open(self.test_to_run_csv_file, "a") as f:
                    f.write(test_csv_info)
        if not test_ref_match:
            test_csv_info = self.test_csv_line_values(
                self.reference_tests[0], new_test_dict, test_type
            )
            print(f"{test['name']}\n{test_csv_info}")
            with open(self.test_to_run_csv_file, "a") as f:
                f.write(test_csv_info)

    @staticmethod
    def test_header_csv_line(reference_tests):
        csv_line = f"name,id,type,"
        for key in reference_tests[0]:
            if key not in {"name", "id", "type"}:
                csv_line = csv_line + key + ","
        csv_line = csv_line[:-1] + "\n"  # remove last comma and add end line
        return csv_line

    @staticmethod
    def test_csv_line_values(reference_test, new_test_dict, test_type):
        csv_line = f"{new_test_dict['name']},{new_test_dict['id']},{test_type},"
        for key, value in reference_test.items():
            if key not in {"name", "id", "type"}:
                csv_line = csv_line + value + ","
        csv_line = csv_line[:-1] + "\n"  # remove last comma and add end line
        return csv_line
