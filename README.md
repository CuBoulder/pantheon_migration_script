# Web Express Migration Script

A python 3 script to automate moving sites from our webservers to Pantheon

## Pre-requisites

You will need to have the following items ready before using the script:

- [CU Boulder Pantheon Organization Access](https://dashboard.pantheon.io/login). You will need:
  - Organization ID
  - Express Mono Upstream ID

- [Terminus](https://pantheon.io/docs/terminus/) - Terminus, provides advanced interaction with Pantheon. Terminus enables you to do almost everything in a terminal that you can do in the Dashboard, and much more. [Installation steps](https://pantheon.io/docs/terminus/install/). Make sure to follow the both the Install and Authenticate: Machine Token steps.

- Add your ssh key to the utility servers
  ```
    ssh-copy-id YOUR_IDENTIKEY@remote-host
  ```

## Running the Script

1. Add run `ssh-add` in the same directory as the `migration.sh` script
2. Replace variables `identikey`, `user_password`, `org`, and `upstream_id` accordingly in `local_vars.py`
3. Set the variables `env`, `backups_env`, `pantheon_env`, `instance_list` in `python_migration_script.py`
4. Run script simply with `python3 python_migration_script.py`
