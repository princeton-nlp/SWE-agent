import sys
import os
from datetime import date

from sweagent.investigations.constants import DRIVE_REPRO_FOLDER
from sweagent.investigations.paths import strip_extension
from sweagent.investigations.google_drive import upload_folder, upload_file


run_id = "command_line_test" # this really needs to be changed
user = os.getlogin()
model = "claude-3.5-sonnet" # assuming we'll keep this constant for now

def main():
    if len(sys.argv) != 2:
        print("Usage: python gather-results.py <result_json_path>")
        sys.exit(1)

    result_json_path = os.path.abspath(sys.argv[1])

    result_basename = os.path.basename(result_json_path)
    result_dirname = os.path.dirname(result_json_path)

    stripped_basename = strip_extension(result_basename, f".{run_id}.json")
    trajectories_path = f"{result_dirname}/trajectories/{user}/{stripped_basename}"
    eval_logs_path = f"{result_dirname}logs/run_evaluation/{run_id}/{stripped_basename}"

    drive_folder = f"{user}-{model}-{date.today().strftime('%Y%m%d')}"

    upload_file(DRIVE_REPRO_FOLDER, [drive_folder], result_json_path)

    upload_folder(DRIVE_REPRO_FOLDER, [drive_folder, "trajectories"], trajectories_path)
    upload_folder(DRIVE_REPRO_FOLDER, [drive_folder, "evaluation_logs"], eval_logs_path)


if __name__ == "__main__":
    main()
