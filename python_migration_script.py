# Python 3 Migration Script
from local_vars import *
import subprocess
import requests
import time
import optparse
import logging
import os

from helpers import pantheon_secrets

logging.basicConfig(filename='app.log', filemode='a',
                    format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.INFO)

parser = optparse.OptionParser()

parser.add_option('-n', '--nofiles',
                  action="store_false", dest="import_site_files",
                  help="Boolean to switch, use this flag to exclude files on site import")

parser.add_option('-r', '--redis',
                  action="store_true", dest="enable_redis",
                  help="Boolean to switch, use this flag to enable redis on sites to import")

parser.add_option('-d', '--debug',
                  action="store_true", dest="debug",
                  help="Boolean to switch, use this to deploy a site to dev only and skip the rest")

options, args = parser.parse_args()

# Bool, False will skip files from being imported
import_file_bool = options.import_site_files
enable_redis_bool = options.enable_redis
deploy_until_dev = options.debug

# Open file where we log sites
f = open("imported_sites.txt", "a+")

# Atlas target Environment
env = "osr-prod-util01.int.colorado.edu"
# TODO: Get rid of the backups_env var, only used when scp
backups_env = "prod"

# TODO: Agree on prefix
site_prefix = "migration-test"

# Number of seconds to wait before checking if site backup is ready
backup_wait = 5

# Make an array with instances
with open('instance_list.txt') as my_file:
    instance_list = my_file.read().splitlines()

