#!/bin/bash

# Export Pantheon variables
# org, upstream_id
source vars.sh
echo "Pantheon Site Importer"

# Atlas Target Environment
env='osr-dev-util01.int.colorado.edu'
# Backup Timer

backup_wait=5
# Pantheon Settings
pantheon_env='dev'
#label must not contain spaces otherwise site crete step will break
label='Test-Run-7'

# Instance to export
instance='5cd5e902e1fa27ae427accc5'
# Get instance path
site_name=$(curl -s -L https://${env}/atlas/sites/$instance | jq -r '.path')
echo "$site_name"

# Request site backups
status=$(curl -s --netrc-file credentials.netrc -H "Content-Type: application/json" -X POST -o /dev/null -I -w '%{http_code}' https://{$env}/atlas/sites/{$instance}/backup)

# Conditional to check for backup status
if [ $status -eq 200 ]; then
	echo "$instance | $site_name backup Initiated. Waiting $backup_wait seconds for backup to finish..."
else
	echo "Something went wrong, got $STATUS response. Exiting..."
	exit 1
fi
sleep $backup_wait

# Request most recent backup for instance
# -g This  option  switches  off  the "URL globbing parser". When you set this option, you can specify URLs that contain the letters {}[] without having them being interpreted by  curl itself.
echo "Querying for backup..."
backups_json=$(curl -s -g 'https://'${env}'/atlas/backup?sort=-_updated&max_results=1&where={"site":"'${instance}'"}')

# Variable names for file and database backups
site_files=$(echo $backups_json | jq -r '._items[].files')
site_database=$(echo $backups_json | jq -r '._items[].database')
backup_timestamp=$(echo $backups_json | jq -r '._items[].backup_date')
backup_state=$(echo $backups_json | jq -r '._items[].state')

# TODO: Add timeout for large backups, while loops in bash are limited so an if statement for now
if [ $backup_state != "complete" ]
then
	echo "Backup is not ready yet. Retrying in $backup_wait seconds..."
	sleep $backup_wait
	backups_json_retry=$(curl -s -g 'https://'${env}'/atlas/backup?sort=-_updated&max_results=1&where={"site":"'${instance}'"}')
	backup_state=$(echo $backups_json_retry | jq '._items[].state')
	echo "$backup_state"
	if [ $backup_state != "complete" ]
	then
		echo "Backup is taking too long to generate. Exiting..."
		exit 1
	fi
fi

echo "Backup is ready to export!"

# # # User needs to have SSH key added to server in order for this to work
echo "Exporting..."
scp -i ~/.ssh/id_rsa ${env}:/nfs/dev_backups/backups/$site_database ./database
echo "Your database backup is ${site_database}"

scp -i ~/.ssh/id_rsa ${env}:/nfs/dev_backups/backups/$site_files ./files
echo "Your files backup is ${site_files}"

# Pantheon create new site
# site:create [--org [ORG]] [--region [REGION]] [--] <site> <label> <upstream_id>

echo "$org $site_name $label $upstream_id"
# TODO Handle:  [error]  The site name jesus-import-site is already taken.
terminus site:create --org $org $site_name $label $upstream_id

# # Send DB to Pantheon
echo "Uploading database to $site_name"
# Get mysql credentials for pantheon site
mysql_username=$(terminus connection:info $site_name.dev --field mysql_username)
mysql_password=$(terminus connection:info $site_name.dev --field mysql_password)
mysql_database=$(terminus connection:info $site_name.dev --field mysql_database)
mysql_command=$(terminus connection:info jesus-import-site.dev --field mysql_command)
site_id=$(terminus site:info jesus-import-site --field id)

eval "$mysql_command < ./database/$site_database"

echo "Database upload complete"

echo "Rsync'ing files to pantheon"
tar -xzvf ./files/$site_files -C ./files/
rm ./files/$site_files

# TODO: Verify $env substitution
rsync -rlIpz  -e "ssh -p 2222 -o StrictHostKeyChecking=no" --temp-dir=~/tmp --delay-updates ./files/ $pantheon_env.$site_id@appserver.$pantheon_env.$site_id.drush.in:files

echo "File rync complete"

# # Log instance to file
echo -e $instance >> imported_sites.txt

# Clean up 
echo "Cleaning up..."
rm -rf ./database/*
rm -rf ./files/*
echo "Done"
