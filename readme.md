## CyberFlood NetSecOPEN Automation Script

### Installing and running the script
Script requires python 3.7 or higher.

To install python dependencies use following command:

pip install -r requirements.txt

(if python3 use pip3 instead of pip)

To use script:
1. edit credentials.py
2. set controller IP in config.py file
3. configure a throughput test with queue and subnets on the controller (in a project)
4. copy the test id from the browser url bar (last part of URL)
5. paste test id under create_test.py section of config.py file
6. optionally edit /input/create_tests_nso.csv file for tests to create
7. run create_tests.py script: python create_tests.py (use python3 with multiple versions)
8. edit capacity_adjust column in run_tests.csv. Default load is simuser per core.
   E.g. for C100-S3 10G, use 3 (has 3 cores per port), 100G use 14. etc.
9. run tests: python run_tests.py

In case of path errors when executing the scripts.
Add project to python path (add the project, not the cf_runtest sub dir)

Linux: 
export PYTHONPATH=/path/to/cf-netsecopen-tests:$PYTHONPATH

Windows: 
set PYTHONPATH=%PYTHONPATH%;C:\path\to\cf-netsecopen-tests

### Run_tests.csv parameters

- name: name of the test in CyberFlood
- id: CyberFlood test ID, this is the id at the end of a tests configuration URL.
- type: CyberFlood test type, can be 'http_throughput', 'http_connections_per_second', 'open_connections' or 'emix'.
- run: Y or N to run test, useful to run only select tests.
- run_oder: tests run in order of this field 0 being first. When multiple tests have the same order number they run in order of the list. To support sub ordering later 11 will run before 2.
- goal_seek: Y or N for goal seeking. If N, the script runs the tests per the load spec with ramp to the start_load value.
- ramp_seek: Y or N for optional additional ramp to ramp_kpi value after ramp to start_load and before goal seeking.
- ramp_kpi: tps, cps, bw, conns or ttfb, kpi type for ramp_value.
- ramp_value: number the script will attempt to ramp up to.
- ramp_step: number of steps to ramp up to the ramp_value before starting goal seeking.
- duration: maximum duration of test. When goal seeking the test will stop if the goal has not been reached after this time. Without goal seeking the duration minus startup, rampup, rampdown and shutdown is the steady state period of the test.
- startup: time before traffic starts.
- rampup: duration of ramp to start_load value.
- rampdown: duration of ramp to no load at the end of the steady phase. Not used when goal seeking.
- shutdown: time after rampdown to allow connections to close.
- sustain_period: time to run test after maximum load has been reached in goal seeking. Only used in goal seeking. The script report has the average of this phase. Default is 30s. NetSecOPEN certification requires this value to be changed to 300s.
- kpi_1: tps (default), cps, bw, conns or ttfb. Primary kpi to determine if load is stable before further load increases.
- kpi_2: cps (default), tps, bw, conns or ttfb. Secondary kpi to determine if load is stable before further load increases.
- kpi_and_or: 'AND' or 'OR'. If set to OR load stability is determined from either value. If set to AND both KPIs have to be stable before further load increases.
- load_type: 'Simusers', 'Simusers/Second', Bandwidth', 'Connections/Second' or 'connections'. CyberFlood load spec type for start_load and incremental load values.
- start_load: starting load for selected load_type. Every test will ramp up to this load. Defaults are starting simuser load type. If load is set to bandwidth 1000000 is 1 Gbps.
- incr_low: initial goal seek load increase and subsequent increases if average kpi_1 increase is higher than low_threshold. For simusers(/second) load type the threshold is a percentage between 0 and 100. For other load types it is the actual value, for example, when low_threshold is set to 5Gbps increases will be by this value in bandwidth.
- incr_med: subsequent goal seek load increase if kpi_1 increase is between low_ and med_threshold.
- incr_high: subsequent goal seek load increase if kpi_1 increase is between med_ and high_threshold.
- low_threshold: threshold for load increase for incr_low.
- med_threshold: threshold for load increase for incr_med.
- high_threshold: stops goal seeking if load increase of kpi_1 is below this value.
- variance_sample_size: number of result interval samples to determine load stability, default is 3. Can go higher, lower is not recommended.
- max_variance: maximum allowed variance within variance_sample_size to allow load increase. Default is 0.03 (3%) between minimum and maximum values in variance_sample_size.
- capacity_adj: multiplies load values start_load, incr_low, _med and _high. If set to 'auto' multiple will be based on client core count in test when set to simusers(/second) and to port count for other load types. Can be set to a number also.
- ramp_low: percentage of load at ramp_seek complete phase to set goal seek incr_low value. Only used with ramp_seek and goal_seek. Default 60(%).
- ramp_med: percentage of load at ramp_seek complete phase to set goal seek incr_med value. Only used with ramp_seek and goal_seek. Default 40(%).
- ramp_high: percentage of load at ramp_seek complete phase to set goal seek incr_high value. Only used with ramp_seek and goal_seek. Default 20(%).



