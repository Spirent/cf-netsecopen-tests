import pathlib
import sys
import random
import string

project_dir = pathlib.Path().absolute().parent
sys.path.append(str(project_dir))

from cf_common.CfClient import *
from cf_runtests.input.cf_config import *
from cf_runtests.input.credentials import *
from cf_common.cf_functions import *
from cf_common.CfCreateTest import *

if (pathlib.Path.cwd() / "dev_settings.py").is_file():
    from cf_runtests.dev_settings import *

input_dir, output_dir, report_dir = verify_directory_structure(
    in_project_dir, input_location, output_location, report_location
)

cf = CfClient(cf_controller_address, username, password, verify_ssl)
cf.connect()
log.info("Connected to controller")

create_tests_base_file = output_dir / create_tests_base_file

# get base test from controller and save to file
cf.get_test(create_tests_base_type, create_tests_base_test_id, create_tests_base_file)

# load base test from file
with open(create_tests_base_file) as infile:
    base = json.load(infile)
# bt = base test class instance
bt = BaseTest(base)

create_test_source_csv = input_dir / create_test_source_csv
with open(create_test_source_csv, "r") as f:
    reader = csv.DictReader(f)
    test_list = list(reader)
# print(f'\ntest_list\n{json.dumps(test_list, indent=4)}')

# create tests to run csv file
reference_to_run_csv_file = input_dir / reference_to_run_csv_file
test_to_run_csv_file = input_dir / test_to_run_csv_file
run_tests = TestsToRun(reference_to_run_csv_file, test_to_run_csv_file)

create_tests_output_list_csv = output_dir / create_tests_output_list_csv
with open(create_tests_output_list_csv, "w") as f:
    created_tests = f"id,type,name"
    f.write(created_tests)

# check CyberFlood version
cf_ver = cf.get_system_version()
print(f"CyberFlood controller version: {cf_ver['version']}")
log.debug(f"\nCyberFlood version response\n{json.dumps(cf_ver, indent=4)}")
log.debug(f"CyberFlood controller version: {cf_ver['version']}")

# set test name suffix to be used if input sheet is not set to "auto"
chars = 3
suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=chars))


for test in test_list:
    if test["include"].lower() in {"y", "yes"}:
        print(f"creating test: {json.dumps(test, indent=4)}")
        # load test template from controller
        test_template = cf.fetch_test_template(
            test["type"], output_dir / "template_last_created.json"
        )
        log.debug(f"\nTemplate response\n{json.dumps(test_template, indent=4)}")
        # instantiate new test
        if test["name_suffix"] == "auto":
            test["name_suffix"] = suffix
        new = CfCreateTest(base, test, test_template, cf_ver["version"])
        new.update_config_changes()
        last_created_test = output_dir / "last_created_test.json"
        new.save_test(last_created_test)

        response = cf.post_test(test["type"], last_created_test)
        log.debug(f"\nPost response\n{json.dumps(response, indent=4)}")
        if "type" in response:
            if response["type"] == "validation":
                print(json.dumps(response, indent=4))
                sys.exit(1)
        run_tests.add_test(response, test["type"])
        test_info = f"\n{response['id']},{test['type']},{response['name']}"
        print(f"test info: {test_info}")
        with open(create_tests_output_list_csv, "a") as f:
            f.write(test_info)
