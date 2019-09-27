import pathlib


def verify_directory_structure(bool_project_dir, input_dir, output_dir, report_dir):
    # parent.parent assumes this function is in a sub directory of the main project
    # project_root_dir = pathlib.Path(__file__).parent.parent
    project_dir = pathlib.Path.cwd()
    if bool_project_dir:
        input_dir = project_dir / input_dir
        output_dir = project_dir / output_dir
        report_dir = project_dir / report_dir
        input_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        report_dir.mkdir(parents=True, exist_ok=True)
    else:
        input_dir = pathlib.Path(input_dir)
        output_dir = pathlib.Path(output_dir)
        report_dir = pathlib.Path(report_dir)
    if not input_dir.is_dir():
        print(f"input_dir does not exist: {input_dir}")
    if not output_dir.is_dir():
        print(f"output_dir does not exist: {output_dir}")
    if not report_dir.is_dir():
        print(f"report_dir does not exist: {report_dir}")
    return input_dir, output_dir, report_dir


def html_report(df_table, sub_report_tables, html_report_file, filter_columns):
    html = ""
    for sub_table in sub_report_tables:
        df_table.reset_df_filter()
        df_table.filter_rows_containing(sub_table)
        df_table.filter_columns(filter_columns)
        # check if there are results in a table before adding it to the html file
        if not len(df_table.df_filter.index) == 0:
            if sub_table is None:
                table_filter = f"<h3>ALL TESTS - including above tests</h3>"
            else:
                table_filter = f"<h3>{sub_table}</h3>"
            html = html + table_filter + df_table.html_table(df_table.style_a())
    with open(html_report_file, "w") as f:
        f.write(html)


def csv_report(df_table, csv_report_file):
    df_table.reset_df_filter()
    df_table.df_filter.to_csv(csv_report_file, index=False)


# def dut_refresh()
#     # A test run has ended at this point, either successfully or not.
#     # Perform DUT refresh and/or file transfers, if required.
#     dut_refresh_settings = current_test.dut_refresh
#     retrieve_files_settings = current_test.retrieve_files
#     if dut_refresh_settings["required"] or retrieve_files_settings["required"]:
#         from ssh_access import dut_refresh, file_transfer
#         time.sleep(4)
#         print()
#
#         if retrieve_files_settings["required"]:
#             # if file transfer is required for this test, run the function.
#             if not file_transfer(retrieve_files_settings["ip_address"], retrieve_files_settings["username"],
#                                  retrieve_files_settings["password"], retrieve_files_settings["remote_path"],
#                                  retrieve_files_settings["local_path"]):
#                 log.error("File transfer failed to perform.")
#
#         if dut_refresh_settings["required"]:
#             # if dut_refresh is required for this test, run the function.
#             if not dut_refresh(dut_refresh_settings["ip_address"], dut_refresh_settings["username"],
#                                dut_refresh_settings["password"],
#                                dut_refresh_settings["commands_to_execute"],
#                                dut_refresh_settings["optional_wait_time"]):
#                 log.error("DUT refresh required but failed to perform.")
