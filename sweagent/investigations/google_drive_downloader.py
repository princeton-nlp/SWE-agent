import os
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
from tqdm import tqdm

from sweagent.investigations.google_drive import get_google_drive_service
from sweagent.investigations.lock_file import LockFile

class GoogleDriveDownloader:
    def __init__(self):
        self.service = get_google_drive_service()
        self.total_size = 0
        self.processed_size = 0
        self.total_files = 0
        self.processed_files = 0
        self.downloaded_files = 0
        self.skipped_files = 0
        self.failed_files = 0
        self.progress_bar = None

    def download(self, dest_path: str, drive_item_id: str, is_folder: bool = False):
        with LockFile("downloaded", dest_path) as bundle_lock:
            if bundle_lock.had_lock:
                # We downloaded this before. Skip.
                return

            print("Calculating total files and size...")
            with tqdm(total=0, unit=' items', bar_format='{desc}{bar:10}', leave=False) as pbar:
                pbar.set_description_str("Scanning files")
                self.calculate_total_size(drive_item_id, is_folder, pbar)

            print(f"Total files to process: {self.total_files}")
            print(f"Total size: {self.total_size / (1024*1024):.2f} MB")

            self.progress_bar = tqdm(total=self.total_files, unit=' files', desc="Overall Progress")
            
            if is_folder:
                result = self.download_folder(dest_path, drive_item_id)
            else:
                result = self.download_file(dest_path, drive_item_id)
            
            self.progress_bar.close()
            return result

    def calculate_total_size(self, item_id: str, is_folder: bool, pbar):
        if is_folder:
            self._calculate_folder_size(item_id, pbar)
        else:
            file_metadata = self.service.files().get(fileId=item_id, fields='size').execute()
            self.total_size += int(file_metadata.get('size', 0))
            self.total_files += 1
            pbar.update(1)

    def _calculate_folder_size(self, folder_id: str, pbar):
        query = f"'{folder_id}' in parents"
        results = self.service.files().list(q=query, fields="files(id, mimeType, size)").execute()
        items = results.get('files', [])

        for item in items:
            if item['mimeType'] == 'application/vnd.google-apps.folder':
                self._calculate_folder_size(item['id'], pbar)
            else:
                self.total_size += int(item.get('size', 0))
                self.total_files += 1
                pbar.update(1)

    def download_file(self, dest_path: str, drive_file_id: str):
        try:
            file_metadata = self.service.files().get(fileId=drive_file_id, fields='size,name').execute()
            file_size = int(file_metadata.get('size', 0))
            file_name = file_metadata.get('name', 'Unknown')

            if os.path.exists(dest_path) and os.path.getsize(dest_path) == file_size:
                # print(f"File {file_name} already exists with correct size. Skipping.")
                self.skipped_files += 1
                self.processed_size += file_size
                self.processed_files += 1
                self.progress_bar.update(1)
                return True

            request = self.service.files().get_media(fileId=drive_file_id)
            
            with open(dest_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request, chunksize=1024*1024)
                done = False
                while not done:
                    status, done = downloader.next_chunk()

            # print(f"File {file_name} downloaded successfully.")
            self.downloaded_files += 1
            self.processed_files += 1
            self.processed_size += file_size
            self.progress_bar.update(1)
            return False
        except HttpError as error:
            print(f"Error downloading file {file_name}: {str(error)}")
            self.failed_files += 1
            self.processed_files += 1
            self.progress_bar.update(1)
            return False

    def download_folder(self, dest_path: str, folder_id: str):
        if not os.path.exists(dest_path):
            os.makedirs(dest_path)

        query = f"'{folder_id}' in parents"
        results = self.service.files().list(q=query, fields="files(id, name, mimeType)").execute()
        items = results.get('files', [])

        for item in items:
            item_path = os.path.join(dest_path, item['name'])
            if item['mimeType'] == 'application/vnd.google-apps.folder':
                self.download_folder(item_path, item['id'])
            else:
                self.download_file(item_path, item['id'])

        # print(f"Folder {os.path.basename(dest_path)} and its contents processed successfully.")
        return True

    def print_summary(self):
        print("\nDownload Summary:")
        print(f"Total files: {self.total_files}")
        print(f"Processed files: {self.processed_files}")
        print(f"Downloaded: {self.downloaded_files}")
        print(f"Skipped: {self.skipped_files}")
        print(f"Failed: {self.failed_files}")
        print(f"Total size: {self.total_size / (1024*1024):.2f} MB")
        print(f"Processed size: {self.processed_size / (1024*1024):.2f} MB")

# Usage example:
# downloader = GoogleDriveDownloader()
# downloader.download_item("/path/to/destination", "drive_item_id", is_folder=False)
# downloader.download_item("/path/to/destination", "drive_folder_id", is_folder=True)
# downloader.print_summary()