from __future__ import annotations

import logging
import subprocess

from git import Repo

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clone_repository(instance_id: str, local_dir: str, repo_url: str):
    try:
        logger.info(f"Cloning repository for instance {instance_id} into {local_dir}")
        Repo.clone_from(repo_url, local_dir)
    except Exception as e:
        logger.error(f"Failed to clone repository for instance {instance_id}: {e}")
        raise  # Re-raise to notify caller about the failure


def create_and_save_patch(local_dir: str, patch_output_file: str):
    try:
        logger.info(f"Creating patch for the repository in {local_dir}")
        # Navigate to the repository directory and create the patch
        subprocess.run(f"cd {local_dir} && git diff > {patch_output_file}", shell=True, check=True)
        logger.info(f"Patch saved at {patch_output_file}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error creating patch for {local_dir}: {e}")
        raise  # Optionally re-raise the error after logging it


def apply_patch(local_dir: str, patch_file: str):
    try:
        logger.info(f"Applying patch {patch_file} to the repository in {local_dir}")
        # Apply the patch to the repository
        subprocess.run(f"cd {local_dir} && git apply {patch_file}", shell=True, check=True)
        logger.info(f"Patch {patch_file} successfully applied.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error applying patch {patch_file} to {local_dir}: {e}")
        raise  # Optionally re-raise the error after logging it


def send_files_to_remote(instance_id: str, local_dir: str, remote_server: str, remote_dir: str):
    try:
        logger.info(f"Sending files back to the remote server for instance {instance_id}")
        # Example command to send files via scp
        subprocess.run(f"scp -r {local_dir} {remote_server}:{remote_dir}", shell=True, check=True)
        logger.info(f"Files successfully sent to {remote_server}:{remote_dir}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error sending files to remote server for instance {instance_id}: {e}")
        raise  # Optionally re-raise the error after logging it


def main():
    instance_id = "123456"
    local_dir = "/path/to/local/repo"
    repo_url = "https://github.com/user/repo.git"
    patch_output_file = "/path/to/patch.diff"
    patch_file = "/path/to/patch.diff"
    remote_server = "user@remote.server.com"
    remote_dir = "/path/to/remote/dir"

    try:
        # Step 1: Clone the repository
        clone_repository(instance_id, local_dir, repo_url)

        # Step 2: Create a patch
        create_and_save_patch(local_dir, patch_output_file)

        # Step 3: Apply the patch
        apply_patch(local_dir, patch_file)

        # Step 4: Send files back to the remote server
        send_files_to_remote(instance_id, local_dir, remote_server, remote_dir)

    except Exception as e:
        logger.error(f"An error occurred in the process: {e}")


if __name__ == "__main__":
    main()
