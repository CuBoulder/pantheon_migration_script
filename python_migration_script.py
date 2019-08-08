# Python 3 Migration Script
from local_vars import *
import subprocess
import requests
import time
import optparse

parser = optparse.OptionParser()

parser.add_option('-f', '--nofiles',
                  action="store_false", dest="import_site_files",
                  help="Boolean to switch, use this flag to exclude files on site import")

options, args = parser.parse_args()

# Bool, False will skip files from being imported
import_file_bool = options.import_site_files

# Open file where we log sites
f = open("imported_sites.txt", "a+")

# Atlas target Environment
env = ""
# TODO: Get rid of the backups_env var, only used when scp
backups_env = "prod"

# TODO: Agree on prefix
site_prefix = "ucb"

# Number of seconds to wait before checking if site backup is ready
backup_wait = 5

# Instance to export
instance_list = [""]

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
    pantheon_site_name = site_prefix + '-' + site_name.replace("/", "-")
    print(f"Pantheon site name: {pantheon_site_name}")

    # Label will be the site name for now
    # Label must not contain spaces otherwise site crete step will break
    pantheon_label = pantheon_site_name

    # Request site backups
    backup_request = requests.post(f"https://{env}/atlas/sites/{instance}/backup", auth=(identikey, user_password))
    print("Requesting Backup...")
    time.sleep(backup_wait)
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
    if (import_file_bool == False): 
        print('Skipping file imports...')
    else:
        print(f"Exporting files from {env}...")
        print(f"Files Backup: {site_files}")
        subprocess.call(["scp", "-i" "~/.ssh/id_rsa", f"{env}:/nfs/{backups_env}_backups/backups/{site_files}", "./files"])

    print(f"Database Backup: {site_database}")
    subprocess.call(["scp", "-i", "~/.ssh/id_rsa", f"{env}:/nfs/{backups_env}_backups/backups/{site_database}", "./database"])

    

    # Pantheon create new site
    # site:create [--org [ORG]] [--region [REGION]] [--] <site> <label> <upstream_id>
    # TODO Handle: Duplicate site names
    # [error]  The site name jesus-import-site is already taken.
    create_site = subprocess.call(["terminus", "site:create", "--org", f"{org}", f"{pantheon_site_name}", f"{pantheon_label}", f"{upstream_id}"])

    print(f"Uploading database to {pantheon_site_name}")
    # Get mysql credentials for pantheon site
    # TODO: Is there a way to call of this info at once and store in one variable?
    mysql_username = subprocess.getoutput(f"terminus connection:info {pantheon_site_name}.{pantheon_env} --field mysql_username")
    mysql_password = subprocess.getoutput(f"terminus connection:info {pantheon_site_name}.{pantheon_env} --field mysql_password")
    mysql_database = subprocess.getoutput(f"terminus connection:info {pantheon_site_name}.{pantheon_env} --field mysql_database")
    mysql_command = subprocess.getoutput(f"terminus connection:info {pantheon_site_name}.{pantheon_env} --field mysql_command")
    site_id = subprocess.getoutput(f"terminus site:info {pantheon_site_name} --field id")

    # Send DB to Pantheon
    database_sync = subprocess.Popen([f'eval "{mysql_command} < ./database/{site_database}"'], shell=True)
    database_sync.wait()
    print("Database upload complete")

    if (import_file_bool == False):
        print('Skipping file rsync...')
    else:

        print("Rsync'ing files to pantheon")
        # # Unzip files backup on local machine
        unpack_files = subprocess.call(["tar", "-xzf", f"./files/{site_files}", "-C", "./files/"])
    
        # Remove tar file
        remove_tar = subprocess.call(["rm", f"./files/{site_files}"])

        # TODO: Verify $env substitution, handle errors or write script to restart rync
        # Rsync files to pantheon
        file_rsync = subprocess.Popen([f'rsync -rlIpz -e "ssh -p 2222 -o StrictHostKeyChecking=no" --temp-dir=~/tmp --delay-updates ./files/ dev.{site_id}@appserver.dev.{site_id}.drush.in:files'], shell=True)
        file_rsync.wait()
        print("File rsync complete")

    # TODO:
    # settings.php

    # Disable ucb_on_prem_hosting module
    enable_ucb_on_prem = subprocess.Popen([f'terminus drush {pantheon_site_name}.dev pm-disable ucb_on_prem_hosting'], shell=True)
    enable_ucb_on_prem.wait()

    # Enable pantheon_hosting_module
    enable_ucb_on_prem = subprocess.Popen([f'terminus drush {pantheon_site_name}.dev pm-enable pantheon_hosting'], shell=True)
    enable_ucb_on_prem.wait()

    print(f"Deploying {pantheon_site_name} to test environment")
    deploy_test_env = subprocess.Popen([f"terminus env:deploy --updatedb {pantheon_site_name}.test"], shell=True)
    deploy_test_env.wait()

    print(f"Deploying {pantheon_site_name} to prod environment")
    deploy_prod_env = subprocess.Popen([f"terminus env:deploy --updatedb {pantheon_site_name}.prod"], shell=True)
    deploy_prod_env.wait()

    # Enable redis server for site
    enable_redis = subprocess.Popen([f"terminus redis:enable {site_id}"], shell=True)
    enable_redis.wait()

    # Clean up 
    print("Cleaning up for next run...")
    subprocess.call(["rm", "-rf", "./database/"])
    subprocess.call(["rm", "-rf", "./files/"])
    
    # Log instance to file
    print(f"Completed: {instance}")
    f.write(f"{instance}\n")

print("All Sites Processed.")
f.close()
