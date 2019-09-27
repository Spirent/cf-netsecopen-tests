import requests
import json
import logging
import sys
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

fmt_str = "[%(asctime)s] %(levelname)s %(lineno)d: %(message)s"
logging.basicConfig(
    filename="cf.log", filemode="w", level=logging.DEBUG, format=fmt_str
)
log = logging.getLogger(__name__)
log.debug("start logging")


class CfClient:
    def __init__(self, controller_ip, username, password, verify_ssl):
        log.debug("Initializing a new object of the CfClient class.")
        self.log = logging.getLogger("requests.packages.urllib3")
        self.username = username
        self.password = password
        self.controller_ip = controller_ip
        self.api = "https://" + self.controller_ip + "/api/v2"
        self.__session = requests.session()
        self.__session.verify = verify_ssl
        self.exception_state = True
        retries = Retry(
            total=5, backoff_factor=1, status_forcelist=[422, 500, 502, 503, 504]
        )
        self.__session.mount("https://", HTTPAdapter(max_retries=retries))

    def connect(self):
        self.exception_state = True
        log.debug("Inside the CfClient/connect method.")
        credentials = {"email": self.username, "password": self.password}
        try:
            response = self.__session.post(
                self.api + "/token", data=credentials, timeout=10
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as errh:
            self.requests_error_handler("http", errh, response)
        except requests.exceptions.ConnectionError as errc:
            self.requests_error_handler("connection", errc, None)
        except requests.exceptions.Timeout as errt:
            self.requests_error_handler("timeout", errt, None)
        except requests.exceptions.RequestException as err:
            self.requests_error_handler("other", err, None)
        self.exception_continue_check()
        dict_response = response.json()
        print(dict_response)
        if "token" in dict_response:
            self.__session.headers["Authorization"] = "Bearer " + dict_response["token"]

    def get_test(self, test_type, test_id, outfile):
        self.exception_state = True
        try:
            response = self.__session.get(
                self.api + "/tests/" + test_type + "/" + test_id
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as errh:
            self.requests_error_handler("http", errh, response)
        except requests.exceptions.ConnectionError as errc:
            self.requests_error_handler("connection", errc, None)
        except requests.exceptions.Timeout as errt:
            self.requests_error_handler("timeout", errt, None)
        except requests.exceptions.RequestException as err:
            self.requests_error_handler("other", err, None)

        dict_response = response.json()
        with open(outfile, "w") as f:
            json.dump(dict_response, f, indent=4)
        return dict_response

    def fetch_test_template(self, test_type, outfile):
        self.exception_state = True
        try:
            response = self.__session.get(
                self.api + "/tests/" + test_type + "/template"
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as errh:
            self.requests_error_handler("http", errh, response)
        except requests.exceptions.ConnectionError as errc:
            self.requests_error_handler("connection", errc, None)
        except requests.exceptions.Timeout as errt:
            self.requests_error_handler("timeout", errt, None)
        except requests.exceptions.RequestException as err:
            self.requests_error_handler("other", err, None)

        dict_response = response.json()
        with open(outfile, "w") as f:
            json.dump(dict_response, f, indent=4)
        return dict_response

    def post_test(self, test_type, infile):
        self.exception_state = True
        with open(infile, "r") as f:
            intest = json.load(f)
        try:
            response = self.__session.post(
                self.api + "/tests/" + test_type + "/", json=intest
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as errh:
            self.requests_error_handler("http", errh, response)
        except requests.exceptions.ConnectionError as errc:
            self.requests_error_handler("connection", errc, None)
        except requests.exceptions.Timeout as errt:
            self.requests_error_handler("timeout", errt, None)
        except requests.exceptions.RequestException as err:
            self.requests_error_handler("other", err, None)
        self.exception_continue_check()
        print(response)
        dict_response = response.json()
        return dict_response

    def update_test(self, test_type, test_id, infile):
        self.exception_state = True
        with open(infile, "r") as f:
            intest = json.load(f)
            print(intest)
        try:
            response = self.__session.put(
                self.api + "/tests/" + test_type + "/" + test_id, json=intest
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as errh:
            self.requests_error_handler("http", errh, response)
        except requests.exceptions.ConnectionError as errc:
            self.requests_error_handler("connection", errc, None)
        except requests.exceptions.Timeout as errt:
            self.requests_error_handler("timeout", errt, None)
        except requests.exceptions.RequestException as err:
            self.requests_error_handler("other", err, None)
        self.exception_continue_check()
        dict_response = response.json()
        return dict_response

    def delete_test(self, test_type, test_id):
        self.exception_state = True
        try:
            response = self.__session.delete(
                self.api + "/tests/" + test_type + "/" + test_id
            )
        except requests.exceptions.HTTPError as errh:
            self.requests_error_handler("http", errh, response)
        except requests.exceptions.ConnectionError as errc:
            self.requests_error_handler("connection", errc, None)
        except requests.exceptions.Timeout as errt:
            self.requests_error_handler("timeout", errt, None)
        except requests.exceptions.RequestException as err:
            self.requests_error_handler("other", err, None)

        return response

    def get_queue(self, queue_id):
        self.exception_state = True
        try:
            response = self.__session.get(self.api + "/queues/" + queue_id)
        except requests.exceptions.HTTPError as errh:
            self.requests_error_handler("http", errh, response)
        except requests.exceptions.ConnectionError as errc:
            self.requests_error_handler("connection", errc, None)
        except requests.exceptions.Timeout as errt:
            self.requests_error_handler("timeout", errt, None)
        except requests.exceptions.RequestException as err:
            self.requests_error_handler("other", err, None)
        self.exception_continue_check()
        dict_response = response.json()
        return dict_response

    def start_test(self, test_id):
        self.exception_state = True
        try:
            response = self.__session.put(self.api + "/tests/" + test_id + "/start")
            response.raise_for_status()
        except requests.exceptions.HTTPError as errh:
            self.requests_error_handler("http", errh, response)
        except requests.exceptions.ConnectionError as errc:
            self.requests_error_handler("connection", errc, None)
        except requests.exceptions.Timeout as errt:
            self.requests_error_handler("timeout", errt, None)
        except requests.exceptions.RequestException as err:
            self.requests_error_handler("other", err, None)
        self.exception_continue_check()
        dict_response = response.json()
        return dict_response

    def list_test_runs(self):
        self.exception_state = True
        try:
            response = self.__session.get(self.api + "/test_runs")
        except requests.exceptions.HTTPError as errh:
            self.requests_error_handler("http", errh, response)
        except requests.exceptions.ConnectionError as errc:
            self.requests_error_handler("connection", errc, None)
        except requests.exceptions.Timeout as errt:
            self.requests_error_handler("timeout", errt, None)
        except requests.exceptions.RequestException as err:
            self.requests_error_handler("other", err, None)
        self.exception_continue_check()
        dict_response = response.json()
        return dict_response

    def get_test_run(self, test_run_id):
        self.exception_state = True
        try:
            response = self.__session.get(self.api + "/test_runs/" + test_run_id)
        except requests.exceptions.HTTPError as errh:
            self.requests_error_handler("http", errh, response)
        except requests.exceptions.ConnectionError as errc:
            self.requests_error_handler("connection", errc, None)
        except requests.exceptions.Timeout as errt:
            self.requests_error_handler("timeout", errt, None)
        except requests.exceptions.RequestException as err:
            self.requests_error_handler("other", err, None)
        self.exception_continue_check()
        dict_response = response.json()
        return dict_response

    def fetch_test_run_statistics(self, test_run_id):
        self.exception_state = True
        try:
            response = self.__session.get(
                self.api + "/test_runs/" + test_run_id + "/statistics"
            )
        except requests.exceptions.HTTPError as errh:
            self.requests_error_handler("http", errh, response)
        except requests.exceptions.ConnectionError as errc:
            self.requests_error_handler("connection", errc, None)
        except requests.exceptions.Timeout as errt:
            self.requests_error_handler("timeout", errt, None)
        except requests.exceptions.RequestException as err:
            self.requests_error_handler("other", err, None)
        self.exception_continue_check()
        dict_response = response.json()
        return dict_response

    def stop_test(self, test_run_id):
        self.exception_state = True
        try:
            response = self.__session.put(
                self.api + "/test_runs/" + test_run_id + "/stop"
            )
        except requests.exceptions.HTTPError as errh:
            self.requests_error_handler("http", errh, response)
        except requests.exceptions.ConnectionError as errc:
            self.requests_error_handler("connection", errc, None)
        except requests.exceptions.Timeout as errt:
            self.requests_error_handler("timeout", errt, None)
        except requests.exceptions.RequestException as err:
            self.requests_error_handler("other", err, None)
        self.exception_continue_check()
        dict_response = response.json()
        return dict_response

    def change_load(self, test_run_id, new_load):
        self.exception_state = True
        load = {"load": new_load}
        try:
            response = self.__session.put(
                self.api + "/test_runs/" + test_run_id + "/changeload", data=load
            )
        except requests.exceptions.HTTPError as errh:
            self.requests_error_handler("http", errh, response)
        except requests.exceptions.ConnectionError as errc:
            self.requests_error_handler("connection", errc, None)
        except requests.exceptions.Timeout as errt:
            self.requests_error_handler("timeout", errt, None)
        except requests.exceptions.RequestException as err:
            self.requests_error_handler("other", err, None)
        self.exception_continue_check()
        dict_response = response.json()
        log.debug(f"change load: {load} > {json.dumps(dict_response, indent=4)}")
        return dict_response

    def get_system_version(self):
        self.exception_state = True
        try:
            response = self.__session.get(self.api + "/system/version")
        except requests.exceptions.HTTPError as errh:
            self.requests_error_handler("http", errh, response)
        except requests.exceptions.ConnectionError as errc:
            self.requests_error_handler("connection", errc, None)
        except requests.exceptions.Timeout as errt:
            self.requests_error_handler("timeout", errt, None)
        except requests.exceptions.RequestException as err:
            self.requests_error_handler("other", err, None)
        self.exception_continue_check()
        dict_response = response.json()
        return dict_response

    def requests_error_handler(self, error_type, error_response, json_response):
        if error_type == "http":
            report_error = f"Http Error: {error_response}"
        elif error_type == "connection":
            report_error = f"Error Connecting: {error_response}"
        elif error_type == "timeout":
            report_error = f"Timeout Error: {error_response}"
        elif error_type == "other":
            report_error = (
                f"Other error, not http, connection or timeout error: {error_response}"
            )
        else:
            report_error = f"unknown"

        log.debug(report_error)
        print(report_error)
        if json_response is not None:
            log.debug(json_response.json())
            print(json_response.json())
        # sys.exit(1)
        self.exception_state = False

    def exception_continue_check(self):
        if not self.exception_state:
            sys.exit(1)
