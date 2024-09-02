from __future__ import annotations

import io
import os
from typing import Callable

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from tqdm import tqdm

# We are focused on this one run (for now).
DRIVE_REPRO_FOLDER_20240826 = "1ZkyW9o_KlHws3jpgBlgrDBrV31KOisYk"

# 
DRIVE_DEFAULT_USER_INDEX = "2"

RUN_LOGS_FOLDER_NAME = "run-logs"

google_drive_service: any = None


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


def get_google_drive_folder_href(id: str) -> str:
    return f"https://drive.google.com/drive/u/{DRIVE_DEFAULT_USER_INDEX}/folders/{id}"


def list_shared_folders() -> list[str]:
    """
    List all shared folders that the service account has access to.
    """
    service = get_google_drive_service()
    try:
        query = "mimeType = 'application/vnd.google-apps.folder' and sharedWithMe"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        items = results.get("files", [])

        if not items:
            print("No shared folders found.")
            return []

        print("Shared folders:")
        for item in items:
            print(f"Folder ID: {item['id']}, Name: {item['name']}")

        return [item["id"] for item in items]

    except HttpError as error:
        print(f"An error occurred while listing shared folders: {str(error)}")
        return []

# ###########################################################################
# Google Drive Stuff
# ###########################################################################

def get_google_drive_service() -> any:
    global google_drive_service
    if google_drive_service:
        return google_drive_service
    print("Authenticating Google Drive Service...")
    key_path = get_absolute_path("service-account-key.json")
    creds = Credentials.from_service_account_file(key_path, scopes=["https://www.googleapis.com/auth/drive"])
    google_drive_service = build("drive", "v3", credentials=creds)
    return google_drive_service

# Keep folder ids cached, to save ourselves unnecessary look-ups.
drive_file_ids_by_path: dict = {}

def get_drive_file(parent_folder_id: str, relative_path: list[str]) -> str | None:
    global drive_file_ids_by_path

    # Construct the cache key
    cache_key = f"{parent_folder_id}/{'/'.join(relative_path)}"

    # Check if the result is already in the cache
    if cache_key in drive_file_ids_by_path:
        return drive_file_ids_by_path[cache_key]

    service = get_google_drive_service()
    current_parent_id = parent_folder_id
    current_path = parent_folder_id

    # Traverse through all but the last item in relative_path (these should be folders)
    for folder_name in relative_path[:-1]:
        current_path += f"/{folder_name}"
        
        # Check if this intermediate path is in the cache
        if current_path in drive_file_ids_by_path:
            current_parent_id = drive_file_ids_by_path[current_path]
            continue

        query = f"name='{folder_name}' and '{current_parent_id}' in parents and mimeType='application/vnd.google-apps.folder'"
        results = service.files().list(q=query, fields="files(id)").execute()
        items = results.get("files", [])

        if items:
            current_parent_id = items[0]["id"]
            # Cache the intermediate result
            drive_file_ids_by_path[current_path] = current_parent_id
        else:
            # If any folder in the path is not found, return None and don't cache
            return None

    # Look up the final item (file or folder)
    final_name = relative_path[-1]
    query = f"name='{final_name}' and '{current_parent_id}' in parents"
    
    results = service.files().list(q=query, fields="files(id)").execute()
    items = results.get("files", [])

    if items:
        file_id = items[0]["id"]
        # Cache the final result
        drive_file_ids_by_path[cache_key] = file_id
        return file_id
    else:
        return None

def get_or_create_drive_folder(parent_folder_id: str, relative_path: list[str]) -> str:
    service = get_google_drive_service()
    current_parent_id = parent_folder_id

    current_path = []
    for folder_name in relative_path:
        current_path.append(folder_name)

        # Try to get the folder using the get_drive_file function
        folder_id = get_drive_file(current_parent_id, [folder_name])
        
        if folder_id is not None:
            current_parent_id = folder_id
        else:
            # If the folder doesn't exist, create it
            file_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [current_parent_id]
            }
            file = service.files().create(body=file_metadata, fields="id").execute()
            new_folder_id = file.get("id")

            # Update the cache with the newly created folder
            global drive_file_ids_by_path
            cache_key = f"{parent_folder_id}/{'/'.join(current_path)}"
            drive_file_ids_by_path[cache_key] = new_folder_id
            current_parent_id = new_folder_id

    return current_parent_id


def download_drive_file(dest_path: str, drive_file_id: str, drive_file_size: int = None):
    skipped: bool = False
    service = get_google_drive_service()

    # Check if file already exists and has the correct size
    if drive_file_size and os.path.exists(dest_path) and os.path.getsize(dest_path) == drive_file_size:
        skipped = True
    else:
        try:
            request = service.files().get_media(fileId=drive_file_id)
            file = io.BytesIO()
            downloader = MediaIoBaseDownload(file, request)
            done = False
            while done is False:
                _, done = downloader.next_chunk()

            file_content = file.getvalue()

            # Save the file locally
            with open(dest_path, "wb") as f:
                f.write(file_content)
        except HttpError as error:
            msg = f"Error downloading file {os.path.basename(dest_path)}: {str(error)}"
            raise Exception(msg)
    return skipped

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

# def get_instance_eval_report_href(instance_id: str):
#     id = get_drive_file(DRIVE_REPRO_FOLDER_20240826, ["evaluation_logs", instance_id, "report.json"])
#     return get_google_drive_file_href(id)


def drive_download_files(folder_id: str, query: str, get_local_file_path: callable[[str], str]) -> list[str]:
    service = get_google_drive_service()
    try:
        # Make sure we can access the folder first.
        service.files().get(fileId=folder_id).execute()
    except HttpError as error:
        print(f"⚠ Failed to access folder with ID at {get_google_drive_folder_href(folder_id)} ⚠.")
        print("Listing all shared folders the service has access to:\n\n")
        list_shared_folders()
        raise error

    # Find matching files.
    query = f"'{folder_id}' in parents and {query}"
    # print(f"DDBG querying: '{query}'")
    results = service.files().list(q=query, fields="files(id, name, size)").execute()
    items = results.get("files", [])
    print(f"Downloading {len(items)} files matching query '{query}'")

    if not items:
        print(f"Could not find any log files in folder {folder_id}.")
        return []

    downloaded_files = []
    skipped = 0
    for item in tqdm(items, desc="Processing files", unit="file"):
        file_name = item["name"]
        local_file_path = get_local_file_path(file_name)
        file_id = item["id"]
        file_size = int(item["size"])
        skipped += download_drive_file(local_file_path, file_id, file_size)
        downloaded_files.append(local_file_path)

    print(f"Finished downloading ({skipped} skipped).")

    return list(set(downloaded_files))
