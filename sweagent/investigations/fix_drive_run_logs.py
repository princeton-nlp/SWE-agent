"""
1. Download scrambled run logs from Google Drive.
2. Disentangle logs into files by instance_id.
3. Upload clean logs to run-logs sub-folder in Google Drive.
"""

from __future__ import annotations

import os
import re

from googleapiclient.http import MediaFileUpload
from tqdm import tqdm

from sweagent.investigations.run_logs import (
    DEFAULT_TRAJECTORY_FOLDER_ID,
    drive_download_files,
    get_google_drive_folder_href,
    get_google_drive_service,
    get_instance_run_log_path,
    get_or_create_drive_folder,
    get_raw_run_log_path,
    get_local_trajectory_json_path,
    RUN_LOGS_FOLDER_NAME,
)


def create_folders() -> str:
    os.makedirs(get_local_trajectory_json_path(), exist_ok=True)
    os.makedirs(get_raw_run_log_path(), exist_ok=True)


def disentangle_log_file(file_path: str) -> list[str]:
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    # Regex pattern to match instance blocks
    pattern = r"INFO ▶️  Beginning task[\s\S]*?INFO Trajectory saved to .*?/([^/]+?)\.traj"

    instances = list(re.finditer(pattern, content, re.MULTILINE))

    disentangled_files = []
    for match in instances:
        instance_content = match.group(0)
        instance_id = match.group(1)

        # Create a new file for each instance
        output_file = get_instance_run_log_path(instance_id)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(instance_content)

        disentangled_files.append(output_file)

    return disentangled_files


def process_all_logs(input_dir: str) -> list[str]:
    all_disentangled_files = []

    log_files = [f for f in os.listdir(input_dir) if f.startswith("run-") and f.endswith(".log")]

    for filename in tqdm(log_files, desc="Processing log files", unit="file"):
        file_path = os.path.join(input_dir, filename)
        disentangled_files = disentangle_log_file(file_path)
        all_disentangled_files.extend(disentangled_files)

    return all_disentangled_files


def get_upload_file_log_path():
    return get_local_trajectory_json_path("uploaded_files.log")


def read_existing_files(run_logs_folder_id: str):
    service = get_google_drive_service()
    query = f"'{run_logs_folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id, name, size)").execute()
    return {file["name"]: file for file in results.get("files", [])}


# def write_existing_file(file_name: str):
#     # Append the uploaded file name to the log
#     with open(get_upload_file_log_path(), 'a') as log_file:
#         log_file.write(f"{file_name}\n")


def upload_files_to_drive(run_logs_folder_id: str, file_paths: list[str]) -> None:
    total_size = sum(os.path.getsize(file_path) for file_path in file_paths)
    skipped = 0

    uploaded_files = read_existing_files(run_logs_folder_id)
    service = get_google_drive_service()

    with tqdm(total=total_size, desc="Uploading files", unit="B", unit_scale=True, dynamic_ncols=True) as pbar:
        for file_path in file_paths:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)

            # Update progress bar description with current file name
            pbar.set_description(f"Uploading {file_name}")

            if file_name in uploaded_files and uploaded_files[file_name]["size"] == file_size:
                # Skip if file has been uploaded before
                pbar.update(file_size)
                skipped += 1
                print(f"Skipped: {file_name}")
                continue

            file_metadata = {
                "name": file_name,
                "parents": [run_logs_folder_id],
                # Note: Uncomment the mimeType line to upload the files as Google Docs.
                # Warning: When doing that, make sure that `resumable` still works as expected, since then
                # upload file size and target file size will be different from one another.
                # 'mimeType': 'application/vnd.google-apps.document'
            }
            media = MediaFileUpload(file_path, resumable=True, chunksize=1024 * 1024)

            request = service.files().create(body=file_metadata, media_body=media, fields="id")
            response = None

            file_uploaded_size = 0
            last_status = None
            while response is None:
                # The status object is defined here: https://github.com/googleapis/google-api-python-client/blob/411c1b802f21def293a84adb16d8d4ad7478643b/googleapiclient/http.py#L232
                status, response = request.next_chunk()
                if status:
                    chunk_size = status.resumable_progress - file_uploaded_size
                    file_uploaded_size = status.resumable_progress
                    # print(f"Uploaded {file_name}: {chunk_size} ({file_uploaded_size}/{status.total_size})")
                    if file_uploaded_size > status.total_size:
                        # Note: Saw a weird bug where the upload would sometimes exceed the total file size and then it erroring with a 400.
                        # Not sure why.
                        print(
                            f"\n\n⚠⚠⚠WARNING⚠⚠⚠\nGDrive API tried to upload more than file size for file {file_name}.\nCancelled.\n\n"
                        )
                        break
                    pbar.update(chunk_size)
                elif last_status:
                    # print(f"DDBG1 {last_status.total_size - file_uploaded_size}")
                    pbar.update(last_status.total_size - file_uploaded_size)
                else:
                    # print(f"DDBG2 {file_size}")
                    pbar.update(file_size)
                last_status = status
            # print(f"Uploaded: {file_name}")
            # write_existing_file(file_name)

    pbar.set_description(f"Upload finished ({skipped} skipped).")


def main():
    create_folders()  # Ensure the run-logs folder exists before downloading
    drive_download_query = "name contains 'run-' and name contains '.log'"
    raw_files = drive_download_files(DEFAULT_TRAJECTORY_FOLDER_ID, drive_download_query, get_raw_run_log_path)
    print(f"Found and downloaded {len(raw_files)} raw run log files.")

    if raw_files:
        disentangled_files = process_all_logs(get_raw_run_log_path())
        print(f"Disentangled {len(disentangled_files)} instance log files.")

        run_logs_folder_id = get_or_create_drive_folder(DEFAULT_TRAJECTORY_FOLDER_ID, RUN_LOGS_FOLDER_NAME)
        upload_files_to_drive(run_logs_folder_id, disentangled_files)
        print(
            f"Uploaded {len(disentangled_files)} disentangled log files to Google Drive at {get_google_drive_folder_href(run_logs_folder_id)}"
        )
    else:
        print("No files were downloaded. Please check the folder ID and service account permissions.")


if __name__ == "__main__":
    main()
