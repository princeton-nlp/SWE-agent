import sys
import os
from datetime import date

from sweagent.investigations.constants import DRIVE_REPRO_FOLDER
from sweagent.investigations.paths import strip_extension
from sweagent.investigations.google_drive import upload_directory, upload_file


run_id = "command_line_test" # this really needs to be changed
user = os.getlogin()
model = "claude-3.5-sonnet" # assuming we'll keep this constant for now

def main():
    if len(sys.argv) != 2:
        print("Usage: python gather-results.py <result_json_path>")
        sys.exit(1)

    result_json_path = sys.argv[1]

    basename = os.path.basename(result_json_path)
    stripped_basename = strip_extension(basename, f".{run_id}.json")
    traj_directory = f"trajectories/{user}/{stripped_basename}"
    eval_log_directory = f"logs/run_evaluation/{run_id}/{stripped_basename}"

    drive_folder = f"{user}-{model}-{date.today().strftime('%Y%m%d')}"

    upload_file(DRIVE_REPRO_FOLDER, [drive_folder], result_json_path)

    upload_directory(DRIVE_REPRO_FOLDER, [drive_folder, "trajectories"], traj_directory)
    upload_directory(DRIVE_REPRO_FOLDER, [drive_folder, "evaluation_logs"], eval_log_directory)


if __name__ == "__main__":
    main()
