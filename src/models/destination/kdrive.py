from datetime import datetime, timedelta
import subprocess
import logging
import json


class kDrive:
    def __init__(self, endpoint_url, folder, user, password):
        self.endpoint_url = endpoint_url
        self.folder = folder
        self.user = str(user)
        self.password = password
        self.config_name = "kDrive"
        self.setup_rclone_config()

    def setup_rclone_config(self):
        # Check if kDrive config already exists
        result = subprocess.run(
            ["rclone", "config", "show"], capture_output=True, text=True
        )
        if self.config_name not in result.stdout:
            logging.info("Creating kDrive config for rclone.")
            # Create kDrive config
            subprocess.run(
                [
                    "rclone",
                    "config",
                    "create",
                    self.config_name,
                    "webdav",
                    "url",
                    f"{self.endpoint_url}/{self.folder}",
                    "vendor",
                    "other",
                    "user",
                    self.user,
                ]
            )
            subprocess.run(
                [
                    "rclone",
                    "config",
                    "password",
                    self.config_name,
                    "pass",
                    self.password,
                ]
            )
            # Verify creation
            result = subprocess.run(
                ["rclone", "config", "show"], capture_output=True, text=True
            )
            if self.config_name in result.stdout:
                logging.info("kDrive config created for rclone.")
            else:
                logging.error("ERROR: kDrive config not created, please check!")
                raise Exception("kDrive config creation failed")

    def list(self):
        try:
            result = subprocess.run(
                [
                    "rclone",
                    "lsjson",
                    "--recursive",
                    f"{self.config_name}:",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            logging.error(
                f"ERROR: Failed to list files in {remote_path} on kDrive: {str(e)}"
            )
            raise

    def upload_file(self, file_path, remote_path):
        try:
            # Ensure the remote path includes the full path and filename
            result = subprocess.run(
                ["rclone", "copyto", file_path, f"{self.config_name}:{remote_path}"],
                check=True,
            )
            logging.info(f"File uploaded to kDrive successfully as {remote_path}.")
            return f"Uploaded {file_path} to kDrive as {remote_path}"
        except subprocess.CalledProcessError as e:
            logging.error(f"ERROR: Failed to upload {file_path} to kDrive: {str(e)}")
            raise

    def delete_file(self, remote_path):
        try:
            # Delete file from kDrive
            result = subprocess.run(
                ["rclone", "deletefile", f"{self.config_name}:{remote_path}"],
                check=True,
            )
            logging.info(f"File deleted from kDrive: {remote_path}")
        except subprocess.CalledProcessError as e:
            logging.error(
                f"ERROR: Failed to delete {remote_path} from kDrive: {str(e)}"
            )
            raise

    def cleanup(self, retention):
        """
        Delete folder older than retention period
        """
        current_time = datetime.utcnow()
        retention_threshold = current_time - timedelta(days=retention)

        for file in self.list():
            if file["MimeType"] != "inode/directory":
                obj_datetime = file["ModTime"]

                # Convert obj_datetime to native datetime for comparison
                obj_datetime_native = datetime.fromisoformat(
                    obj_datetime.replace("Z", "+00:00")
                ).replace(tzinfo=None)

                if obj_datetime_native < retention_threshold:
                    self.delete_file(file["Path"])
