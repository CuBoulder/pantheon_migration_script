#!/bin/bash

# Export Pantheon variables
# org, upstream_id
source vars.sh
echo "Pantheon Site Importer"

# Clean up old files, if present
rm -rf ./database/*
rm -rf ./files/*

# Atlas target Environment
env=''
# TODO: Get rid of the backups_env var, only used when scp
backups_env=''
# Instance to export
instance=''

# Get instance path/name
site_name=$(curl -s -L https://${env}/atlas/sites/$instance | jq -r '.path')

# Parse url, replace forward slashes with dashes
# The site name can only contain a-z, A-Z, 0-9, and dashes ('-'), cannot begin or end with a dash, and must be fewer than 52 characters
pantheon_site_name="${site_name//\//-}"
echo "$pantheon_site_name"

# Backup Timer
backup_wait=10
# Pantheon Settings
# Pantheon Target Environment
pantheon_env='dev'
# Label will be the site name for now
# Label must not contain spaces otherwise site crete step will break
label=$pantheon_site_name

# Request site backups
status=$(curl -s --netrc-file credentials.netrc -H "Content-Type: application/json" -X POST -o /dev/null -I -w '%{http_code}' https://{$env}/atlas/sites/{$instance}/backup)

# Conditional to check for backup status
if [ $status -eq 200 ]; then
	echo "$instance | $site_name \n backup Initiated. Waiting $backup_wait seconds for backup to finish..."
else
	echo "Something went wrong, got $status response. Exiting..."
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
	echo $backup_state
	if [ $backup_state != "complete" ]
	then
		echo "Backup is taking too long to generate. Exiting..."
		exit 1
	fi
fi

echo "Backup is ready to export!"

# User needs to have SSH key added to server in order for scp to work
echo "Exporting..."
scp -i ~/.ssh/id_rsa ${env}:/nfs/${backups_env}_backups/backups/$site_database ./database
echo "Your database backup is ${site_database}"

scp -i ~/.ssh/id_rsa ${env}:/nfs/${backups_env}_backups/backups/$site_files ./files
echo "Your files backup is ${site_files}"

# Pantheon create new site
# site:create [--org [ORG]] [--region [REGION]] [--] <site> <label> <upstream_id>
# TODO Handle: Duplicate site names
# [error]  The site name jesus-import-site is already taken.
terminus site:create --org $org $pantheon_site_name $label $upstream_id

echo "Uploading database to $pantheon_site_name"
# Get mysql credentials for pantheon site
mysql_username=$(terminus connection:info $pantheon_site_name.dev --field mysql_username)
mysql_password=$(terminus connection:info $pantheon_site_name.dev --field mysql_password)
mysql_database=$(terminus connection:info $pantheon_site_name.dev --field mysql_database)
mysql_command=$(terminus connection:info $pantheon_site_name.dev --field mysql_command)
site_id=$(terminus site:info $pantheon_site_name --field id)

# Send DB to Pantheon
eval "$mysql_command < ./database/$site_database"

echo "Database upload complete"

echo "Rsync'ing files to pantheon"
# Unzip files backup on local machine
tar -xzf ./files/$site_files -C ./files/
# Remove tar file
rm ./files/$site_files

# TODO: Verify $env substitution, handle errors or write script to restart rync
# Rsync files to pantheon
rsync -rlIpz  -e "ssh -p 2222 -o StrictHostKeyChecking=no" --temp-dir=~/tmp --delay-updates ./files/ $pantheon_env.$site_id@appserver.$pantheon_env.$site_id.drush.in:files

echo "File rync complete"

# # Log instance to file
echo -e $instance >> imported_sites.txt

# Clean up 
echo "Cleaning up..."
rm -rf ./database/*
rm -rf ./files/*
echo "Done"
