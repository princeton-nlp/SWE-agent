import os

from sweagent.investigations.constants import RUN_LOGS_FOLDER_NAME

def strip_extension(path: str, ext: str) -> str:
    if path.endswith(ext):
        return path[: -len(ext)]
    return path

def get_absolute_path(relative_path: str) -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, relative_path)

def get_local_run_log_path(filename: str = "") -> str:
    return get_absolute_path(os.path.join(RUN_LOGS_FOLDER_NAME, filename))

def get_local_trajectory_json_path(filename: str = "") -> str:
    return get_absolute_path(os.path.join(RUN_LOGS_FOLDER_NAME, filename + ".json"))

def get_local_run_path(filename: str = "") -> str:
    return get_absolute_path(os.path.join(RUN_LOGS_FOLDER_NAME, filename))

def get_run_log_name(instance_id: str) -> str:
    return f"run-{instance_id}.log"

def get_instance_run_log_path(instance_id: str) -> str:
    return get_absolute_path(os.path.join(RUN_LOGS_FOLDER_NAME, get_run_log_name(instance_id)))


def get_raw_run_log_path(filename: str = "") -> str:
    return get_absolute_path(os.path.join(f"{RUN_LOGS_FOLDER_NAME}-raw", filename))
