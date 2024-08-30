from __future__ import annotations

import io
import os

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from tqdm import tqdm

# Get folder ID from environment variables
DEFAULT_TRAJECTORY_FOLDER_ID = "1rA9cqZnANg-GDfp4-sWZze-xzMWEOuF2"

run_logs_folder_name = "run-logs"
google_drive_service: any = None


def get_absolute_path(relative_path: str) -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, relative_path)


def get_run_log_path(filename: str = "") -> str:
    return get_absolute_path(os.path.join(run_logs_folder_name, filename))

def get_run_log_name(instance_id: str) -> str:
    return f"run-{instance_id}.log"

def get_instance_run_log_path(instance_id: str) -> str:
    return get_absolute_path(os.path.join(run_logs_folder_name, get_run_log_name(instance_id)))


def get_raw_run_log_path(filename: str = "") -> str:
    return get_absolute_path(os.path.join(f"{run_logs_folder_name}-raw", filename))


def get_google_drive_href(id: str) -> str:
    return f"https://drive.google.com/drive/u/0/folders/{id} (https://drive.google.com/drive/u/2/folders/{id})"


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

def get_or_create_drive_folder(parent_folder_id: str, name: str) -> str:
    """
    Create a folder inside the specified parent folder.
    If the folder already exists, return its ID.
    """
    service = get_google_drive_service()
    query = f"name='{name}' and '{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder'"
    results = service.files().list(q=query, fields="files(id)").execute()
    items = results.get("files", [])

    if items:
        return items[0]["id"]

    file_metadata = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_folder_id]}
    file = service.files().create(body=file_metadata, fields="id").execute()
    return file.get("id")


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

def download_instance_log(instance_id: str):
    run_logs_folder_id = get_or_create_drive_folder(DEFAULT_TRAJECTORY_FOLDER_ID, run_logs_folder_name)
    return download_run_logs(run_logs_folder_id, f"name='{get_run_log_name(instance_id)}'", get_run_log_path)


def download_run_logs(folder_id: str, query: str, get_local_file_path: callable[[str], str]) -> list[str]:
    service = get_google_drive_service()
    try:
        # Make sure we can access the folder first.
        service.files().get(fileId=folder_id).execute()
    except HttpError as error:
        print(f"⚠ Failed to access folder with ID at {get_google_drive_href(folder_id)} ⚠.")
        print("Listing all shared folders the service has access to:\n\n")
        list_shared_folders()
        raise error

    # Find matching files.
    query = f"'{folder_id}' in parents and {query}"
    # print(f"DDBG querying: '{query}'")
    results = service.files().list(q=query, fields="files(id, name, size)").execute()
    items = results.get("files", [])
    print(f"{len(items)} Files matching query in folder {folder_id}")

    if not items:
        print(f"Could not find any log files in folder {folder_id}.")
        return []

    downloaded_files = []
    skipped = 0
    for item in tqdm(items, desc="Processing files", unit="file"):
        file_name = item["name"]
        file_path = get_local_file_path(file_name)
        file_id = item["id"]
        file_size = int(item["size"])
        skipped += download_drive_file(file_path, file_id, file_size)
        downloaded_files.append(file_path)

    print(f"Finished downloading ({skipped} skipped).")

    return list(set(downloaded_files))
