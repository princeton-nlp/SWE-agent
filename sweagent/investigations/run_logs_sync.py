from __future__ import annotations

from sweagent.investigations.constants import DRIVE_REPRO_DATA_ROOT_FOLDER_ID, SANITIZED_RUN_LOGS_FOLDER_NAME
from sweagent.investigations.google_drive import get_google_drive_folder_href, get_drive_file_id, drive_download_files, upload_folder
from sweagent.investigations.google_drive_downloader import GoogleDriveDownloader
from sweagent.investigations.local_paths import LocalPaths, get_instance_run_log_name

class RunLogsSync(LocalPaths):
    """
    Synchronize trajectory and eval logs between a given local folder and a given Google Drive folder.
    """
    def __init__(self, run_name: str) -> None:
        # call super ctor
        super().__init__(run_name)

    def download_instance_prediction_run_log(self, instance_id: str):
        run_logs_folder_id = get_drive_file_id(DRIVE_REPRO_DATA_ROOT_FOLDER_ID, [self.run_name, "trajectories", SANITIZED_RUN_LOGS_FOLDER_NAME])
        instance_file_name = get_instance_run_log_name(instance_id)
        return drive_download_files(run_logs_folder_id, f"name='{instance_file_name}'", self.get_prediction_run_log_path)

    def download_instance_prediction_trajectory_json(self, instance_id: str):
        folder_id = get_drive_file_id(DRIVE_REPRO_DATA_ROOT_FOLDER_ID, [self.run_name, "trajectories"])
        instance_file_name = f"{instance_id}.traj"
        return drive_download_files(folder_id, f"name='{instance_file_name}'", self.get_prediction_trajectories_path)

    def get_instance_eval_folder_href(self, instance_id: str):
        folder_id = get_drive_file_id(DRIVE_REPRO_DATA_ROOT_FOLDER_ID, [self.run_name, "evaluation_logs", instance_id])
        return get_google_drive_folder_href(folder_id)

    def download_eval_instance_patch(self, instance_id: str):
        folder_id = get_drive_file_id(DRIVE_REPRO_DATA_ROOT_FOLDER_ID, [self.run_name, "evaluation_logs", instance_id])
        file_name = "patch.diff"
        def local_path_fn(_fname: str) -> str:
            return self.get_local_run_path(f"{instance_id}-patch.diff")
        return drive_download_files(folder_id, f"name='{file_name}'", local_path_fn)
    
    def download_entire_run(self):
        downloader = GoogleDriveDownloader()
        downloader.download_folder_but_slow(DRIVE_REPRO_DATA_ROOT_FOLDER_ID, self.logs_root, self.run_name)
    
    def upload_entire_run(self):
        return upload_folder(DRIVE_REPRO_DATA_ROOT_FOLDER_ID, [self.run_name], self.run_path)

