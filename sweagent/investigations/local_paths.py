import os
from datetime import date
import re
import shutil
from tqdm import tqdm
from typing import Type, TypeVar
from pathlib import Path

from sweagent.investigations.constants import SANITIZED_RUN_LOGS_FOLDER_NAME
from sweagent.investigations.lock_file import LockFile

PROJECT_ROOT_FOLDER = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
SANTIZIED_LOGS_ROOT_FOLDER = os.path.join(PROJECT_ROOT_FOLDER, "sanitized_logs")
"""
The ROOT_FOLDER of the project, 2 levels up from here. Logs are relative to it.
"""

TRAJECTORIES_FOLDER_NAME = "trajectories"
EVAL_FOLDER_NAME = "evaluation_logs"
COMPELTE_RUN_RESULTS_FILENAME = "COMPELTE_RUN_RESULTS.json"


def get_instance_run_log_name(instance_id: str) -> str:
    return f"run-{instance_id}.log"


def make_run_name(date_str: str) -> str:
    user = os.getlogin()
    model = "claude-3.5-sonnet"  # assuming we'll keep this constant for now
    return f"{user}-{model}-{date_str}"


def recursive_move(src, dst):
    src_path = Path(src)
    dst_path = Path(dst)

    missing_files = []

    if not src_path.exists():
        print(f"Source path does not exist: {src_path}")
        return

    if src_path.is_file():
        try:
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_path), str(dst_path))
            print(f"Moved: {src_path} -> {dst_path}")
        except FileNotFoundError:
            # print(f"File not found: {src_path}")
            missing_files.append(str(src_path))
        except Exception as e:
            print(f"Error moving {src_path}: {e}")

    elif src_path.is_dir():
        for item in src_path.iterdir():
            recursive_move(item, dst_path / item.relative_to(src_path), missing_files)
        src_path.rmdir()
        # print(f"Removed empty directory: {src_path}")


