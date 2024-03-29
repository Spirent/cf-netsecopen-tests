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

    def create_log_response(self, resp):
        with open(("response.log"), "w") as f:
            f.write(str(resp))
        return True
    
    def append_log_response(self, method, status, url, resp):
        s = f'\n{method} {status} {url}\n{resp}'
        with open(("response.log"), "a") as f:
            f.write(s)
        return True

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
        self.create_log_response(dict_response)
        if "token" in dict_response:
            self.__session.headers["Authorization"] = "Bearer " + dict_response["token"]
        
    def get_test(self, test_type, test_id, outfile):
        self.exception_state = True
        url = self.api + "/tests/" + test_type + "/" + test_id
        try:
            response = self.__session.get(url)
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
        self.append_log_response('get', response.status_code, url, dict_response)
        with open(outfile, "w") as f:
            json.dump(dict_response, f, indent=4)
        return dict_response

    def fetch_test_template(self, test_type, outfile):
        self.exception_state = True
        url = self.api + "/tests/" + test_type + "/template"
        try:
            response = self.__session.get(url)
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
        if test_type == "advanced_mixed_traffic":
            dict_response["config"]["trafficMix"]["mixer"] = self.fetch_amt_predefinedprotocols()
        self.append_log_response('get', response.status_code, url, dict_response)
        with open(outfile, "w") as f:
            json.dump(dict_response, f, indent=4)
        return dict_response

    def fetch_amt_predefinedprotocols(self):
        self.exception_state = True
        url = self.api + "/tests/advanced_mixed_traffic/predefined_protocols"
        try:
            response = self.__session.get(url)
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
        self.append_log_response('get', response.status_code, url, dict_response)
        return dict_response

    def post_test(self, test_type, infile):
        self.exception_state = True
        with open(infile, "r") as f:
            intest = json.load(f)
        url = self.api + "/tests/" + test_type + "/"
        try:
            response = self.__session.post(url, json=intest)
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
        self.append_log_response('post', response.status_code, url, dict_response)
        return dict_response

    def update_test(self, test_type, test_id, infile):
        self.exception_state = True
        with open(infile, "r") as f:
            intest = json.load(f)
            print(intest)
        url = self.api + "/tests/" + test_type + "/" + test_id
        try:
            response = self.__session.put(url, json=intest)
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
        self.append_log_response('put', response.status_code, url, dict_response)
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
        url = self.api + "/queues/" + queue_id
        try:
            response = self.__session.get(url)
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
        self.append_log_response('get', response.status_code, url, dict_response)
        return dict_response

    def start_test(self, test_id):
        self.exception_state = True
        url = self.api + "/tests/" + test_id + "/start"
        try:
            response = self.__session.put(url)
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
        self.append_log_response('put', response.status_code, url, dict_response)
        return dict_response

    def list_test_runs(self):
        self.exception_state = True
        url = self.api + "/test_runs"
        try:
            response = self.__session.get(url)
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
        self.append_log_response('get', response.status_code, url, dict_response)
        return dict_response

    def get_test_run(self, test_run_id):
        self.exception_state = True
        url = self.api + "/test_runs/" + test_run_id
        try:
            response = self.__session.get(url)
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
        self.append_log_response('get', response.status_code, url, dict_response)
        return dict_response

    def fetch_test_run_statistics(self, test_run_id):
        self.exception_state = True
        url = self.api + "/test_runs/" + test_run_id + "/statistics"
        try:
            response = self.__session.get(url)
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
        self.append_log_response('get', response.status_code, url, dict_response)
        return dict_response

    def fetch_event_logs(self, test_run_id):
        self.exception_state = True
        url = self.api + "/test_runs/" + test_run_id + "/eventlogs"
        try:
            response = self.__session.get(url)
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
        self.append_log_response('get', response.status_code, url, dict_response)
        return dict_response

    def stop_test(self, test_run_id):
        self.exception_state = True
        url = self.api + "/test_runs/" + test_run_id + "/stop"
        try:
            response = self.__session.put(url)
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
        self.append_log_response('put', response.status_code, url, dict_response)
        return dict_response

    def change_load(self, test_run_id, new_load):
        self.exception_state = True
        load = {"load": new_load}
        url = self.api + "/test_runs/" + test_run_id + "/changeload"
        try:
            response = self.__session.put(url, data=load)
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
        self.append_log_response('put', response.status_code, url, dict_response)
        log.debug(f"change load: {load} > {json.dumps(dict_response, indent=4)}"
                  f"response: {response}")
        return dict_response

    def get_system_version(self):
        self.exception_state = True
        url = self.api + "/system/version"
        try:
            response = self.__session.get(url)
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
        self.append_log_response('get', response.status_code, url, dict_response)
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
