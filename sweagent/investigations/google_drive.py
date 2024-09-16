from __future__ import annotations

import io
import os
from typing import Callable

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from tqdm import tqdm

from sweagent.investigations.constants import DRIVE_DEFAULT_USER_INDEX

google_drive_service: any = None


def get_google_drive_folder_href(id: str) -> str:
    return f"https://drive.google.com/drive/u/{DRIVE_DEFAULT_USER_INDEX}/folders/{id}"


def get_absolute_path(relative_path: str) -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, relative_path)


def get_google_drive_service() -> any:
    global google_drive_service
    if google_drive_service:
        return google_drive_service
    print("Authenticating Google Drive Service...")
    key_path = get_absolute_path("service-account-key.json")
    creds = Credentials.from_service_account_file(
        key_path, scopes=["https://www.googleapis.com/auth/drive"]
    )
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
                "parents": [current_parent_id],
            }
            file = service.files().create(body=file_metadata, fields="id").execute()
            new_folder_id = file.get("id")

            # Update the cache with the newly created folder
            global drive_file_ids_by_path
            cache_key = f"{parent_folder_id}/{'/'.join(current_path)}"
            drive_file_ids_by_path[cache_key] = new_folder_id
            current_parent_id = new_folder_id

    return current_parent_id


def download_drive_file(
    dest_path: str, drive_file_id: str, drive_file_size: int = None
):
    skipped: bool = False
    service = get_google_drive_service()

    # Check if file already exists and has the correct size
    if (
        drive_file_size
        and os.path.exists(dest_path)
        and os.path.getsize(dest_path) == drive_file_size
    ):
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


def drive_download_files(
    folder_id: str, query: str, get_local_file_path: Callable[[str], str]
) -> list[str]:
    service = get_google_drive_service()
    try:
        # Make sure we can access the folder first.
        service.files().get(fileId=folder_id).execute()
    except Exception as error:
        print(
            f"⚠ Failed to access folder with ID at {get_google_drive_folder_href(folder_id)} ⚠ - {str(error)}"
        )
        print("Listing all shared folders the service has access to:\n\n")
        list_shared_folders()
        # raise error
        return []

    # Find matching files.
    query = f"'{folder_id}' in parents and {query}"
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


def upload_file(
    dest_drive_folder_id: str, relative_dest_path: list[str], src_file_path: str
):
    service = get_google_drive_service()

    # Get or create the destination folder
    dest_folder_id = get_or_create_drive_folder(
        dest_drive_folder_id, relative_dest_path
    )

    file_metadata = {
        "name": os.path.basename(src_file_path),
        "parents": [dest_folder_id],
    }

    media = MediaFileUpload(src_file_path, resumable=True)

    try:
        file = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        return file.get("id")
    except HttpError as error:
        msg = f"Error uploading file {src_file_path}: {str(error)}"
        raise Exception(msg)


def get_relative_path_segments(root_path: str, abs_folder: str) -> list[str]:
    res = os.path.relpath(abs_folder, root_path).split("/")
    if ".." in res:
        raise Exception(f"Given {abs_folder} is not in {root_path}. relpath = {res}")
    if len(res) >= 1 and res[0] == ".":
        return res[1:]
    return res


def upload_folder(
    dest_drive_folder_id: str, relative_dest_path: list[str], src_root: str
):
    uploaded_files = []

    # Get or create the destination folder
    actual_dest_folder_id = get_or_create_drive_folder(
        dest_drive_folder_id, relative_dest_path
    )

    print(
        f"Uploading directory '{src_root}' to: {get_google_drive_folder_href(actual_dest_folder_id)}"
    )
    for abs_folder_path, _, files in os.walk(src_root):
        for file in tqdm(files, desc="Uploading files", unit="file"):
            src_file_path = os.path.join(abs_folder_path, file)
            relative_segments = get_relative_path_segments(src_root, abs_folder_path)
            # print(f"Uploading {src_file_path} to {relative_segments}...")
            file_id = upload_file(actual_dest_folder_id, relative_segments, src_file_path)
            if file_id:
                uploaded_files.append((file, file_id))

    return uploaded_files
