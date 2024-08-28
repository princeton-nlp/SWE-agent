"""
1. Download scrambled run logs from Google Drive.
2. Disentangle logs into files by instance_id.
3. Upload clean logs to run-logs sub-folder in Google Drive.
"""

import os
import re
from typing import List
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from googleapiclient.errors import HttpError
import io
from tqdm import tqdm

# Get folder ID from environment variables
TRAJECTORY_FOLDER_ID = "1rA9cqZnANg-GDfp4-sWZze-xzMWEOuF2"
run_logs_folder_name = "run-logs"

def get_absolute_path(relative_path: str) -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, relative_path)

def get_run_log_path(filename: str = "") -> str:
    return get_absolute_path(os.path.join(run_logs_folder_name, filename))

def get_download_run_log_path(filename: str = "") -> str:
    return get_absolute_path(os.path.join(f"{run_logs_folder_name}-downloaded", filename))

def get_google_drive_href(id: str) -> str:
    return f"https://drive.google.com/drive/u/0/folders/{id} (https://drive.google.com/drive/u/2/folders/{id})";

def authenticate_google_drive() -> build:
    print("Authenticating...")
    key_path = get_absolute_path('service-account-key.json')
    creds = Credentials.from_service_account_file(key_path, scopes=['https://www.googleapis.com/auth/drive'])
    return build('drive', 'v3', credentials=creds)

def list_shared_folders(service: build) -> List[str]:
    """
    List all shared folders that the service account has access to.
    """
    try:
        query = "mimeType = 'application/vnd.google-apps.folder' and sharedWithMe"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        items = results.get('files', [])
        
        if not items:
            print("No shared folders found.")
            return []

        print("Shared folders:")
        for item in items:
            print(f"Folder ID: {item['id']}, Name: {item['name']}")
        
        return [item['id'] for item in items]
    
    except HttpError as error:
        print(f"An error occurred while listing shared folders: {str(error)}")
        return []
def download_run_logs(service: build, folder_id: str) -> List[str]:
    try:
        # Try to access the folder
        service.files().get(fileId=folder_id).execute()
    except HttpError as error:
        print(f"⚠ Failed to access folder with ID at {get_google_drive_href(folder_id)} ⚠.")
        print("Listing all shared folders the service has access to:\n\n")
        list_shared_folders(service)
        raise

    # If we successfully accessed the folder, proceed with the original logic
    query = f"'{folder_id}' in parents and name contains 'run-' and name contains '.log'"
    results = service.files().list(q=query, fields="files(id, name, size)").execute()
    items = results.get('files', [])
    print(f"Files matching query in folder {folder_id}: {len(items)}")

    if not items:
        print(f"Could not find any log files in folder {folder_id}.")
        return []

    downloaded_files = []
    skipped = 0
    for item in tqdm(items, desc="Processing files", unit="file"):
        file_id = item['id']
        file_name = item['name']
        file_size = int(item['size'])
        file_path = get_download_run_log_path(file_name)

        # Check if file already exists and has the correct size
        if os.path.exists(file_path) and os.path.getsize(file_path) == file_size:
            skipped += 1
            downloaded_files.append(file_path)
            continue

        try:
            request = service.files().get_media(fileId=file_id)
            file = io.BytesIO()
            downloader = MediaIoBaseDownload(file, request)
            done = False
            while done is False:
                _, done = downloader.next_chunk()
            
            file_content = file.getvalue()
            
            # Save the file locally
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            downloaded_files.append(file_path)
        except HttpError as error:
            print(f"Error downloading file {file_name}: {str(error)}")

    print(f"Finished downloading ({skipped} skipped).")
    
    return downloaded_files

def create_folders() -> str:
    os.makedirs(get_run_log_path(), exist_ok=True)
    os.makedirs(get_download_run_log_path(), exist_ok=True)

def disentangle_log_file(file_path: str, output_dir: str) -> List[str]:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex pattern to match instance blocks
    pattern = r'INFO ▶️  Beginning task[\s\S]*?INFO Trajectory saved to .*?/([^/]+?)\.traj'
    
    instances = list(re.finditer(pattern, content, re.MULTILINE))
    
    disentangled_files = []
    for match in instances:
        instance_content = match.group(0)
        instance_id = match.group(1)
        
        # Create a new file for each instance
        output_file = os.path.join(output_dir, f"run-{instance_id}.log")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(instance_content)
        
        disentangled_files.append(output_file)
    
    return disentangled_files

