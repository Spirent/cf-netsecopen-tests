Script requires python 3.7.

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
Linux: export PYTHONPATH=/path/to/spectre-core:$PYTHONPATH
Windows: set PYTHONPATH=%PYTHONPATH%;C:\path\to\spectre-core