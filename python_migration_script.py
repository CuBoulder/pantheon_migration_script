# Python 3 Migration Script
from local_vars import *
import subprocess
import requests
import time

# Open file where we log sites
f = open("imported_sites.txt", "a+")

# Atlas target Environment
env = "osr-dev-util01.int.colorado.edu"
# TODO: Get rid of the backups_env var, only used when scp
backups_env = "dev"
# Pantheon Target Environment
pantheon_env = 'dev'

# Instance to export
instance_list = ["5cd5e902e1fa27ae427accc5"]

# Backup Timer
backup_wait = 5

for instance in instance_list:
    
    print("Express Python Site Migration Script")

    # Remove existing database and file directories
    subprocess.call(["rm", "-rf", "./database/"])
    subprocess.call(["rm", "-rf", "./files/"])

    # Create empty database and file directories
    subprocess.call(["mkdir", "database"])
    subprocess.call(["mkdir", "files"])

    # Get the path of the site we are importing
    site_response = requests.get(f"https://{env}/atlas/sites/{instance}")
    payload_json = site_response.json()
    site_name = payload_json["path"]

    # Parse url, replace forward slashes with dashes
    # The site name can only contain a-z, A-Z, 0-9, and dashes ('-'), cannot begin or end with a dash, and must be fewer than 52 characters
    pantheon_site_name = site_name.replace("/", "-")
    print(f"Pantheon site name: {pantheon_site_name}")

    # Label will be the site name for now
    # Label must not contain spaces otherwise site crete step will break
    pantheon_label = pantheon_site_name

    # Request site backups
    backup_request = requests.post(f"https://{env}/atlas/sites/{instance}/backup", auth=(identikey, user_password))
    print("Requesting Backup...")
    site_backup_state = ''

    # Proceed with cloning of database and files after backup is complete
    while (site_backup_state != "complete"):
        backup_params = {'sort': '-_updated', 'max_results': '1', 'where': '{"site":"'+instance+'"}'}
        site_backup_request = requests.get(f"https://{env}/atlas/backup", params = backup_params)
        site_backup_json = site_backup_request.json()
        site_backup_state = site_backup_json['_items'][0]['state']
        print(f"Backup Status: {site_backup_state}")
        time.sleep(backup_wait)

    print("Backup is ready for export!")

    site_files = site_backup_json["_items"][0]["files"]
    site_database = site_backup_json["_items"][0]["database"]

    # User needs to have SSH key added to server in order for scp to work
    print(f"Exporting files from {env}...")

    subprocess.call(["scp", "-i", "~/.ssh/id_rsa", f"{env}:/nfs/{backups_env}_backups/backups/{site_database}", "./database"])
    print(f"Database Backup: {site_database}")

    subprocess.call(["scp", "-i" "~/.ssh/id_rsa" f"{env}:/nfs/{backups_env}_backups/backups/{site_files}", "./files"])
    print(f"Files Backup: {site_files}")

    # Pantheon create new site
    # site:create [--org [ORG]] [--region [REGION]] [--] <site> <label> <upstream_id>
    # TODO Handle: Duplicate site names
    # [error]  The site name jesus-import-site is already taken.
    create_site = subprocess.call(["terminus", "site:create", "--org", f"{org}", f"{pantheon_site_name}", f"{pantheon_label}", f"{upstream_id}"])

    print(f"Uploading database to {pantheon_site_name}")
    # Get mysql credentials for pantheon site
    # TODO: Is there a way to call of this info at once and store in one variable?
    mysql_username = subprocess.call(["terminus", "connection:info", f"{pantheon_site_name}.{pantheon_env}", "--field", "mysql_username"])
    mysql_password = subprocess.call(["terminus", "connection:info", f"{pantheon_site_name}.{pantheon_env}", "--field", "mysql_password"])
    mysql_database = subprocess.call(["terminus", "connection:info", f"{pantheon_site_name}.{pantheon_env}", "--field", "mysql_database"])
    mysql_command = subprocess.call(["terminus", "connection:info", f"{pantheon_site_name}.{pantheon_env}", "--field", "mysql_command"])
    site_id = subprocess.call([f"terminus", "site:info", f"{pantheon_site_name}", "--field", "id"])

    # Send DB to Pantheon
    database_sync = subprocess.call(["eval", f"'{mysql_command} < ./database/{site_database}'"])
    print("Database upload complete")

    print("Rsync'ing files to pantheon")
    # # Unzip files backup on local machine
    unpack_files = subprocess.call(["tar", "-xzf", f"./files/{site_files}", "-C", "./files/"])
    
    # Remove tar file
    remove_tar = subprocess.call(["rm", f"./files/{site_files}"])

    # TODO: Verify $env substitution, handle errors or write script to restart rync
    # Rsync files to pantheon
    file_rsync = subprocess.call(['rsync', '-rlIpz', '-e', '"ssh -p 2222 -o StrictHostKeyChecking=no"', '--temp-dir=~/tmp', '--delay-updates', './files/', f'{pantheon_env}.{site_id}@appserver.{pantheon_env}.{site_id}.drush.in:files'])
    print("File rsync complete")

    # Clean up 
    print("Cleaning up for next run...")
    subprocess.call(["rm", "-rf", "./database/"])
    subprocess.call(["rm", "-rf", "./files/"])
    
    # Log instance to file
    print(f"Completed: {instance}")
    f.write(f"{instance}\n")

print("All Sites Processed.")
f.close()
