from google.cloud import storage
from datetime import datetime, timedelta
import os
from logging import  getLogger
log = getLogger('mobile_service_log')



def get_files(path, skipDays=60):
    '''
    Optimized function to generate a list of files in the given path that are older than
    a specified number of days. The function walks through directories, 
    checks file modification dates against a skip timestamp, and appends older files to a list.
    '''
    log.info(f"Scanning for files older than {skipDays} days in {path}")
    old_files = []
    skipTimestamp = (datetime.now() - timedelta(days=skipDays)).timestamp()

    try:
        for root, _, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    if os.path.getmtime(file_path) < skipTimestamp:
                        old_files.append(file_path)
                        log.debug(f"Old file found: {file_path}")
                except Exception as e:
                    log.error(f"Error processing file {file_path}: {e}", exc_info=True)

        log.info(f"Found {len(old_files)} old files in {path}")
    except Exception as e:
        log.error(f"Error in get_files: {e}", exc_info=True)

    return old_files
    

def move_files_to_GCS(file_paths, bucket_name, target_dir="", test_env=False):
    '''
    Moves files from the specified list to Google Cloud Storage.
    This function handles the connection to GCS, determines the blob name,
    and uploads the file. It optionally deletes the local file if it's successfully
    uploaded and the target directory is not for testing.
    '''
    log.info(f"Moving files to GCS bucket: {bucket_name}")
    try:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = f"{os.path.expanduser('~')}/service-account-file.json"
        client = storage.Client()
        bucket = client.get_bucket(bucket_name)

        for file_path in file_paths:
            try:
                # Efficient blob name generation
                blob_name = file_path.replace(target_dir, "", 1)  # Ensure only the first instance is replaced
                if test_env:
                    blob_name = blob_name.replace("youtility4_media", "youtility2_test")

                blob = bucket.blob(blob_name)
                blob.upload_from_filename(file_path)

                if blob.exists() and not test_env:
                    os.remove(file_path)
                    log.debug(f"File {file_path} moved to GCS and deleted locally")  # Consider log level

            except Exception as e:
                log.error(f"Error moving file {file_path}: {e}", exc_info=True)
    except Exception as e:
        log.error(f"Error in move_files_to_GCS: {e}", exc_info=True)
        

def del_empty_dir(path):
    '''
    Deletes empty directories within the given path, 
    except those ending with "/transaction/".
    '''
    log.info(f"Deleting empty directories in {path}")
    try:
        for root, dirs, files in os.walk(path, topdown=False):
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                if os.path.isdir(dir_path) and not os.listdir(dir_path) and not dir_path.endswith("/transaction/"):
                    os.rmdir(dir_path)
                    log.info(f"Deleted empty directory: {dir_path}")

        return 0
    except Exception as e:
        log.error(f"Error in del_empty_dir: {e}", exc_info=True)
        return -1