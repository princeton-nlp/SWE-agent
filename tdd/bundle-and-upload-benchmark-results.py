from sweagent.investigations.local_paths import bundle_local_run_results
from sweagent.investigations.run_logs_sync import RunLogsSync


def main():
    # Bundle local files and folders.
    syncer = bundle_local_run_results(RunLogsSync)

    # Upload.
    syncer.upload_entire_run()


if __name__ == "__main__":
    main()
