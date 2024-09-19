import os
from tqdm import tqdm
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
from sweagent.investigations.google_drive import get_google_drive_service, get_drive_file_id
from sweagent.investigations.lock_file import LockFile

class GoogleDriveDownloader:
    def __init__(self):
        self.total_size = 0
        self.processed_size = 0
        self.total_files = 0
        self.processed_files = 0
        self.downloaded_files = 0
        self.skipped_files = 0
        self.failed_files = 0
        self.progress_bar = None
        self.files_to_download = []

    def download_folder_but_slow(
        self, drive_parent_folder_id: str, parent_dest_path: str, folder_name: str
    ) -> bool:
        """
        Returns whether the folder was downloaded (or False if it was downloaded previously).
        This uses a lock file mechanism to track cached downloaded files.
        WARNING: This is slow. Faster (batch) downloads of big files/folders are apparently possible with the gdown library, but require public access.
        """
        dest_path = os.path.join(parent_dest_path, folder_name)
        with LockFile("downloaded", dest_path) as download_lock_file:
            if download_lock_file.had_lock: # Already downloaded. Skip.
                return False

            print("Calculating total files and size...")
            drive_item_id = get_drive_file_id(drive_parent_folder_id, [folder_name])
            with tqdm(
                total=0, unit=" items", bar_format="{desc}{bar:10}", leave=False
            ) as pbar:
                pbar.set_description_str("Scanning files")
                self.calculate_total_size(drive_item_id, True, pbar, dest_path)

            print(f"Files to download: {len(self.files_to_download)}")
            print(f"Total files: {self.total_files}")
            print(f"Total size: {self.total_size / (1024*1024):.2f} MB")

            self.progress_bar = tqdm(
                total=len(self.files_to_download), unit=" files", desc="Overall Progress"
            )

            self.download_files()

            self.progress_bar.close()
            return True

    def calculate_total_size(self, item_id: str, is_folder: bool, pbar, dest_path: str):
        service = get_google_drive_service()
        if is_folder:
            self._calculate_folder_size(item_id, pbar, dest_path)
        else:
            file_metadata = service.files().get(fileId=item_id, fields="size,name").execute()
            file_size = int(file_metadata.get("size", 0))
            file_name = file_metadata.get("name", "Unknown")
            file_path = os.path.join(dest_path, file_name)
            
            self.total_size += file_size
            self.total_files += 1
            
            if not os.path.exists(file_path) or os.path.getsize(file_path) != file_size:
                self.files_to_download.append((item_id, file_path, file_size))
            
            pbar.update(1)

    def _calculate_folder_size(self, folder_id: str, pbar, dest_path: str):
        service = get_google_drive_service()
        query = f"'{folder_id}' in parents"
        results = (
            service.files().list(q=query, fields="files(id, mimeType, size, name)").execute()
        )
        items = results.get("files", [])

        for item in items:
            item_path = os.path.join(dest_path, item["name"])
            if item["mimeType"] == "application/vnd.google-apps.folder":
                if not os.path.exists(item_path):
                    os.makedirs(item_path)
                self._calculate_folder_size(item["id"], pbar, item_path)
            else:
                file_size = int(item.get("size", 0))
                self.total_size += file_size
                self.total_files += 1
                
                if not os.path.exists(item_path) or os.path.getsize(item_path) != file_size:
                    self.files_to_download.append((item["id"], item_path, file_size))
                
                pbar.update(1)

    def download_files(self):
        service = get_google_drive_service()
        for file_id, dest_path, file_size in self.files_to_download:
            try:
                request = service.files().get_media(fileId=file_id)
                with open(dest_path, "wb") as f:
                    downloader = MediaIoBaseDownload(f, request, chunksize=1024 * 1024)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()

                self.downloaded_files += 1
                self.processed_files += 1
                self.processed_size += file_size
                self.progress_bar.update(1)
            except HttpError as error:
                print(f"Error downloading file {dest_path}: {str(error)}")
                self.failed_files += 1
                self.processed_files += 1
                self.progress_bar.update(1)

        print(f"Downloaded: {self.downloaded_files}, Skipped: {self.skipped_files}, Failed: {self.failed_files}")

    def print_summary(self):
        print("\nDownload Summary:")
        print(f"Total files: {self.total_files}")
        print(f"Processed files: {self.processed_files}")
        print(f"Downloaded: {self.downloaded_files}")
        print(f"Skipped: {self.skipped_files}")
        print(f"Failed: {self.failed_files}")
        print(f"Total size: {self.total_size / (1024*1024):.2f} MB")
        print(f"Processed size: {self.processed_size / (1024*1024):.2f} MB")
