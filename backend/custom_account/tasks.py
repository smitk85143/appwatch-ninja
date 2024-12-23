# import os
# import subprocess
# import dropbox
# import logging
# from django.conf import settings
# from django.utils import timezone
# from celery import shared_task

# logger = logging.getLogger(__name__)

# BACKUP_FILE = f"{settings.POSTGRES_DB}_backup_{timezone.now().strftime('%Y-%m-%d')}.sql"

# dbx = dropbox.Dropbox(settings.DROPBOX_ACCESS_TOKEN)

# def backup_postgres():
#     try:

#         dump_command = [
#             'docker', 'exec', '-e', f'PGPASSWORD={settings.POSTGRES_PASSWORD}', 'postgres',
#             'pg_dump', '-U', settings.POSTGRES_USER, '-d', settings.POSTGRES_DB, '-F', 'c', '-f', BACKUP_FILE
#         ]
#         dump_command = [
#             'pg_dump', '-h', settings.POSTGRES_HOST, "-p", settings.POSTGRES_PORT, '-U', settings.POSTGRES_USER, '-d', settings.POSTGRES_DB, '-F', 'c', '-f', BACKUP_FILE
#         ]
#         # copy_command = ['docker', 'cp', f'postgres:{BACKUP_FILE}', f"{BACKUP_FILE}"]
#         # cleanup_command = ['docker', 'exec', 'postgres', 'rm', BACKUP_FILE]
#         subprocess.run(dump_command, check=True, env={"PGPASSWORD": settings.POSTGRES_PASSWORD})
#         # subprocess.run(copy_command, check=True)
#         # subprocess.run(cleanup_command, check=True)
#         logger.info(f"Backup of {settings.POSTGRES_DB} completed successfully: {BACKUP_FILE}")
#     except Exception as e:
#         logger.error(f"Error backing up PostgreSQL: {e}")
#         raise

# def upload_to_dropbox():
#     try:
#         if not os.path.isfile(BACKUP_FILE):
#             raise FileNotFoundError(f"Backup file {BACKUP_FILE} not found.")
        
#         with open(BACKUP_FILE, 'rb') as f:
#             dropbox_path = f"/backups/{os.path.basename(BACKUP_FILE)}"
#             dbx.files_upload(f.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)
#             logger.info(f"Backup uploaded to Dropbox successfully: {dropbox_path}")
#     except Exception as e:
#         logger.error(f"Error uploading to Dropbox: {e}")
#         raise

# def cleanup():
#     try:
#         if os.path.isfile(BACKUP_FILE):
#             os.remove(BACKUP_FILE)
#             logger.info(f"Cleaned up local backup file: {BACKUP_FILE}")
#     except Exception as e:
#         logger.error(f"Error cleaning up local file: {e}")

# @shared_task
# def backup_database():
#     try:
#         backup_postgres()
#         upload_to_dropbox()
#     finally:
#         cleanup()
