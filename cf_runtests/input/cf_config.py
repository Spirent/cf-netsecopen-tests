# Configuration file

# IMPORTANT:
# Create addition file in input directory with name 'credentials.py'.
# In this file have following two lines:
# username = 'user@company.com'
# password = 'password'


# FQDN or IP address of the CyberFlood Controller. Do NOT prefix with https://
cf_controller_address = "cyberflood.company.com"
# file locations
in_project_dir = True,  # set to true if in main project dir, if set to False provide full path
report_location = "report"
input_location = "input"
output_location = "output"
#  TLS certificate validation - False or True
verify_ssl = False


# create_tests.py base test ID - use working HTTP Throughput test from controller.
# create_tests will use this ID to copy port group, subnets and other settings from.
create_tests_base_test_id = '30cb822c541ad0b3aadbde98b915f471'
create_test_source_csv = 'create_tests_nso.csv'  # located in input sub directory, do not put subdir in var
reference_to_run_csv_file = 'run_tests_reference.csv'
test_to_run_csv_file = 'run_tests.csv'
# Files for logging purposes:
create_tests_output_list_csv = 'created_tests.csv'  # located in output sub directory
create_tests_base_type = 'http_throughput'  # 'http_throughput' or 'http_connections_per_second'
create_tests_base_file = 'base_test_config.json'  # located in output sub directory, do not put subdir in var

# get_test.py - get copy of test ID
get_test_id = 'c71c621a39bb9d10862bf30182d14796'
get_test_type = 'http_throughput'  # 'http_throughput' or 'http_connections_per_second'
get_test_to_file = 'get_test_config.json'

# delete_created_tests.py
delete_tests_csv = create_tests_output_list_csv  # csv file with tests to delete - from Global_settings output_location

# run_tests.py
run_tests_from_csv = 'run_tests.csv'  # from Global_settings input_location

# html_report.py and report portion of run_test.py
html_report_csv = None  # If None take latest csv file from Report directory
report_tables = ['HTTP-CPS', 'HTTP-TPUT', 'TLS-CPS', 'TLS-TPUT', 'HTTP-LAT', 'TLS-LAT', 'HTTP-CON', 'TLS-CON', None]
col_order = ['test_name', 'cps', 'tps', 'total_bandwidth', 'open_conns',
             'tcp_avg_tt_synack', 'tcp_avg_ttfb', 'url_response_time',
             'successful_txn', 'unsuccessful_txn', 'aborted_txn',
             'total_tcp_established', 'total_tcp_attempted',
             'tps_stdy_min', 'tps_stdy_max', 'tps_stdy_delta',
             'seconds', 'current_load',
             'max_tps_seconds', 'max_tps_load', 'tps_max', 'cps_max',
             'total_bandwidth_max', 'report',
             'client_cpu', 'server_cpu', 'client_pkt_mem', 'server_pkt_mem',
             'client_rcv_queue', 'server_rcv_queue',
             "t_run", "t_start", "t_tx", "t_stop",
             ]
html_additional_reports = {
    'sum': ['test_name', 'cps', 'tps', 'total_bandwidth', 'open_conns'],
    'kpi': ['test_name', 'cps', 'tps', 'total_bandwidth', 'open_conns', 'tcp_avg_ttfb', 'url_response_time', 'report'],
    'all': col_order
}


