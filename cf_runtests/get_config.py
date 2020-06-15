import pathlib
import json
import sys
project_dir = pathlib.Path().absolute().parent
sys.path.append(str(project_dir))

from cf_common.CfClient import *
from cf_runtests.input.cf_config import *
from cf_runtests.input.credentials import *
from cf_common.cf_functions import *

if (pathlib.Path.cwd() / "dev_settings.py").is_file():
    from cf_runtests.dev_settings import *

input_dir, output_dir, report_dir = verify_directory_structure(
    in_project_dir, input_location, output_location, report_location
)

cf = CfClient(cf_controller_address, username, password, verify_ssl)
cf.connect()

response = cf.get_test(get_test_type, get_test_id, output_dir / get_test_to_file)
if cf.exception_state:
    print(f"\nSaved to file: {get_test_to_file} \n{json.dumps(response, indent=4)}")
else:
    print(f"Unable to save test id: {get_test_id} with test type: {get_test_type}")
