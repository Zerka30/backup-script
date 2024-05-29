from gitignore_parser import parse_gitignore
from models.destination.s3 import S3Bucket
from models.destination.kdrive import kDrive
from models.backup import Backup

import logging
import yaml

# Configure logging
logging.basicConfig(
    filename="backup.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Load configuration from the config.yml file
with open("./config.yml", "r") as config_file:
    config = yaml.load(config_file, Loader=yaml.FullLoader)

# Read the .bakignore file and parse the ignore rules
bakignore_rules = parse_gitignore(".bakignore")


if __name__ == "__main__":
    # Define the backup destination
    config_destination = config["backup"]["destination"]
    backup_destinations = []

    for destination in config_destination:
        if config_destination[destination]["enable"]:
            match destination:
                case "s3":
                    backup_destinations.append(
                        S3Bucket(
                            config_destination[destination]["endpoint"],
                            config_destination[destination]["bucket"],
                            config_destination[destination]["key"]["access"],
                            config_destination[destination]["key"]["secret"],
                        )
                    )
                case "kdrive":
                    backup_destinations.append(
                        kDrive(
                            config_destination[destination]["endpoint"],
                            config_destination[destination]["folder"],
                            config_destination[destination]["user"],
                            config_destination[destination]["password"],
                        )
                    )

    if len(backup_destinations) <= 0:
        logging.error("No backup destination enabled")
        exit(1)

    # Define the backup notification
    config_notification = config["notify"]
    notifications = []
    for notif in notifications:
        if config_notification[notif]["enable"]:
            pass

    # Backup
    backup = Backup(config, backup_destinations, bakignore_rules)
    backup.backup()