for instance_data in instance_list:

    instance_data_array = instance_data.split(',')

    instance = instance_data_array[0]
    instance_subdomain = instance_data_array[1]

    logging.info("Starting Migration on " + str(instance))

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
    site_sid = payload_json["sid"]

    # Parse url, replace forward slashes with dashes
    # The site name can only contain a-z, A-Z, 0-9, and dashes ('-'), cannot begin or end with a dash, and must be fewer than 52 characters
    # pantheon_site_name = site_prefix + '-' + site_name.replace("/", "-")
    pantheon_site_name = "cu" + "-" + site_sid
    print(f"Pantheon site name: {pantheon_site_name}")

    # Label will be the site name for now
    # Label must not contain spaces otherwise site crete step will break
    pantheon_label = pantheon_site_name

    # Request site backups
    backup_request = requests.post(
        f"https://{env}/atlas/sites/{instance}/backup", auth=(identikey, user_password))
    print("Requesting Backup...")
    time.sleep(backup_wait)
    site_backup_state = ''

    # Proceed with cloning of database and files after backup is complete
    while (site_backup_state != "complete"):
        backup_params = {'sort': '-_updated',
                         'max_results': '1', 'where': '{"site":"'+instance+'"}'}
        site_backup_request = requests.get(
            f"https://{env}/atlas/backup", params=backup_params)
        site_backup_json = site_backup_request.json()
        site_backup_state = site_backup_json['_items'][0]['state']
        print(f"Backup Status: {site_backup_state}")
        time.sleep(backup_wait)

    print("Backup is ready for export!")

    site_files = site_backup_json["_items"][0]["files"]
    logging.info(str(instance) + "files backup: " + str(site_files))
    site_database = site_backup_json["_items"][0]["database"]
    logging.info(str(instance) + " db backup: " + str(site_database))

    # User needs to have SSH key added to server in order for scp to work
    if (import_file_bool == False):
        print('Skipping file imports...')
    else:
        print(f"Exporting files from {env}...")
        print(f"Files Backup: {site_files}")
        subprocess.call(["scp", "-i" "~/.ssh/id_rsa",
                         f"{env}:/nfs/{backups_env}_backups/backups/{site_files}", "./files"])
        logging.info(f"{instance} files backup successful")

    print(f"Database Backup: {site_database}")
    subprocess.call(["scp", "-i", "~/.ssh/id_rsa",
                     f"{env}:/nfs/{backups_env}_backups/backups/{site_database}", "./database"])
    logging.info(f"{instance} database backup successful")

    # Pantheon create new site
    # TODO Handle: Duplicate site names
    # [error]  The site name jesus-import-site is already taken.
    create_site = subprocess.call(["terminus", "site:create", "--org",
                                   f"{org}", f"{pantheon_site_name}", f"{pantheon_label}", f"{upstream_id}"])
    logging.info(f"{instance} pantheon instance created")

    print(f"Uploading database to {pantheon_site_name}")
    # Get mysql credentials for pantheon site
    # TODO: Is there a way to call of this info at once and store in one variable?
    mysql_username = subprocess.getoutput(
        f"terminus connection:info {pantheon_site_name}.dev --field mysql_username")
    mysql_password = subprocess.getoutput(
        f"terminus connection:info {pantheon_site_name}.dev --field mysql_password")
    mysql_database = subprocess.getoutput(
        f"terminus connection:info {pantheon_site_name}.dev --field mysql_database")
    mysql_command = subprocess.getoutput(
        f"terminus connection:info {pantheon_site_name}.dev --field mysql_command")
    site_id = subprocess.getoutput(
        f"terminus site:info {pantheon_site_name} --field id")

    # Send DB to Pantheon
    database_sync = subprocess.Popen(
        [f'eval "{mysql_command} < ./database/{site_database}"'], shell=True)
    database_sync.wait()
    print("Database upload complete")
    logging.info(f"{instance} db migration successful")

    if (import_file_bool == False):
        print('Skipping file rsync...')
    else:

        print("Rsync'ing files to pantheon")
        # # Unzip files backup on local machine
        unpack_files = subprocess.call(
            ["tar", "-xzf", f"./files/{site_files}", "-C", "./files/"])

        # Remove tar file
        remove_tar = subprocess.call(["rm", f"./files/{site_files}"])

        # Rsync files to pantheon
        file_rsync = subprocess.Popen(
            [f'rsync -rlIpz -e "ssh -p 2222 -o StrictHostKeyChecking=no" --temp-dir=~/tmp --delay-updates ./files/ dev.{site_id}@appserver.dev.{site_id}.drush.in:files'], shell=True)
        file_rsync.wait()
        print("File rsync complete")
        logging.info(f"{instance} files migration successful")

    # Enable sftp mode, needed to add and commit settings.php
    enable_sftp = subprocess.Popen(
        [f"terminus connection:set {pantheon_site_name}.dev sftp"], shell=True)
    enable_sftp.wait()

    # TODO: Generate settings.php from template
    print("Creating settings.php")
    os.system('cp default.settings.php settings.php')

    print(f"Uploading settings.php to {pantheon_site_name}")
    place_settings = subprocess.Popen(
        [f"terminus rsync settings.php {pantheon_site_name}.dev:code/sites/default/"], shell=True)
    place_settings.wait()

    # Workaround for bug:
    clear_dev_cache = subprocess.Popen(
        [f"terminus env:clear-cache {pantheon_site_name}.dev"], shell=True)
    clear_dev_cache.wait()

   # Commit changes, switch to Git Mode
    print("Commit settings.php")
    commit_files = subprocess.Popen(
        [f"terminus env:commit --message='Migration: Adding initial settings.php' {pantheon_site_name}.dev"], shell=True)
    commit_files.wait()

    # Switch back to Git mode
    print("Enable Git on Site")
    enable_git_mode = subprocess.Popen(
        [f"terminus connection:set {pantheon_site_name}.dev git -y"], shell=True)
    enable_git_mode.wait()

    # Disable ucb_on_prem_hosting module
    print("Disabling on_prem hosting")
    enable_ucb_on_prem = subprocess.Popen(
        [f'terminus remote:drush -- {pantheon_site_name}.dev pm-disable ucb_on_prem_hosting -y'], shell=True)
    enable_ucb_on_prem.wait()

    # Enable pantheon_hosting_module
    print("Enabling pantheon_hosting")
    enable_pantheon_hosting = subprocess.Popen(
        [f'terminus remote:drush -- {pantheon_site_name}.dev pm-enable pantheon_hosting -y'], shell=True)
    enable_pantheon_hosting.wait()

    # Enable redis server for site, if passed via flag
    if enable_redis_bool == True:
        print("Enabling redis")
        enable_redis_service = subprocess.Popen(
            [f"terminus redis:enable {site_id}"], shell=True)
        enable_redis_service.wait()

        # Enable redis module
        enable_redis_module = subprocess.Popen(
            [f'terminus remote:drush -- {pantheon_site_name}.dev pm-enable redis -y'], shell=True)
        enable_redis_module.wait()
    
    # Apply DB Updates, if any
    print(f"Running drush updb {pantheon_site_name} on dev")
    run_database_updates = subprocess.Popen(
        [f"terminus drush {pantheon_site_name}.dev -- updb -y"], shell=True)
    run_database_updates.wait()
    logging.info(f"{instance} drush updb")

    # Use terminus rsync to place certs in private directory
    print(f"Placing saml certs for {pantheon_site_name} in dev")
    place_certs_dev = subprocess.Popen(
        [f"terminus rsync ./cert {pantheon_site_name}.dev:files/private -y"], shell=True)
    place_certs_dev.wait()
    logging.info(f"{instance} placed saml certs in dev")

    if deploy_until_dev == False:
        # Deploy to TEST
        print(f"Deploying {pantheon_site_name} to test environment")
        deploy_test_env = subprocess.Popen([f"terminus env:deploy --updatedb {pantheon_site_name}.test"], shell=True)
        deploy_test_env.wait()
        logging.info(f"{instance} deployed to pantheon test")
        # Deploy to PROD
        print(f"Deploying {pantheon_site_name} to prod environment")
        deploy_prod_env = subprocess.Popen([f"terminus env:deploy --updatedb {pantheon_site_name}.live"], shell=True)
        deploy_prod_env.wait()
        logging.info(f"{instance} deployed to pantheon prod")

        # Use regular rsync for the other two, StrictHostKeyChecking=no is needed
        print(f"Placing certs for {pantheon_site_name} in test")
        place_certs_test = subprocess.Popen(
            [f'rsync -rlIpz -e "ssh -p 2222 -o StrictHostKeyChecking=no" --temp-dir=~/tmp --delay-updates ./cert test.{site_id}@appserver.test.{site_id}.drush.in:files/private'], shell=True)
        place_certs_test.wait()
        logging.info(f"{instance} placed saml certs in test")

        print(f"Placing certs for {pantheon_site_name} in live")
        place_certs_live = subprocess.Popen(
            [f'rsync -rlIpz -e "ssh -p 2222 -o StrictHostKeyChecking=no" --temp-dir=~/tmp --delay-updates ./cert live.{site_id}@appserver.live.{site_id}.drush.in:files/private'], shell=True)
        place_certs_live.wait()
        logging.info(f"{instance} placed saml certs in live")

         # Place secrets.json in dev, test and live

        print(f"Creating {pantheon_site_name} in dev")
        place_secrets_dev = subprocess.Popen(
            [f'rsync -rlIpz -e "ssh -p 2222 -o StrictHostKeyChecking=no" --temp-dir=~/tmp --delay-updates secrets.json dev.{site_id}@appserver.dev.{site_id}.drush.in:files/private/'], shell=True)
        place_secrets_dev.wait()
        logging.info(f"{instance} created secrets.json in dev")

        print(f"Creating {pantheon_site_name} in test")
        place_secret_test = subprocess.Popen(
            [f'rsync -rlIpz -e "ssh -p 2222 -o StrictHostKeyChecking=no" --temp-dir=~/tmp --delay-updates secrets.json test.{site_id}@appserver.test.{site_id}.drush.in:files/private/'], shell=True)
        place_secret_test.wait()
        logging.info(f"{instance} created secrets.json in test")

        print(f"Creating {pantheon_site_name} in live")
        place_secrets_live = subprocess.Popen(
            [f'rsync -rlIpz -e "ssh -p 2222 -o StrictHostKeyChecking=no" --temp-dir=~/tmp --delay-updates secrets.json live.{site_id}@appserver.live.{site_id}.drush.in:files/private/'], shell=True)
        place_secrets_live.wait()
        logging.info(f"{instance} created secrets.json in live")

        # Update site plan to basic
        print(f"Upgrading site plan to basic {pantheon_site_name}")
        upgrade_plan = subprocess.Popen(
            [f"terminus plan:set {pantheon_site_name} plan-basic_small-contract-annual-1"], shell=True)
        upgrade_plan.wait()
        logging.info(f"{instance} upgrated to basic plan")

        # Add subdomain to live subdomains list
        print(f"Adding subdomain live environment list")
        add_subdomain = subprocess.Popen(
            [f"terminus domain:add {pantheon_site_name}.live {instance_subdomain}"], shell=True)
        add_subdomain.wait()
        logging.info(f"{instance} adding subdomain to site subdomain list")

        # Connect subdomain to live instance
        print(f"Connecting subdomain {instance_subdomain}")
        connect_subdomain = subprocess.Popen(
            [f"terminus domain:primary:add {pantheon_site_name}.live {instance_subdomain}"], shell=True)
        connect_subdomain.wait()
        logging.info(f"{instance} Connecting subdomain {instance_subdomain}")

    # Clean up
    print("Cleaning up for next run...")
    subprocess.call(["rm", "-rf", "./database/"])
    subprocess.call(["rm", "-rf", "./files/"])
    subprocess.call(["rm", "settings.php"])

    # Log instance to file
    print(f"Completed: {instance}")
    logging.info(f"{instance} migrated succesfully")
    f.write(f"{instance}\n")

print("All Sites Processed.")
f.close()
