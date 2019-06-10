# Python 3 Migration Script

import subprocess
import requests
import time

# Clean up old files, if present
# TODO: Create new directories instead to ensure "clean" setup
subprocess.Popen(['rm -rf ./database/*'], shell=True)
subprocess.Popen(['rm -rf ./files/*'], shell=True)

# Atlas target Environment
env = 'osr-dev-util01.int.colorado.edu'
# TODO: Get rid of the backups_env var, only used when scp
backups_env = 'dev'
# Instance to export
instance = '5b97d9ee8ee9ff763a0844c8'

# Get instance path/name
# site_name = 

response = requests.get(f'https://{env}/atlas/sites/{instance}')
payload_json = response.json()
site_name = payload_json["path"]

# Parse url, replace forward slashes with dashes
# The site name can only contain a-z, A-Z, 0-9, and dashes ('-'), cannot begin or end with a dash, and must be fewer than 52 characters
pantheon_site_name = site_name.replace('/', '-')
print("Pantheon Site Name " + pantheon_site_name)

# Backup Timer
backup_wait = 5
# Pantheon Settings
# Pantheon Target Environment
pantheon_env='dev'
# Label will be the site name for now
# Label must not contain spaces otherwise site crete step will break
label=pantheon_site_name

# Request site backups
backup_request = requests.post(f'https://{env}/atlas/sites/{instance}/backup', auth=(identikey, user_password))
print(backup_request.status_code)
print(f"Waiting {backup_wait} secs")
time.sleep(backup_wait)

# TODO: Come up with a better way to insert instance var in payload dict
backup_params = {'sort': '-_updated', 'max_results': '1', 'where': '{"site":"'+instance+'"}'}
site_backup_request = requests.get(f'https://{env}/atlas/backup', params = backup_params)
site_backup_json = site_backup_request.json()
site_backup_state = site_backup_json['_items'][0]['state']
# print(site_backup_json['_items'][0]['state'])

print("First check: " + site_backup_state)
while (site_backup_state != 'complete'):
    backup_params = {'sort': '-_updated', 'max_results': '1', 'where': '{"site":"'+instance+'"}'}
    site_backup_request = requests.get(f'https://{env}/atlas/backup', params = backup_params)
    site_backup_json = site_backup_request.json()
    site_backup_state = site_backup_json['_items'][0]['state']
    print("Loop " + site_backup_state)
    print(f"Waiting {backup_wait} secs again")
    time.sleep(backup_wait)


print("Backup is ready for export!")

site_files = site_backup_json['_items'][0]['files']
site_database = site_backup_json['_items'][0]['database']
backup_timestamp = site_backup_json['_items'][0]['backup_date']

# User needs to have SSH key added to server in order for scp to work
print("Exporting...")

subprocess.Popen([f'scp -i ~/.ssh/id_rsa {env}:/nfs/{backups_env}_backups/backups/{site_database} ./database'], shell=True)

print(f"Your database backup is {site_database}")

subprocess.Popen([f'scp -i ~/.ssh/id_rsa {env}:/nfs/{backups_env}_backups/backups/{site_files} ./files'], shell=True)
print(f"Your files backup is {site_files}")


# Pantheon create new site
# site:create [--org [ORG]] [--region [REGION]] [--] <site> <label> <upstream_id>
# TODO Handle: Duplicate site names
# [error]  The site name jesus-import-site is already taken.
subprocess.Popen([f"terminus site:create --org {org} {pantheon_site_name} {label} {upstream_id}"], shell=True)

print(f"Uploading database to {pantheon_site_name}")
# Get mysql credentials for pantheon site
# TODO: Is there a way to call of this info at once and store in one variable?
mysql_username = subprocess.Popen([f'terminus connection:info {pantheon_site_name}.{pantheon_env} --field mysql_username'], shell=True)
mysql_password = subprocess.Popen([f'terminus connection:info {pantheon_site_name}.{pantheon_env} --field mysql_password'], shell=True)
mysql_database = subprocess.Popen([f'terminus connection:info {pantheon_site_name}.{pantheon_env} --field mysql_database'], shell=True)
mysql_command = subprocess.Popen([f'terminus connection:info {pantheon_site_name}.{pantheon_env} --field mysql_command)'], shell=True)
site_id = subprocess.Popen([f'terminus site:info {pantheon_site_name} --field id)'], shell=True)

# Send DB to Pantheon
subprocess.Popen([f'eval "{mysql_command} < ./database/{site_database}"'], shell=True)

print("Database upload complete")

print("Rsync'ing files to pantheon")
# Unzip files backup on local machine
subprocess.Popen([f'tar -xzf ./files/{site_files} -C ./files/'], shell=True)

# Remove tar file
subprocess.Popen([f'rm ./files/{site_files}'], shell=True)

# TODO: Verify $env substitution, handle errors or write script to restart rync
# Rsync files to pantheon
subprocess.Popen([f'rsync -rlIpz  -e "ssh -p 2222 -o StrictHostKeyChecking=no" --temp-dir=~/tmp --delay-updates ./files/ {pantheon_env}.{site_id}@appserver.{pantheon_env}.{site_id}.drush.in:files'], shell=True

print("File rync complete")

# Log instance to file
# TODO: Do the file writing in python
subprocess.Popen([f'echo -e {instance} >> imported_sites.txt'], shell=True)

# Clean up 
print("Cleaning up...")
subprocess.Popen(['rm -rf ./database/*'], shell=True)
subprocess.Popen(['rm -rf ./files/*'], shell=True)


print('Done.')

# subprocess.Popen('rm -rf ./database/*', shell=True)
# subprocess.Popen('rm -rf ./files/*', shell=True)
