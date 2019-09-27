import numpy as np
import pandas as pd
import pathlib
import sys

project_dir = pathlib.Path().absolute().parent
sys.path.append(str(project_dir))

from cf_runtests.input.cf_config import *
from cf_common.cf_functions import *
from cf_common.CfRunTest import *

if (pathlib.Path.cwd() / "dev_settings.py").is_file():
    from cf_runtests.dev_settings import *

input_dir, output_dir, report_dir = verify_directory_structure(
    in_project_dir, input_location, output_location, report_location
)

if html_report_csv is None:
    csv_files = report_dir.glob("*Detailed.csv")
    latest_csv_file = max(csv_files, key=lambda p: p.stat().st_mtime)
    print(latest_csv_file)

# v2
table = Report(latest_csv_file, col_order)
file_name = latest_csv_file.stem
file_path = latest_csv_file.parent
if file_name.endswith("_Detailed"):
    file_name = file_name[: -len("_Detailed")]
# create summary csv report with all columns
csv_name = file_name + "_all"
csv_report_file = pathlib.Path(file_path / csv_name).with_suffix(".csv")
print(csv_report_file)
csv_report(table, csv_report_file)

# create multiple html reports
for k, v in html_additional_reports.items():
    new_name = file_name + "_" + k
    report_file = pathlib.Path(file_path / new_name).with_suffix(".html")
    print(report_file)
    print(v)
    html_report(table, report_tables, report_file, v)