class LocalPaths:
    def __init__(self, run_name: str) -> None:
        self.run_name = run_name

    @property
    def logs_root(self) -> str:
        return SANTIZIED_LOGS_ROOT_FOLDER

    @property
    def run_path(self) -> str:
        return os.path.join(self.logs_root, self.run_name)

    def get_run_path(self, relative_path="") -> str:
        folder = self.run_path
        # folder = os.path.realpath(folder)
        return os.path.join(folder, relative_path)

    # ###########################################################################
    # Predictions
    # ###########################################################################

    def get_prediction_trajectories_path(self, relative_path: str = "") -> str:
        return self.get_run_path(os.path.join(TRAJECTORIES_FOLDER_NAME, relative_path))

    def get_prediction_run_log_path(self, instance_id: str) -> str:
        return self.get_prediction_trajectories_path(
            get_instance_run_log_name(instance_id)
        )

    def get_trajectory_json_path(self, instance_id: str) -> str:
        return self.get_prediction_trajectories_path(instance_id + ".traj")

    def get_prediction_patch_path(self, instance_id: str) -> str:
        return self.get_prediction_trajectories_path(
            os.path.join("patches", f"{instance_id}.patch")
        )

    def get_summary_json_path(self) -> str:
        return self.get_run_path(COMPELTE_RUN_RESULTS_FILENAME)

    # ###########################################################################
    # Evaluations
    # ###########################################################################

    def get_eval_path(self, relative_path: str = "") -> str:
        return self.get_run_path(os.path.join(EVAL_FOLDER_NAME, relative_path))

    def get_eval_meta_log(self, instance_id: str):
        return self.get_eval_path(os.path.join(instance_id, "run_instance.log"))

    def get_eval_test_output_log(self, instance_id: str):
        return self.get_eval_path(os.path.join(instance_id, "test_output.txt"))

    # ###########################################################################
    # Bundling
    # ###########################################################################

    def bundle_run_results(self, user: str, run_id: str) -> None:
        """
        This function is called after a benchmark run:
        It takes all the different files in the different places and put them in the same folder, indexed
        by a new "run name" (which includes the date).
        Returns the "run name".
        """
        os.makedirs(self.run_path, exist_ok=True)

        with LockFile("bundled", self.run_path, self.run_name) as bundle_lock:
            if bundle_lock.had_lock:
                # We bundled this already. Skip.
                return
            print(
                f"BUNDLING benchmark results into new folder:\n  {self.get_run_path()}"
            )

            src_trajectory_name_suffix = f".{run_id}.json"
            src_summary_jsons = [
                f
                for f in os.listdir(SANTIZIED_LOGS_ROOT_FOLDER)
                if f.endswith(src_trajectory_name_suffix)
            ]
            if len(src_summary_jsons) != 1:
                raise ValueError(
                    f"Expected 1 summary JSON file, found {len(src_summary_jsons)} files matching suffix '{src_trajectory_name_suffix}':"
                    + "\n "
                    + "\n ".join(src_summary_jsons)
                )
            src_summary_json = src_summary_jsons[0]
            src_trajectory_name = src_summary_json.replace(
                src_trajectory_name_suffix, ""
            )
            src_trajectories_path = f"{SANTIZIED_LOGS_ROOT_FOLDER}/trajectories/{user}/{src_trajectory_name}"
            src_eval_logs_path = f"{SANTIZIED_LOGS_ROOT_FOLDER}/logs/run_evaluation/{run_id}/{src_trajectory_name}"

            dst_summary_json = self.get_summary_json_path()
            dst_trajectories_path = self.get_prediction_trajectories_path()
            dst_eval_logs_path = self.get_eval_path()

            # Get moving:
            recursive_move(src_trajectories_path, dst_trajectories_path)
            recursive_move(src_eval_logs_path, dst_eval_logs_path)
            recursive_move(src_summary_json, dst_summary_json)

            bundle_lock.write_lock("downloaded")  # Also write downloaded.lock

            print("Done.")

    # ###################################
    # Run log sanitization
    # ###################################

    def disentangle_raw_run_log_file(self, raw_run_log_path: str) -> list[str]:
        with open(raw_run_log_path, encoding="utf-8") as f:
            content = f.read()

        # Regex pattern to match instance blocks
        pattern = (
            r"INFO ▶️  Beginning task[\s\S]*?INFO Trajectory saved to .*?/([^/]+?)\.traj"
        )

        instances = list(re.finditer(pattern, content, re.MULTILINE))

        disentangled_files = []
        for match in instances:
            instance_content = match.group(0)
            instance_id = match.group(1)

            # Create a new file for each instance
            output_file = self.get_prediction_run_log_path(instance_id)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(instance_content)

            disentangled_files.append(output_file)

        return disentangled_files

    def disentangle_prediction_run_logs(self) -> None:
        with LockFile("logs_processed", self.run_path) as lock_file:
            if lock_file.had_lock: # Already processed. Skip.
                return

            all_disentangled_files = []
            trajectories_path = self.get_prediction_trajectories_path()

            # Clean up.
            raw_run_log_files = [
                f
                for f in os.listdir(trajectories_path)
                if f.startswith("run-") and f.endswith(".log")
            ]
            for filename in tqdm(
                raw_run_log_files, desc="Processing log files", unit="file"
            ):
                run_log_path = os.path.join(trajectories_path, filename)
                disentangled_files = self.disentangle_raw_run_log_file(run_log_path)
                all_disentangled_files.extend(disentangled_files)

            print(f"Disentangled {len(disentangled_files)} instance log files.")


LocalPathsT = TypeVar("LocalPathsT", bound="LocalPaths")


def bundle_local_run_results(PathsClass: Type[LocalPathsT] = LocalPaths) -> LocalPathsT:
    run_name = make_run_name(date.today().strftime("%Y%m%d"))
    user = os.getlogin()
    run_id = "command_line_test"  # this really needs to be changed

    local_paths = PathsClass(run_name)
    local_paths.bundle_run_results(user, run_id)
    return local_paths
