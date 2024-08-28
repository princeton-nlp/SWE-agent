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

def get_absolute_path(relative_path: str) -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, relative_path)

def get_run_log_path(filename: str = "") -> str:
    return get_absolute_path(os.path.join("run-logs", filename))

def get_download_run_log_path(filename: str = "") -> str:
    return get_absolute_path(os.path.join("run-logs-downloaded", filename))

def get_google_drive_href(id: str) -> str:
    return f"https://drive.google.com/drive/u/0/folders/{id} (https://drive.google.com/drive/u/2/folders/{id})";

def authenticate_google_drive() -> build:
    """
    Authenticate with Google Drive API using a service account JSON key file.
    
    The key file should be named 'service-account-key.json' and located in the same directory as this script.
    """
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
    skipped = 0
    
    with tqdm(total=total_size, desc="Uploading files", unit='B', unit_scale=True, dynamic_ncols=True) as pbar:
        for file_path in file_paths:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            # Update progress bar description with current file name
            pbar.set_description(f"Uploading {file_name}")
            
            # Check if file already exists in the run-logs folder
            query = f"name='{file_name}' and '{run_logs_folder_id}' in parents"
            results = service.files().list(q=query, fields="files(id, size)").execute()
            existing_files = results.get('files', [])
            
            if existing_files and int(existing_files[0]['size']) == file_size:
                skipped += 1
                uploaded_size += file_size
                pbar.update(file_size)
                continue
            
            file_metadata = {
                'name': file_name,
                'parents': [run_logs_folder_id]
            }
            media = MediaFileUpload(file_path, resumable=True, chunksize=1024*1024)
            
            request = service.files().create(body=file_metadata, media_body=media, fields='id')
            response = None
            
            file_uploaded_size = 0
            while response is None:
                status, response = request.next_chunk()
                if status:
                    chunk_size = status.resumable_progress - file_uploaded_size
                    file_uploaded_size = status.resumable_progress
                    uploaded_size += chunk_size
                    pbar.update(chunk_size)
    
    print(f"Upload finished ({skipped} skipped).")

def main():
    service = authenticate_google_drive()
    create_folders()  # Ensure the run-logs folder exists before downloading
    downloaded_files = download_run_logs(service, TRAJECTORY_FOLDER_ID)
    print(f"Downloaded {len(downloaded_files)} run log files.")
    
    if downloaded_files:
        run_logs_dir = get_absolute_path("run-logs")
        print(f"Using 'run-logs' folder at: {run_logs_dir}")
        
        disentangled_files = process_all_logs(get_download_run_log_path(), run_logs_dir)
        print(f"Disentangled {len(disentangled_files)} instance log files.")

        run_logs_folder_id = get_or_create_drive_folder(service, TRAJECTORY_FOLDER_ID)
        upload_files_to_drive(service, run_logs_folder_id, disentangled_files)
        print(f"Uploaded {len(disentangled_files)} disentangled log files to Google Drive at {get_google_drive_href(run_logs_folder_id)}")
    else:
        print("No files were downloaded. Please check the folder ID and service account permissions.")

if __name__ == "__main__":
    main()
