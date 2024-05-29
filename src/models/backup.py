from datetime import datetime
from models.destination.s3 import S3Bucket

import os
import subprocess
import logging
import tarfile
import tempfile


class Backup:
    def __init__(self, config, destination, bakignore_rules):
        self.config = config
        self.destination = destination
        self.summary = []
        self.to_ignore = bakignore_rules

    def backup(self):
        if len(self.config["backup"]["databases"]) > 0:
            self.database_backup()

        if len(self.config["backup"]["folders"]) > 0:
            self.folders_backup()

        logging.info("Backup completed")

        self.cleanup()

    def database_backup(self):
        """
        Backup the databases
        """
        backup_dir = "/tmp/databases"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        for database in self.config["backup"]["databases"]:
            name = (
                database["name"] or database["host"]
            )  # In case user doesn't provide a name, use the host
            host = database["host"]
            port = database["port"]
            user = database["user"]
            password = database["password"]

            logging.info(f"Backing up databases from {name}")
            self.summary.append(f"Backing up databases from {name}")

            for db in database["database"]:
                db_name = db["name"]
                backup_file = f"{backup_dir}/{db_name}-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.sql"
                try:
                    command = f"mariadb-dump -h {host} -P {port} -u {user} --password={password} {db_name} > {backup_file}"
                    subprocess.run(command, shell=True, check=True)
                except subprocess.CalledProcessError as e:
                    logging.error(f"Backup of {db_name} failed: {e}")
                    self.summary.append(f"Backup of {db_name} failed: {e}")
                    continue

            if self.config["backup"]["archive"]:
                with tempfile.NamedTemporaryFile(
                    "wb", suffix=".tar.gz", delete=False
                ) as archive_file:
                    archive_name = archive_file.name
                    with tarfile.open(fileobj=archive_file, mode="w:gz") as tar:
                        for backup_file in os.listdir(backup_dir):
                            file_path = os.path.join(backup_dir, backup_file)
                            tar.add(file_path, arcname=os.path.basename(file_path))
                            os.remove(file_path)
                    archive_file.close()

                for destination in self.destination:
                    msg = destination.upload_file(
                        archive_name,
                        f"database/{name}-{datetime.now().strftime('%Y-%m-%d_%H-%M')}.tar.gz",
                    )
                    self.summary.append(msg)

            else:
                logging.error("Not supported yet")

    def folders_backup(self):
        """
        Backup the folders
        """
        for folder in self.config["backup"]["folders"]:
            name = folder["name"]
            path = folder["path"]

            if self.config["backup"]["archive"]:
                with tempfile.NamedTemporaryFile(
                    "wb", suffix=".tar.gz", delete=False
                ) as archive_file:
                    archive_name = archive_file.name
                    with tarfile.open(fileobj=archive_file, mode="w:gz") as tar:
                        for root, dirs, files in os.walk(path):
                            for file in files:
                                source_file = os.path.join(root, file)
                                rel_source_file = os.path.relpath(
                                    source_file, os.path.abspath(path)
                                )
                                if not self.to_ignore(rel_source_file):
                                    tar.add(source_file, arcname=rel_source_file)
                    archive_file.close()

                for destination in self.destination:
                    msg = destination.upload_file(
                        archive_name,
                        f"data/{name}/{name}-{datetime.now().strftime('%Y-%m-%d_%H-%M')}.tar.gz",
                    )
                    self.summary.append(msg)

    def notify(self):
        """
        Notify the backup summary
        """
        pass

    def cleanup(self):
        """
        Cleanup the backup
        """
        retention = self.config["backup"]["retention"]
        for destination in self.destination:
            destination.cleanup(retention)
