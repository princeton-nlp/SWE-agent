from __future__ import annotations

from sweagent.investigations.constants import DRIVE_REPRO_FOLDER_20240826, RUN_LOGS_FOLDER_NAME
from sweagent.investigations.google_drive import get_google_drive_folder_href, get_drive_file, drive_download_files
from sweagent.investigations.paths import get_local_run_log_path, get_local_run_path, get_local_trajectory_json_path, get_run_log_name

def download_instance_prediction_log(folder_id: str):
    run_logs_folder_id = get_drive_file(DRIVE_REPRO_FOLDER_20240826, ["trajectories", RUN_LOGS_FOLDER_NAME])
    instance_file_name = get_run_log_name(folder_id)
    return drive_download_files(run_logs_folder_id, f"name='{instance_file_name}'", get_local_run_log_path)

def download_instance_prediction_trajectory_json(instance_id: str):
    folder_id = get_drive_file(DRIVE_REPRO_FOLDER_20240826, ["trajectories"])
    instance_file_name = f"{instance_id}.traj"
    return drive_download_files(folder_id, f"name='{instance_file_name}'", get_local_trajectory_json_path)

def get_instance_eval_folder_href(instance_id: str):
    folder_id = get_drive_file(DRIVE_REPRO_FOLDER_20240826, ["evaluation_logs", instance_id])
    return get_google_drive_folder_href(folder_id)

def download_instance_eval_test_output(instance_id: str):
    folder_id = get_drive_file(DRIVE_REPRO_FOLDER_20240826, ["evaluation_logs", instance_id])
    file_name = "test_output.txt"
    def local_path_fn(_fname: str) -> str:
        return get_local_run_path(f"{instance_id}-eval-output.log")
    return drive_download_files(folder_id, f"name='{file_name}'", local_path_fn)

def download_instance_patch(instance_id: str):
    folder_id = get_drive_file(DRIVE_REPRO_FOLDER_20240826, ["evaluation_logs", instance_id])
    file_name = "patch.diff"
    def local_path_fn(_fname: str) -> str:
        return get_local_run_path(f"{instance_id}-patch.diff")
    return drive_download_files(folder_id, f"name='{file_name}'", local_path_fn)