def process_all_logs(input_dir: str, output_dir: str) -> List[str]:
    all_disentangled_files = []
    
    log_files = [f for f in os.listdir(input_dir) if f.startswith("run-") and f.endswith(".log")]
    
    for filename in tqdm(log_files, desc="Processing log files", unit="file"):
        file_path = os.path.join(input_dir, filename)
        disentangled_files = disentangle_log_file(file_path, output_dir)
        all_disentangled_files.extend(disentangled_files)
    
    return all_disentangled_files


def get_or_create_drive_folder(service: build, parent_folder_id: str, name: str) -> str:
    """
    Create a folder inside the specified parent folder.
    If the folder already exists, return its ID.
    """
    query = f"name='{name}' and '{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder'"
    results = service.files().list(q=query, fields="files(id)").execute()
    items = results.get('files', [])

    if items:
        return items[0]['id']
    
    file_metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_folder_id]
    }
    file = service.files().create(body=file_metadata, fields='id').execute()
    return file.get('id')

def upload_files_to_drive(service: build, run_logs_folder_id: str, file_paths: List[str]) -> None:
    
    total_size = sum(os.path.getsize(file_path) for file_path in file_paths)
    uploaded_size = 0
    deleted = 0
    skipped = 0
    
    uploaded_files_log = get_run_log_path("uploaded_files.log")
    
    with open(uploaded_files_log, 'a+') as log_file:
        log_file.seek(0)
        uploaded_files = set(line.strip() for line in log_file)
    
    # Batch query all files in the given folder
    query = f"'{run_logs_folder_id}' in parents"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    drive_files = {file['name']: file['id'] for file in results.get('files', [])}
    
    # Delete files that exist on drive but not in the local log
    for file_name, file_id in drive_files.items():
        if file_name not in uploaded_files:
            service.files().delete(fileId=file_id).execute()
            deleted += 1
            print(f"Deleted: {file_name}")
    
    with tqdm(total=total_size, desc="Uploading files", unit='B', unit_scale=True, dynamic_ncols=True) as pbar:
        for file_path in file_paths:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            # Update progress bar description with current file name
            pbar.set_description(f"Uploading {file_name}")
            
            if file_name in uploaded_files:
                # Skip if file has been uploaded before
                uploaded_size += file_size
                pbar.update(file_size)
                skipped += 1
                print(f"Skipped: {file_name}")
                continue
            
            file_metadata = {
                'name': file_name,
                'parents': [run_logs_folder_id],
                'mimeType': 'application/vnd.google-apps.document'
            }
            media = MediaFileUpload(file_path, resumable=True, chunksize=1024*1024)
            
            request = service.files().create(body=file_metadata, media_body=media, fields='id')
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
                        print(f"\n\n⚠⚠⚠WARNING⚠⚠⚠\nGDrive API tried to upload more than file size for file {file_name}.\nCancelled.\n\n")
                        break
                    pbar.update(chunk_size)
                elif last_status:
                    # print(f"DDBG1 {last_status.total_size - file_uploaded_size}")
                    pbar.update(last_status.total_size - file_uploaded_size)
                else:
                    # print(f"DDBG2 {file_size}")
                    pbar.update(file_size)
                last_status = status
            print(f"Uploaded: {file_name}")
            
            # Append the uploaded file name to the log
            with open(uploaded_files_log, 'a') as log_file:
                log_file.write(f"{file_name}\n")
    
    print(f"Upload finished ({skipped} skipped, {deleted} existing files deleted and re-uploaded).")

# Example usage:
# creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/drive.file'])
# service = build('drive', 'v3', credentials=creds)
# run_logs_folder_id = 'your_folder_id_here'
# file_paths = ['path/to/log1.txt', 'path/to/log2.txt']
# upload_files_to_drive(service, run_logs_folder_id, file_paths)

def main():
    service = authenticate_google_drive()
    create_folders()  # Ensure the run-logs folder exists before downloading
    downloaded_files = download_run_logs(service, TRAJECTORY_FOLDER_ID)
    print(f"Downloaded {len(downloaded_files)} run log files.")
    
    if downloaded_files:
        run_logs_dir = get_absolute_path(run_logs_folder_name)
        print(f"Using 'run-logs' folder at: {run_logs_dir}")
        
        disentangled_files = process_all_logs(get_download_run_log_path(), run_logs_dir)
        print(f"Disentangled {len(disentangled_files)} instance log files.")

        run_logs_folder_id = get_or_create_drive_folder(service, TRAJECTORY_FOLDER_ID, run_logs_folder_name)
        upload_files_to_drive(service, run_logs_folder_id, disentangled_files)
        print(f"Uploaded {len(disentangled_files)} disentangled log files to Google Drive at {get_google_drive_href(run_logs_folder_id)}")
    else:
        print("No files were downloaded. Please check the folder ID and service account permissions.")

if __name__ == "__main__":
    main()
